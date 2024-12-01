from langchain_core.tools import tool
from amadeus import Client, ResponseError
import os
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

# Load variables from the .env file
load_dotenv()


@tool
def flight(departure: str, arrival: str, date: str, people: int = 1, nonstop: str = 'false'):
    """
    You are finding details on flight requests. The definitions of the variables are as follows.

    'departure' : three letter code of starting location of the trip
    'arrival' : three letter code of destination of the trip
    'date' : date the trip is starting
    'people' : number of people on the flight
    'nonstop' : 'true'' if only nonstop flights are requested. 'false' if not specified.
    """
    
    amadeus = Client(
        client_id=os.getenv("AMADEUS_CLIENT_ID"),
        client_secret=os.getenv("AMADEUS_CLIENT_SECRET"),
    )

    response = amadeus.shopping.flight_offers_search.get(
        originLocationCode=departure,
        destinationLocationCode=arrival,
        departureDate=date,
        adults=people,
        nonStop = nonstop,
        max=5
    )

    flights = response.data

    keys_to_filter = ['numberOfBookableSeats','itineraries','price']

    filtered_list = [
        {key: value for key, value in dictionary.items() if key in keys_to_filter}
        for dictionary in flights
    ]


    return filtered_list[:3]

@tool
def hotels(city: str) -> str:
    """
    Use tool when user specifies hotel inquiry

    'city' : City of destination where user asks hotel information about.
    
    """
    
    amadeus = Client(
        client_id=os.getenv("AMADEUS_CLIENT_ID"),
        client_secret=os.getenv("AMADEUS_CLIENT_SECRET"),
    )

    response = amadeus.reference_data.locations.hotels.by_city.get(
        cityCode=city,
        ratings=[5],
        radius=30)

    hotels = response.data

    return hotels[:10]


import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry
import json

@tool
def weather(latitude: str, longitude: str, start_date: str, end_date: str):
    """
    You are finding weather details on the travel destination. The definitions of the variables are as follows.

    'latitude' : latitude of the destination of the trip
    'longitude' : longitude of the destination of the trip
    'start_date' : 3 days before the start date of the trip minus one year
    'end_date' : 4 days after the start date of the trip minus one year
    """
    # Setup the Open-Meteo API client with cache and retry on error
    cache_session = requests_cache.CachedSession('.cache', expire_after = -1)
    retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
    openmeteo = openmeteo_requests.Client(session = retry_session)

    # Make sure all required weather variables are listed here
    # The order of variables in hourly or daily is important to assign them correctly below
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "daily": ["temperature_2m_max", "temperature_2m_min",'rain_sum','snowfall_sum','wind_speed_10m_max'],
        'wind_speed_unit' : 'mph',
        'temperature_unit': 'fahrenheit'
    }
    responses = openmeteo.weather_api(url, params=params)

    # Process first location. Add a for-loop for multiple locations or weather models
    response = responses[0]

    # Process hourly data. The order of variables needs to be the same as requested.
    daily = response.Daily()
    temperature_max = float(daily.Variables(0).ValuesAsNumpy().mean())
    temperature_min = float(daily.Variables(1).ValuesAsNumpy().mean())
    rain_sum = float(daily.Variables(2).ValuesAsNumpy().mean())
    snow_sum = float(daily.Variables(3).ValuesAsNumpy().mean())
    wind_speed_max = float(daily.Variables(4).ValuesAsNumpy().mean())


    # Create a dictionary to hold the data
    summary_data = {
        "average_maximum_temperature": temperature_max,
        "average_minimum_temperature": temperature_min,
        "average_rainfall": rain_sum,
        "average_snowfall": snow_sum,
        "average_wind_speed": wind_speed_max
    }

    return summary_data

@tool("final_answer")
def final_answer(
    summary: str
):
    """
    You are a travel guide.
    Explain all detail retrieved to the user in conversational format
    """

    return ""


from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import time
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langgraph.graph import END, START, StateGraph, MessagesState
from langchain.prompts import SystemMessagePromptTemplate, PromptTemplate
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.chains.llm import LLMChain
from langchain import hub
from typing import TypedDict, Annotated, List, Union
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.messages import BaseMessage
import operator
from langgraph.checkpoint.memory import MemorySaver

class AgentState(TypedDict):
    input: str
    chat_history: list[BaseMessage]
    intermediate_steps: Annotated[list[tuple[AgentAction, str]], operator.add]

formatted_time = time.strftime("%Y-%m-%d", time.localtime())


system_prompt = f"""
You are the oracle, the great AI decision maker and a travel guide.
Talk to the user as a travel guide is treating a customer.

When asked about activities or attractions in a given area, answer directly with out using tools.
Given the user's query you must decide what to do with it based on the list of tools provided to you. Use each tool only once.

Change all city names found in the input to three letter IATA codes before using a tool
If a relative time is given such as "next monday", calculate it with today being {formatted_time}

Once you have collected the information
answer the user's question (stored in the scratchpad), talk conversationally in great detail as if talking to a customer as a travel guide"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="chat_history"),
    ("user", "{input}"),
    ("assistant", "scratchpad: {scratchpad}"),
])

# Initialize the language model
llm = ChatOpenAI(model="gpt-3.5-turbo-0125")


tools=[
    flight,
    hotels,
    weather,
    final_answer
]

# define a function to transform intermediate_steps from list
# of AgentAction to scratchpad string
def create_scratchpad(intermediate_steps: list[AgentAction]):
    research_steps = []
    for i, action in enumerate(intermediate_steps):
        if action.log != "TBD":
            # this was the ToolExecution
            research_steps.append(
                f"Tool: {action.tool}, input: {action.tool_input}\n"
                f"Output: {action.log}"
            )
    return "\n---\n".join(research_steps)

oracle = (
    {
        "input": lambda x: x["input"],
        "chat_history": lambda x: x["chat_history"],
        "scratchpad": lambda x: create_scratchpad(
            intermediate_steps=x["intermediate_steps"]
        ),
    }
    | prompt
    | llm.bind_tools(tools, tool_choice="any")
)

def run_oracle(state: list):
    print("run_oracle")
    print(f"intermediate_steps: {state['intermediate_steps']}")
    out = oracle.invoke(state)
    tool_name = out.tool_calls[0]["name"]
    tool_args = out.tool_calls[0]["args"]
    action_out = AgentAction(
        tool=tool_name,
        tool_input=tool_args,
        log="TBD"
    )
    return {
        "intermediate_steps": [action_out]
    }

def router(state: list):
    # return the tool name to use
    if isinstance(state["intermediate_steps"], list):
        return state["intermediate_steps"][-1].tool
    else:
        # if we output bad format go to final answer
        print("Router invalid format")
        return "final_answer"
    
tool_str_to_func = {
    "flight": flight,
    "hotels": hotels,
    "weather": weather,
    "final_answer": final_answer
}

def run_tool(state: list):
    # use this as helper function so we repeat less code
    tool_name = state["intermediate_steps"][-1].tool
    tool_args = state["intermediate_steps"][-1].tool_input
    print(f"{tool_name}.invoke(input={tool_args})")
    # run tool
    out = tool_str_to_func[tool_name].invoke(input=tool_args)
    action_out = AgentAction(
        tool=tool_name,
        tool_input=tool_args,
        log=str(out)
    )
    return {"intermediate_steps": [action_out]}


from langgraph.graph import StateGraph, END

memory = MemorySaver()

def NomadAI():

    graph = StateGraph(AgentState)

    graph.add_node("oracle", run_oracle)
    graph.add_node("hotels", run_tool)
    graph.add_node("flight", run_tool)
    graph.add_node("weather", run_tool)
    graph.add_node("final_answer", run_tool)

    graph.set_entry_point("oracle")

    graph.add_conditional_edges(
        source="oracle",  # where in graph to start
        path=router,  # function to determine which node is called
    )

    # create edges from each tool back to the oracle
    for tool_obj in tools:
        if tool_obj.name != "final_answer":
            graph.add_edge(tool_obj.name, "oracle")

    # if anything goes to final answer, it must then move to END
    graph.add_edge("final_answer", END)

    runnable = graph.compile(checkpointer=memory)

    return runnable



def invoke_graph(st_messages, callables):
    # Ensure the callables parameter is a list as you can have multiple callbacks
    if not isinstance(callables, list):
        raise TypeError("callables must be a list")
    # Invoke the graph with the current messages and callback configuration
    return runnable.invoke({"input": st_messages, "chat_history": []}, config={"callbacks": callables})