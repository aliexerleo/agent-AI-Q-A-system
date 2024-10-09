from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent


import streamlit as st
from dotenv import load_dotenv
load_dotenv()
import os 

# database credentials
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')
DB_PORT = os.getenv('DB_PORT')
DB_HOST = os.getenv('DB_HOST')

# establishing connection
pg_uri = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
db = SQLDatabase.from_uri(pg_uri)

# specific LLM 
llm = ChatOpenAI(model_name='gpt-4o-mini-2024-07-18')

# complemets Tools 
toolkit = SQLDatabaseToolkit(db=db, llm=llm)
tools = toolkit.get_tools()


SQL_PREFIX_TEMPLATE = """You are an agent designed to interact with a SQL database.
Given an input question, create a syntactically correct SQL query to run, then look at the results of the query and return the answer.
Unless the user specifies a specific number of examples they wish to obtain, always limit your query to at most 20 results.
You can order the results by a relevant column to return the most interesting examples in the database.
Never query for all the columns from a specific table, only ask for the relevant columns given the question.
You have access to tools for interacting with the database.
Only use the below tools. Only use the information returned by the below tools to construct your final answer.
You MUST double check your query before executing it. If you get an error while executing a query, rewrite the query and try again.

DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.

To start you should ALWAYS look at the tables in the database to see what you can query.
Do NOT skip this step.
Then you should query the schema of the most relevant tables."""


system_message = SystemMessage(content=SQL_PREFIX_TEMPLATE)

# initialization the agent
agent_executor = create_react_agent(llm, tools, state_modifier=system_message)


# UI 
st.set_page_config(page_title="AI Assistant", layout="wide")

# Store LLM generated responses
if "messages" not in st.session_state.keys():
    st.session_state.messages = [{"role": "assistant", "content": "How can I help you today?"}]

# Display or clear chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# validate user questio or input message
if prompt := st.chat_input(''):
    st.chat_message('user').markdown(prompt)
    st.session_state.messages.append({'role':'user', 'content': prompt})
    with st.spinner("Processing..."):
        raw_response = agent_executor.stream({"messages": [HumanMessage(content=prompt)]}, {"recursion_limit": 200})  
        result_list = list(raw_response) 
        final_response = result_list[-1]
        content = final_response['agent']['messages'][0].content

        with st.chat_message('assistant'):
            st.markdown(content)

        st.session_state.messages.append({'role': 'assisteant', 'content': content})

# clear all messages
def clear_chat_history():
    st.session_state.messages = [{"role": "assistant", "content": "How can I help you today?"}]
st.sidebar.button("Clear Chat History", on_click=clear_chat_history, type="secondary" )
