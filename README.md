# Nomad AI
Your personal travel guide

## Manual Nomad
A travel guide system was designed by seamlessly integrating four specialized Large Language Models and three distinct API calls. Here's how the system works:

1. **Receptionist**  
   - Acts as the first point of interaction, ensuring user inputs contain the minimum required information for API calls. If details are insufficient, it prompts the user for clarification or additional information.

2. **Parser**  
   - Processes and structures user inputs into a standardized JSON format, making it easy to pass variables into the relevant API calls.

3. **Respondent**  
   - Takes the API output and transforms it into natural, conversational language, delivering clear and engaging responses to the user.

4. **Query Refiner**  
   - Enables a chat-like conversational experience with memory by rephrasing user inputs based on the context of previous interactions. This ensures continuity and a smoother conversation flow after the initial query.

This system creates a dynamic and intuitive travel planning experience, leveraging the strengths of LLMs for efficient interaction and API integration.

 ```
# Within the manual_nomad directory run the following command
streamlit run app.py
 ```

## Langchain Nomad
The system's functionality was further streamlined by leveraging LangChain, a robust framework designed for seamless interaction between language models. By implementing LangChain, a single Large Language Model was orchestrated to perform all four specialized roles—Receptionist, Parser, Respondent, and Query Refiner—within a cohesive workflow

 ```
# Within the langchain_nomad directory run the following command
streamlit run langapp.py
 ```

## Install requirements

 - **Amadeus API key must be present in .env file to run both models**
 - **Ollama with llama 3.2 must be installed locally to run manual_nomad**
 - **OpenAI API keey must be present in .env file of langchain_nomad to run langchain_nomad**
 - **Install python packages with requirements.txt**
```
pip install requirements.txt
```

## Repository structure

```
.
├── __pycache__/
├── images/
├── langchain_nomad/
│   ├── __pycache__/
│   ├── .streamlit/
│   ├── .env
│   ├── lang_model.py
│   ├── langapp.py
│   └── langchain.ipynb
├── manual_nomad/
│   ├── __pycache__/
│   ├── .streamlit/
│   ├── .env
│   ├── app.py
│   ├── dynllm.py
│   └── manual.ipynb
├── .cache.sqlite
├── .gitignore
├── api_test.ipynb
├── README.md
└── requirements.txt

```