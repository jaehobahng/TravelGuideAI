from langchain_core.tools import tool
from amadeus import Client, ResponseError
import os
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

# Load variables from the .env file
load_dotenv()


@tool
def flight(dep: str, arr: str, date: str) -> str:
    """Find Three letter code for Departure and arrival / find date of trip"""
    
    amadeus = Client(
        client_id=os.getenv("AMADEUS_CLIENT_ID"),
        client_secret=os.getenv("AMADEUS_CLIENT_SECRET"),
    )

    response = amadeus.shopping.flight_offers_search.get(
        originLocationCode=dep,
        destinationLocationCode=arr,
        departureDate=date,
        adults=1,
    )
    flights = response.data


    return flights[:3]

@tool
def hotels(city: str) -> str:
    "Find three letter location code for hotel information for trip destination"
    
    amadeus = Client(
        client_id=os.getenv("AMADEUS_CLIENT_ID"),
        client_secret=os.getenv("AMADEUS_CLIENT_SECRET"),
    )

    response = amadeus.reference_data.locations.hotels.by_city.get(
        cityCode=city,
        ratings=[5],
        radius=30)

    hotels = response.data

    return hotels[:3]


from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain.prompts import SystemMessagePromptTemplate, PromptTemplate
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.chains.llm import LLMChain
from langchain import hub

from langgraph.graph import END, START, StateGraph, MessagesState
from langgraph.checkpoint.memory import MemorySaver



# Initialize the language model
llm = ChatOpenAI(model="gpt-3.5-turbo-0125")


# Define the preprocessing function
def preprocessing_function(state):
    input_text = state['input']
    llm = ChatOpenAI(model="gpt-3.5-turbo-0125")

    template_simp = """
    You are a rephraser.
    Look at past chat results to identify the accurate quesitons and
    replace all location names to 3 letter iata codes in the input below and output the replaced text.
    
    input : {input}
    """
    prompt = PromptTemplate(
        template = template_simp,
        input_variables=['input']
    )

    # Define a preprocessing chain (e.g., another LLM or function)
    preprocessing_chain = LLMChain(llm=llm, prompt = prompt, output_key = 'preprocessed_input')

    result = preprocessing_chain.run(input_text)

    return {'preprocessed_input': result}

# Define the agent execution function
def agent_execution_function(state):
    preprocessed_input = state['preprocessed_input']
    llm = ChatOpenAI(model="gpt-3.5-turbo-0125")
    # Here, you would integrate your agent executor logic
    # For demonstration, we'll just return the preprocessed input
    # agent_output = f"Agent received: {preprocessed_input}"

    # Define a prompt template
    prompt = hub.pull("hwchase17/openai-tools-agent")

        # Define the new system message
    new_system_message = SystemMessagePromptTemplate(
        prompt=PromptTemplate.from_template("You are a travel agency. explain the information kindly to customers")
    )

    # Replace the first message with the new system message
    prompt.messages[0] = new_system_message

    # Define tools
    tools = [flight, hotels]  # Replace with your actual tool instances

    # Create the agent
    agent = create_tool_calling_agent(llm, tools, prompt)

    # Create the agent executor
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    agent_output = agent_executor.invoke({'input':preprocessed_input})

    return {'agent_output': agent_output}

# Define the state structure
class AgentState(dict):
    input: str
    preprocessed_input: str
    agent_output: str



graph = StateGraph(AgentState)

# Add nodes to the graph
graph.add_node("preprocessing", preprocessing_function)
graph.add_node("agent_execution", agent_execution_function)

# Define the edges
graph.set_entry_point("preprocessing")
graph.add_edge("preprocessing", "agent_execution")
# graph.add_edge("agent_execution", END)


# from langgraph.store.memory import InMemoryStore

# in_memory_store = InMemoryStore()

app = graph.compile()

# checkpointer = MemorySaver()
# app = graph.compile(checkpointer=checkpointer)


def invoke_graph(st_messages, callables):
    # Ensure the callables parameter is a list as you can have multiple callbacks
    if not isinstance(callables, list):
        raise TypeError("callables must be a list")
    # Invoke the graph with the current messages and callback configuration
    return app.invoke({"input": st_messages}, config={"callbacks": callables})
