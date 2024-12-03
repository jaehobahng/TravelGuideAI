from ollama import chat
from ollama import ChatResponse
import time
import json
from amadeus import Client, ResponseError
from datetime import datetime
from dotenv import load_dotenv
import os

# Load variables from the .env file
load_dotenv()


def stream_output(output, delay=0.05):
    for char in output.split():
        print(char, end=' ', flush=True)
        time.sleep(delay)


# Function to calculate the number of stops
def get_num_stops(offer):
    return len(offer['itineraries'][0]['segments']) - 1



# Function to filter by stops and cabin class
def filter_by_stops_and_cabin(data, stops, cabin_class, top_n):
    # Filter by number of stops
    filtered_by_stops = [offer for offer in data if get_num_stops(offer) == stops]
    
    # Filter by cabin class
    filtered_by_cabin = [
        offer for offer in filtered_by_stops 
        if all(fare['cabin'] == cabin_class for fare in offer['travelerPricings'][0]['fareDetailsBySegment'])
    ]
    
    # Sort by price and return the top `n` offers
    return sorted(filtered_by_cabin, key=lambda x: float(x['price']['total']))[:top_n]

def feature_engineering(data, keys_to_extract):
    """
    Adds a 'flightinfo' key and a 'layover_minutes' key to each item in the dataset.
    - 'flightinfo': Merges details from segments and fareDetailsBySegment.
    - 'layover_minutes': Calculates the layover time between the first arrival and second departure.

    Parameters:
    - data (list): A list of dictionaries, where each dictionary contains 'itineraries' 
                and 'travelerPricings' keys.

    Returns:
    - list: The updated dataset with 'flightinfo' and 'layover_minutes' added to each item.
    """
    for item in data:
        # Extract segments and fare details
        segments = item['itineraries'][0]['segments']
        fare_details = item['travelerPricings'][0]['fareDetailsBySegment']

        # Merge flightinfo
        merged_flight_info = []
        for segment in segments:
            for fare in fare_details:
                if segment['id'] == fare['segmentId']:
                    merged_flight_info.append({
                        'departure': segment['departure'],
                        'arrival': segment['arrival'],
                        'carrierCode': segment['carrierCode'],
                        'duration': segment['duration'],
                        'cabin': fare['cabin'],
                        # 'includedCheckedBags': fare['includedCheckedBags']
                    })
        item['flightinfo'] = merged_flight_info

        # Calculate layover_minutes
        if len(segments) > 1:  # Ensure there are at least two segments to calculate layover
            first_arrival = segments[0]['arrival']['at']
            second_departure = segments[1]['departure']['at']

            # Convert times to datetime objects
            first_arrival_time = datetime.fromisoformat(first_arrival)
            second_departure_time = datetime.fromisoformat(second_departure)

            # Calculate the time difference in minutes
            time_difference_minutes = (second_departure_time - first_arrival_time).total_seconds() / 60
            item['layover_minutes'] = time_difference_minutes
        else:
            item['layover_minutes'] = 0

    data = [{key: item[key] for key in keys_to_extract if key in item} for item in data]

    return data


def query_refiner(log, prompt):
    # Define the system prompt to guide the model's behavior
    system_prompt = {
        'role': 'system',
        'content': (
            """
            Given the following user query and conversation log, extract the last destination location, the last departure location, 
            and the last time mentioned. Use these details to formulate a question that is focused and contextually relevant, 
            while incorporating the rest of the conversation for clarity. Just output the new question.
            """
        )
    }

    # Call the chat model with both the system prompt and the user prompt
    response : ChatResponse = chat(model='llama3.2', messages=[
        system_prompt,
        {'role': 'user', 'content': f"Log : {log} / Prompt : {prompt}"}],
        stream=False,
        options={"temperature":0.1}
    )

    return response['message']['content']

def NomadAI(prompt, context):

    # Define the system prompt to guide the model's behavior
    system_prompt = {
        'role': 'system',
        'content': (
            """You are a travel assistant. Greet them accordingly, but your task is to determine if the user's prompt specifies:
            1. Two cities
            2. A Date

            If either one is missing, explain nicely what information the user needs to input, 

            If both are present, respond only with 'VALID QUERY' and nothing else."""
        )
    }

    # Example user prompt (replace with actual user input)
    # user_prompt = "Why is the sky blue?"
    # user_prompt = "I want to book a flight from chicago to newyork on january 1 2025"

    # Call the chat model with both the system prompt and the user prompt
    validation_response : ChatResponse = chat(model='llama3.2', messages=[
        system_prompt,
        {'role': 'user', 'content': prompt}],
        stream=True,
        options={"temperature":0.1}
    )

    
    validation_output = ""

    # Stream the output word by word
    for chunk in validation_response:
        # Append the current chunk to the output
        validation_output += chunk['message']['content']

    if 'VALID QUERY' not in validation_output:
        for chunk in validation_output:
            yield chunk
        return




    # FINE TUNE MODEL GOES HERE
    # Define the system prompt to guide the model's behavior
    system_prompt = {
        'role': 'system',
        'content': (
            """
            You are a data parser for a travel related input.
            Your task is to read user input, and parse it into json format like below based on starting location, destination, and date.
            Only give the output as json format

            {"endpoint": "/search_flights", "params": {"originLocationCode": "3 letter code", "destinationLocationCode": "3 letter code", "departureDate": "date format", "adults": 1}}
            """
        )
    }

    # Call the chat model with both the system prompt and the user prompt
    json_response : ChatResponse = chat(model='llama3.2', messages=[
        system_prompt,
        {'role': 'user', 'content': prompt}],
        stream=False,
        options={"temperature":0.1}
    )

    json_response = json_response['message']['content']
    response_json = json.loads(json_response)


    # API CALL TO AMADEUS
    amadeus = Client(
        client_id=os.getenv('AMADEUS_CLIENT_ID'),
        client_secret=os.getenv('AMADEUS_CLIENT_SECRET')
    )


    empty = {}
    for request in [response_json]:
        endpoint = request.get("endpoint")
        params = request.get("params", {})
        
        if endpoint == "/search_flights":
            try:
                response = amadeus.shopping.flight_offers_search.get(
                    originLocationCode=params['originLocationCode'],
                    destinationLocationCode=params['destinationLocationCode'],
                    departureDate=params['departureDate'],
                    adults=params['adults'],
                    max=5)

                flights = response.data

                keys_to_filter = ['numberOfBookableSeats','itineraries','price']

                result = [
                    {key: value for key, value in dictionary.items() if key in keys_to_filter}
                    for dictionary in flights
                ]

            #     rd = response.data
            except ResponseError as error:
                print(error)
        elif endpoint == "/search_hotels":
            # Call the hotels API with the provided params
            print(params)
        else:
            print(f"Unknown endpoint: {endpoint}")
        
        empty[endpoint] = result




    # JSON TO HUMAN OUTPUT
    # Define the system prompt to guide the model's behavior
    system_prompt = {
        'role': 'system',
        'content': (
            """
            You are a travel assistant.
            The input will be a json format input with flight information
            Given the context which is conversation that has happened before, summarize the data choices the user has regarding the information.
            Speak as if you are explaining the details.
            Only summarize thoroughly.
            Don't ask to assist further than summarization.
            """
        )
    }

    # Example user prompt (replace with actual user input)
    # user_prompt = "Why is the sky blue?"
    json_data = str(empty)

    # Call the chat model with both the system prompt and the user prompt
    response : ChatResponse = chat(model='llama3.2', messages=[
        system_prompt,
        {'role': 'user', 'content': f"Context':{context} / 'data':{json_data}"}],
        stream=True,
        options={"temperature":0.1}
    )

    # return response['message']['content']

    for chunk in response:
        yield chunk['message']['content']