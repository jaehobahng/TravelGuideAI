import streamlit as st
from streamlit_chat import message
from lang_model import invoke_graph, NomadAI
from st_callable_util import get_streamlit_cb
from langchain_core.messages import AIMessage, HumanMessage
import time
import uuid

# config = {"configurable": {"thread_id": "1"}}

st.title("Nomad AI")

if "messages" not in st.session_state:
    # default initial message to render in message state
    st.session_state["messages"] = [AIMessage(content="How can I help you?")]


# Function to reset the conversation
def reset_conversation():
    st.session_state["messages"] = [AIMessage(content="How can I help you?")]

# Add a reset button at the top
if st.button("Reset Conversation"):
    reset_conversation()
    thread_id = uuid.uuid4()
    config = {"configurable": {"thread_id": thread_id}}

# Loop through all messages in the session state and render them as a chat on every st.refresh mech
for msg in st.session_state.messages:
    # https://docs.streamlit.io/develop/api-reference/chat/st.chat_message
    # we store them as AIMessage and HumanMessage as its easier to send to LangGraph
    if type(msg) == AIMessage:
        st.chat_message("assistant").write(msg.content)
    if type(msg) == HumanMessage:
        st.chat_message("user").write(msg.content)


nomad = NomadAI()
thread_id = uuid.uuid4()
config = {"configurable": {"thread_id": thread_id}}





# takes new input in chat box from user and invokes the graph
if prompt := st.chat_input():

    st.session_state.messages.append(HumanMessage(content=prompt))
    st.chat_message("user").write(prompt)

    # with st.chat_message("assistant"):
    st_callback = get_streamlit_cb(st.container())
    print([st_callback])
    # response = invoke_graph(st.session_state.messages, [st_callback])

    


    assistant_message = st.chat_message('assistant')
    message_placeholder = assistant_message.markdown("Loading your travel plans...!")
    current_response = ""

    # response = nomad.invoke({"input": st.session_state.messages, "chat_history": []}, config={"callbacks": [st_callback]})
    response = nomad.invoke({"input": st.session_state.messages, "chat_history": []}, config=config)

    # # Ensure intermediate steps are processed correctly
    intermediate_steps = response['intermediate_steps'][-1].tool_input['summary']

    # # Process final output
    # final_output = response['intermediate_steps'][-1].tool_input['summary'] if intermediate_steps else "No summary provided."
    # if final_output:  # Check if final output is valid
    #     # formatted_output = final_output.replace("\n", "<br>")
    #     for chunk in final_output.split():
    #         current_response += chunk + " "
    #         message_placeholder.markdown(current_response.strip(), unsafe_allow_html=True)
    #         time.sleep(0.01)
        
    #     st.chat_message("assistant").write(intermediate_steps)
    #     st.session_state.messages.append(AIMessage(content=intermediate_steps))



    # Process final output
    final_output = response['intermediate_steps'][-1].tool_input['summary'] if intermediate_steps else "No summary provided."

    if final_output:
        # Split the final output by lines while preserving formatting
        formatted_chunks = final_output.split("\n")  # Split by newline characters
        current_response = ""
        
        for chunk in formatted_chunks:
            for i in chunk.strip(' '):
                current_response += i  # Append each line with a single newline
                message_placeholder.markdown(current_response.strip(' '))
                time.sleep(0.001)  # Add a slight delay for streaming effect
            current_response += "\n"
            message_placeholder.markdown(current_response.strip(' '))

        # Save the final response
        # st.chat_message("assistant").write(current_response.strip())  # Write the final full response
        st.session_state.messages.append(AIMessage(content=current_response.strip(' ')))









    # if final_output:
    #     # Split the final output by lines while preserving formatting
    #     formatted_chunks = final_output.split("\n")  # Split by newline characters
    #     current_response = ""
        
    #     for chunk in formatted_chunks:
    #         current_response += f"{chunk.strip()}\n"  # Append each line with a single newline
    #         message_placeholder.markdown(current_response.strip())
    #         time.sleep(0.03)  # Add a slight delay for streaming effect

    #     # Save the final response
    #     st.chat_message("assistant").write(current_response.strip())  # Write the final full response
    #     st.session_state.messages.append(AIMessage(content=current_response.strip()))
















    # # Process the AI's response and handles graph events using the callback mechanism
    # with st.chat_message("assistant"):
    #     # Create a new container for streaming messages only
    #     st_callback = get_streamlit_cb(st.container())
    #     response = invoke_graph(st.session_state.messages, [st_callback])

    #     # Dynamically stream intermediate steps if supported by your framework
    #     # for step in response['intermediate_steps'][-1].tool_input['summary'].split():
    #     #     # output = step['tool_input']['summary']
    #     #     st.write(step)  # Stream output directly
    #     #     st.session_state.messages.append(AIMessage(content=step))


    # final_output = response['intermediate_steps'][-1].tool_input['summary']
    # st.chat_message("assistant").write(final_output)
    # st.session_state.messages.append(AIMessage(content=final_output))







    # # Process the AI's response and handles graph events using the callback mechanism
    # with st.chat_message("assistant"):
    #     # create a new container for streaming messages only, and give it context
    #     st_callback = get_streamlit_cb(st.container())
    #     response = invoke_graph(st.session_state.messages, [st_callback])

    #     output = response['intermediate_steps'][-1].tool_input['summary']
    #     # Add that last message to the st_message_state
    #     # Streamlit's refresh the message will automatically be visually rendered bc of the msg render for loop above
    #     st.session_state.messages.append(AIMessage(content=output))
    #     st.session_state.messages.append({'role': 'assistant', 'content': output})