import streamlit as st
from streamlit_chat import message
from dynllm import NomadAI, query_refiner


st.title("Nomad AI")

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'conversation_log' not in st.session_state:
    st.session_state.conversation_log = []  # Keeps the last 3 exchanges

# Display chat messages from history
for message in st.session_state.messages:
    st.chat_message(message['role']).markdown(message['content'])

# Get user prompt
prompt = st.chat_input('Pass Your Prompt here')

if prompt:
    # Keeps the prompt in chat
    st.chat_message('user').markdown(prompt)
    st.session_state.messages.append({'role': 'user', 'content': prompt})

    if len(st.session_state.conversation_log) == 0:
        st.session_state.conversation_log.append(f"User: {prompt}")
        aggregated_conversation = "\n".join(st.session_state.conversation_log)
        response = NomadAI(prompt, aggregated_conversation)
    else:
        # if len(st.session_state.conversation_log) > 6:
        #     st.session_state.conversation_log.pop(0)
        aggregated_conversation = "\n".join(st.session_state.conversation_log)
        # Refine the user query
        refined_query = query_refiner(aggregated_conversation, prompt)
        st.session_state.conversation_log.append(f"User: {refined_query}")
        # Use the refined query as input to NomadAI
        response = NomadAI(refined_query, aggregated_conversation)


    # Add the response to the conversation log
    st.session_state.conversation_log.append(f"Assistant: {response}")

    if len(st.session_state.conversation_log) > 6:
        st.session_state.conversation_log = st.session_state.conversation_log[2:]

    # Keeps the response in chat
    st.chat_message('assistant').markdown(response)
    st.session_state.messages.append({'role': 'assistant', 'content': response})