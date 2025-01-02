import streamlit as st
from streamlit_chat import message
from lang_model import NomadAI
# from st_callable_util import get_streamlit_cb
from langchain_core.messages import AIMessage, HumanMessage
import time
import uuid
import re

# Config for icons
USER_ICON = "../images/traveller.png"  # Replace with the path to your user icon
ASSISTANT_ICON = "../images/guide.png"

st.title("Nomad AI")
# st.chat_message("assistant").image("./images/guide.png")


if "messages" not in st.session_state:
    # default initial message to render in message state
    st.session_state["messages"] = [AIMessage(content="How can I help you?")]


# Function to reset the conversation
def reset_conversation():
    st.session_state["messages"] = [AIMessage(content="How can I help you?")]

# Add a reset button at the top
if st.button("Reset Conversation"):
    reset_conversation()
    new_id = uuid.uuid4()
    config = {"configurable": {"thread_id": new_id}}


# Loop through all messages in the session state and render them with custom icons
for msg in st.session_state["messages"]:
    if isinstance(msg, AIMessage):
        # Render assistant messages with custom icon
        with st.chat_message("assistant", avatar=ASSISTANT_ICON):
            st.write(msg.content)
    elif isinstance(msg, HumanMessage):
        # Render user messages with custom icon
        with st.chat_message("user", avatar = USER_ICON):
            st.write(msg.content)


nomad = NomadAI()
thread_id = uuid.uuid4()
config = {"configurable": {"thread_id": thread_id}}





# takes new input in chat box from user and invokes the graph
if prompt := st.chat_input():

    st.session_state.messages.append(HumanMessage(content=prompt))

    with st.chat_message("user", avatar=USER_ICON):
        st.markdown(prompt)
    # st.chat_message("user").write(prompt)

    # with st.chat_message("assistant"):
    # st_callback = get_streamlit_cb(st.container())
    # print([st_callback])
    # response = invoke_graph(st.session_state.messages, [st_callback])



    with st.chat_message("assistant", avatar=ASSISTANT_ICON):
        # assistant_message = st.chat_message('assistant')
        message_placeholder = st.markdown("Loading your travel plans...!")
        current_response = ""
        try:
            response = nomad.invoke({"input": st.session_state.messages, "chat_history": []}, config=config)

            # Ensure intermediate steps are processed correctly
            intermediate_steps = response['intermediate_steps'][-1].tool_input['summary']

            # Tokenize the summary content
            summary = response['intermediate_steps'][-1].tool_input['summary'] if intermediate_steps else "No summary provided."
            tokens = re.findall(r'\S+|\n', summary)  # Tokenize by non-whitespace or newline

            # Initialize a variable to hold the current response for display
            current_response = ""

            # Loop through the tokens and simulate streaming
            for token in tokens:
                if token == "\n":
                    # Append a newline if the token is a newline character
                    current_response += "\n"
                else:
                    # Append the token followed by a space
                    current_response += token + " "
                
                # Update the placeholder with the current response
                message_placeholder.markdown(current_response.strip(' '))  # Strip trailing spaces
                time.sleep(0.01)  # Add a slight delay for the streaming effect
        except:
            current_response = ""
            response = "I'm sorry I don't think I have the information that you requested. Could you try again please?"
            tokens = response.split()
            for token in tokens:
                current_response += token + " "
                message_placeholder.markdown(current_response.strip(' '))  # Strip trailing spaces
                time.sleep(0.01)  # Add a slight delay for the streaming effect


    # Save the final response
    st.session_state.messages.append(AIMessage(content=current_response.strip(' ')))  # Save the response if needed