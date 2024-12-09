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


def extract_info(data_list):
    results = []
    for data in data_list:
        itinerary = data["itineraries"][0]  # Assume only one itinerary for simplicity
        segments = itinerary["segments"]
        fare_details = data["travelerPricings"][0]["fareDetailsBySegment"]

        # Map segment IDs to fare details
        fare_map = {fare["segmentId"]: fare["cabin"] for fare in fare_details}

        # Initialize flat dictionary
        flat_data = {
            "numberOfBookableSeats": data.get("numberOfBookableSeats"),
            "total_duration": itinerary["duration"].lstrip("PT"),
            "number_of_stops": len(segments)-1,
            "price_currency": data["price"]["currency"],
            "price_total": data["price"]["total"],
        }

        # Flatten segments with departure/arrival IATA codes, carrier code, and cabin class
        for idx, segment in enumerate(segments, start=1):
            flat_data[f"segments_{idx}_departure"] = segment["departure"]["at"]
            flat_data[f"segments_{idx}_departure_iata"] = segment["departure"]["iataCode"]
            flat_data[f"segments_{idx}_arrival"] = segment["arrival"]["at"]
            flat_data[f"segments_{idx}_arrival_iata"] = segment["arrival"]["iataCode"]
            flat_data[f"segments_{idx}_duration"] = segment["duration"].lstrip("PT")
            flat_data[f"segments_{idx}_carrier_code"] = segment["carrierCode"]
            flat_data[f"segments_{idx}_cabin_class"] = fare_map.get(segment.get("id"), "Unknown")

        # Add additional services
        additional_services = data.get("price", {}).get("additionalServices", [])
        for idx, service in enumerate(additional_services, start=1):
            flat_data[f"additional_service_{idx}_type"] = service.get("type", "Unknown")
            flat_data[f"additional_service_{idx}_amount"] = service.get("amount", "0.00")

        results.append(flat_data)
    return results

def filter_flights(
    flights, max_price=None, cabin_class=None
):
    """
    Filters the extracted flight data based on maximum price and cabin class.
    - `max_price`: Maximum allowable price (float).
    - `cabin_class`: Desired cabin class ("ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST").
    """
    filtered = []

    for flight in flights:
        # Check price filter
        if max_price is not None and float(flight["price_total"]) > max_price:
            continue

        # Check cabin class filter (apply to all segments)
        if cabin_class is not None:
            matching_classes = [
                flight.get(f"segments_{idx}_cabin_class")
                for idx in range(1, flight["number_of_stops"] + 2)
            ]
            if cabin_class not in matching_classes:
                continue

        # Add to results if all conditions are satisfied
        filtered.append(flight)

    # Sort by price_total in ascending order
    return sorted(filtered, key=lambda x: x["price_total"])

def query_refiner(log, prompt):
    # Define the system prompt to guide the model's behavior
    system_prompt = {
        'role': 'system',
        'content': (
            """
            Given the following user query and conversation log, use these details to formulate a question that is focused and contextually relevant, 
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

    print(response['message']['content'])

    return response['message']['content']

def NomadAI(prompt, context):

    # Define the system prompt to guide the model's behavior
    system_prompt = {
        'role': 'system',
        'content': (
            """You are a travel assistant. Greet them accordingly
            
            Your task is to determine if the user's prompt specifies:
            1. Departure location
            2. arrival location
            3. Date

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
            You are a parser that parses user input
            """
        )
    }

    # Call the chat model with both the system prompt and the user prompt
    json_response : ChatResponse = chat(model='finetune_1b', messages=[
        system_prompt,
        {'role': 'user', 'content': prompt}],
        stream=False,
        options={"temperature":0.1}
    )

    json_response = json_response['message']['content']
    json_response = json_response.replace("'", '"')
    response_json = json.loads(json_response)


    # API CALL TO AMADEUS
    amadeus = Client(
        client_id=os.getenv('AMADEUS_CLIENT_ID'),
        client_secret=os.getenv('AMADEUS_CLIENT_SECRET')
    )

    empty = {}
    for request in response_json['action']:
        # endpoint = request.get("endpoint")
        # params = request.get("params", {})
        # print(params)
        
        if request == "search_flights":
            try:
                response = amadeus.shopping.flight_offers_search.get(
                    originLocationCode=response_json['action_input']['origin'],
                    destinationLocationCode=response_json['action_input']['destination'],
                    departureDate=response_json['action_input']['departure_date'],
                    adults=response_json['action_input']['adults'],
                    max=10)

                flights = response.data

                clean_flights = extract_info(flights)

                price = response_json['action_input'].get('maxPrice', None) if response_json['action_input'].get('maxPrice') != 'null' else None
                cabin = response_json['action_input'].get('class', None) if response_json['action_input'].get('class') != 'null' else None

                filtered_flights = filter_flights(clean_flights, max_price=price, cabin_class=cabin)

                result = filtered_flights[:5]
                print(result)


                # keys_to_filter = ['numberOfBookableSeats','itineraries','price']

                # result = [
                #     {key: value for key, value in dictionary.items() if key in keys_to_filter}
                #     for dictionary in flights
                # ]

            #     rd = response.data
            except:
                result = "No flights available"
                print(result)



        elif request == "search_hotels":

            rating = response_json['action_input'].get('ratings',5)

            response = amadeus.reference_data.locations.hotels.by_city.get(
                cityCode=response_json['action_input']['destination'],
                ratings=[rating],
                radius=30)

            hotels = response.data

            sorted_hotels = sorted(
                [
                    {
                        'iataCode': hotel['iataCode'],
                        'name': hotel['name'],
                        'address': hotel['address'],
                        'distance': hotel['distance'],
                        'rating': hotel['rating']
                    }
                    for hotel in hotels
                ],
                key=lambda x: x['distance']['value']
            )

            result = sorted_hotels[:10]
            print(result)
        elif request == "activities":
            result = f"search activities to do in {response_json['action_input']['destination']} and respond to user"
        
        empty[request] = result



    # empty = {}
    # for request in [response_json]:
    #     endpoint = request.get("endpoint")
    #     params = request.get("params", {})
    #     print(params)
        
    #     if endpoint == "/search_flights":
    #         try:
    #             response = amadeus.shopping.flight_offers_search.get(
    #                 originLocationCode=params['originLocationCode'],
    #                 destinationLocationCode=params['destinationLocationCode'],
    #                 departureDate=params['departureDate'],
    #                 adults=params['adults'],
    #                 max=5)

    #             flights = response.data

    #             clean_flights = extract_info(flights)

    #             price = params.get('price', None)
    #             cabin = params.get('cabin', None)

    #             filtered_flights = filter_flights(clean_flights, max_price=price, cabin_class=cabin)

    #             result = filtered_flights[:10]
    #             print(result)


    #             # keys_to_filter = ['numberOfBookableSeats','itineraries','price']

    #             # result = [
    #             #     {key: value for key, value in dictionary.items() if key in keys_to_filter}
    #             #     for dictionary in flights
    #             # ]

    #         #     rd = response.data
    #         except:
    #             result = "No flights available"
    #             print(result)
    #     elif endpoint == "/search_hotels":
    #         # Call the hotels API with the provided params
    #         print(params)
    #     else:
    #         print(f"Unknown endpoint: {endpoint}")
        
    #     empty[endpoint] = result




    # JSON TO HUMAN OUTPUT
    # Define the system prompt to guide the model's behavior
    system_prompt = {
        'role': 'system',
        'content': (
            """
            You are a travel assistant.
            The input will be a json format input
            Select only some options and summarize each option separately regarding the information.
            Speak as if you are explaining the details.
            Only summarize thoroughly.
            Don't greet them if the context is empty and only reply form the data given.
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
        {'role': 'user', 'content': f"Context':{len(context)} / 'data':{json_data}"}],
        stream=True,
        options={"temperature":0.1}
    )

    # return response['message']['content']

    for chunk in response:
        yield chunk['message']['content']