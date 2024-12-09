import streamlit as st
from streamlit_chat import message
from dynllm import NomadAI, query_refiner


st.title("Nomad AI")


# Function to reset the conversation
def reset_conversation():
    st.session_state.messages = []
    st.chat_message('assistant').markdown('How can I help you?')
    st.session_state.conversation_log = []

# Add a reset button at the top
if st.button("Reset Conversation"):
    reset_conversation()

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
    st.chat_message('assistant').markdown('How can I help you?')

if 'conversation_log' not in st.session_state:
    st.session_state.conversation_log = []  # Keeps the last 3 exchanges



# Display chat messages from history
for message in st.session_state.messages:
    st.chat_message(message['role']).markdown(message['content'])

# Get user prompt
prompt = st.chat_input('Pass Your Prompt here')

if prompt:
    # Check if the prompt contains "reset"
    if "reset" in prompt.lower():
        # Clear the conversation log and chat history
        st.session_state.conversation_log.clear()
        st.session_state.messages.append({'role': 'user', 'content': prompt})
        st.session_state.messages.clear()  # Clears all past messages
        st.chat_message('user').markdown(prompt)

        response = "Conversation has been reset. How may I help you?"
        st.chat_message('assistant').markdown(response)
        st.session_state.messages.append({'role': 'assistant', 'content': response})
    else:
        # Keeps the prompt in chat
        st.chat_message('user').markdown(prompt)
        st.session_state.messages.append({'role': 'user', 'content': prompt})

        # Add a temporary loading message
        # loading_message = st.chat_message('assistant').markdown("Loading travel plans...!")

        if len(st.session_state.conversation_log) == 0:
            st.session_state.conversation_log.append(f"User: {prompt}")
            aggregated_conversation = "\n".join(st.session_state.conversation_log)
            response = NomadAI(prompt, aggregated_conversation)
        else:
            aggregated_conversation = "\n".join(st.session_state.conversation_log)
            # Refine the user query
            refined_query = query_refiner(aggregated_conversation, prompt)
            st.session_state.conversation_log.append(f"User: {refined_query}")
            # Use the refined query as input to NomadAI
            response = NomadAI(refined_query, aggregated_conversation)

        # loading_message.markdown(response)

        assistant_message = st.chat_message('assistant')
        message_placeholder = assistant_message.markdown("Loading your travel plans...!")

        current_response = ""

        for chunk in response:
            current_response += chunk
            message_placeholder.markdown(current_response)

        # Add the response to the conversation log
        st.session_state.conversation_log.append(f"Assistant: {current_response}")

        if len(st.session_state.conversation_log) > 6:
            st.session_state.conversation_log = st.session_state.conversation_log[2:]

        # Keeps the response in chat
        # st.chat_message('assistant').markdown(response)
        st.session_state.messages.append({'role': 'assistant', 'content': current_response})