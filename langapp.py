import streamlit as st
from streamlit_chat import message
from lang_model import invoke_graph
from st_callable_util import get_streamlit_cb
from langchain_core.messages import AIMessage, HumanMessage

# config = {"configurable": {"thread_id": "1"}}

st.title("Nomad AI")

# # Initialize session state
# if 'messages' not in st.session_state:
#     st.session_state.messages = []

# # Display chat messages from history
# for message in st.session_state.messages:
#     st.chat_message(message['role']).markdown(message['content'])


# # # input_text = st.text_area("Enter your travel query:", placeholder="E.g., Find flights from NYC to LAX on 2024-12-01.")
# prompt = st.chat_input('Pass Your Prompt here')

# if prompt:

#     st.session_state.messages.append({'role': 'user', 'content': prompt})
#     st.chat_message('user').markdown(prompt)

#     assistant_message = st.chat_message('assistant')
#     message_placeholder = assistant_message.markdown("Loading your travel plans...!")


#     st_callback = get_streamlit_cb(st.container())
#     output = invoke_graph(prompt, [st_callback])
#     response = output['agent_output']['output']

#     message_placeholder.markdown(response)

#     st.session_state.messages.append({'role': 'assistant', 'content': response})


if "messages" not in st.session_state:
    # default initial message to render in message state
    st.session_state["messages"] = [AIMessage(content="How can I help you?")]

# Function to reset the conversation
def reset_conversation():
    st.session_state["messages"] = [AIMessage(content="How can I help you?")]

# Add a reset button at the top
if st.button("Reset Conversation"):
    reset_conversation()


# Loop through all messages in the session state and render them as a chat on every st.refresh mech
for msg in st.session_state.messages:
    # https://docs.streamlit.io/develop/api-reference/chat/st.chat_message
    # we store them as AIMessage and HumanMessage as its easier to send to LangGraph
    if type(msg) == AIMessage:
        st.chat_message("assistant").write(msg.content)
    if type(msg) == HumanMessage:
        st.chat_message("user").write(msg.content)

# takes new input in chat box from user and invokes the graph
if prompt := st.chat_input():
    st.session_state.messages.append(HumanMessage(content=prompt))
    st.chat_message("user").write(prompt)

    # Process the AI's response and handles graph events using the callback mechanism
    with st.chat_message("assistant"):
        # create a new container for streaming messages only, and give it context
        st_callback = get_streamlit_cb(st.container())
        response = invoke_graph(st.session_state.messages, [st_callback])
        # Add that last message to the st_message_state
        # Streamlit's refresh the message will automatically be visually rendered bc of the msg render for loop above
        st.session_state.messages.append(AIMessage(content=response['agent_output']['output']))