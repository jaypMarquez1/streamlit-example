# from langchain.llms.openai import OpenAI
# from langchain.agents import create_sql_agent
# from langchain.sql_database import SQLDatabase
# from langchain.agents.agent_types import AgentType
# from langchain.callbacks import StreamlitCallbackHandler
# from langchain.agents.agent_toolkits import SQLDatabaseToolkit

import re
import streamlit as st
from prompts import get_system_prompt
import openai
import logging
import csv
import toml

openai.api_type = "azure"
openai.api_base = "https://oai-dev2.openai.azure.com/"
openai.api_version = "2023-03-15-preview"
openai.api_key = st.secrets.OPENAI_API_KEY

st.set_page_config(page_title="Paysafe Icicle", page_icon="☃️")
st.title("☃️ Paysafe Icicle")

# username = st.sidebar.text_input("Paysafe email:")
# connect_button = st.sidebar.button("Connect")
# domain = st.selectbox("Table:",["DM","LOG_AI"])
# if "connected" not in st.session_state:
#     st.session_state.connected = False

# if st.session_state.connected is False:
#     if connect_button:
#         if domain == "DM":
#             try: 
#                 try:
#                     conn = st.experimental_connection("snowpark", user=username, schema="DM")
#                     conn.query("select current_warehouse()")
            
#                     st.session_state.connection = conn
#                     st.session_state.connected = True
#                 except:
#                     st.info("Please connect with your paysafe email.")
#                     st.stop()
#             else:
#                     st.info("Please connect with your paysafe email.")
#         if domain == "LOG_AI":
#             try:
#                 try:
#                     conn = st.experimental_connection("snowpark", user=username, schema="LOG_AI")
#                     conn.query("select current_warehouse()")
            
#                     st.session_state.connection = conn
#                     st.session_state.connected = True
#                 except:
#                     st.info("Please connect with your paysafe email.")
#                     st.stop()
#     else:
#         st.info("Please connect with your paysafe email.")
#         st.stop()
        # pass

# print("+++++    SECRETS ++++\n", st.secrets, "\n+++++    SECRETS ++++\n")
# print("++++++++++++ USENAME:", username)
# conn = st.experimental_connection("snowpark", user=username)


# if st.session_state.connected is False:
#     if connect_button:
#         try:
#             conn = st.experimental_connection("snowpark", user=username)
#             conn.query("select current_warehouse()")
            
#             st.session_state.connection = conn
#             st.session_state.connected = True
#         except:
#             st.info("Please connect with your paysafe email.")
#             st.stop()
#     else:
#         st.info("Please connect with your paysafe email.")
#         st.stop()

import streamlit as st

def establish_connection(secrets):
    try:
        conn = st.experimental_connection("snowpark", user=secrets["user"], schema=secrets["schema"])
        conn.query("select current_warehouse()")
        st.session_state.connection = conn
        st.session_state.connected = True
    except:
        st.info("Please connect with your paysafe email.")
        st.stop()

st.sidebar.title("Connection")
username = st.sidebar.text_input("Paysafe email:")
connect_button = st.sidebar.button("Connect")

st.sidebar.title("Table Selection")
domain = st.selectbox("Table:", ["DM", "LOG_AI"])

if "connected" not in st.session_state:
    st.session_state.connected = False

if not st.session_state.connected:
    if connect_button:
        if domain == "DM":
            secrets_file = "C:\\Users\\matthewlewington\\.streamlit\\secrets.toml"
        elif domain == "LOG_AI":
            secrets_file = "C:\\Users\\matthewlewington\\.streamlit\\secrets_log_ai.toml"
        
        try:
            with open(secrets_file) as f:
                secrets = toml.load(f)
            establish_connection(secrets)
        except FileNotFoundError:
            st.info("Secrets file not found.")
else:
    st.info("You are already connected.")

st.sidebar.markdown("---")
st.sidebar.text("Sidebar content...")


# def establish_connection(username, schema):
#     try:
#         conn = st.experimental_connection("snowpark", user=username, schema=domain)
#         conn.query("select current_warehouse()")
#         st.session_state.connection = conn
#         st.session_state.connected = True
#     except:
#         st.info("Please connect with your paysafe email.")
#         st.stop()

# st.sidebar.title("Connection")
# username = st.sidebar.text_input("Paysafe email:")
# connect_button = st.sidebar.button("Connect")

# st.sidebar.title("Table Selection")
# domain = st.selectbox("Table:", ["DM", "LOG_AI"])

# if "connected" not in st.session_state:
#     st.session_state.connected = False

# if st.session_state.connected is False:
#     if connect_button:
#         if domain == "DM":
#             establish_connection(username, "DM")
#         elif domain == "LOG_AI":
#             establish_connection(username, "LOG_AI")
#     else:
#         st.info("You are already connected.")
#         st.stop()
# st.sidebar.markdown("---")
# st.sidebar.text("Sidebar content...")

















######## FROSTY CODE

if "messages" not in st.session_state:
    # system prompt includes table information, rules, and prompts the LLM to produce
    # a welcome message to the user.
    st.session_state.messages = [{"role": "system", "content": get_system_prompt()}]

# Get the number of messages already written to the CSV file
if "num_messages_written" not in st.session_state:
    st.session_state.num_messages_written = 0

# Prompt for user input and save
if prompt := st.chat_input():
    st.session_state.messages.append({"role": "user", "content": prompt})


def query_openai(messages):
    response = ""
    for delta in openai.ChatCompletion.create(
        engine='gpt-35-turbo-16k_icicle2',
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.1,
        stream=True,
    ):
        response += delta.choices[0].delta.get("content", "")
    return response


# display the existing chat messages
for message in st.session_state.messages:
    if message["role"] == "system":
        continue
    with st.chat_message(message["role"]):
        st.write(message["content"])
        if "results" in message:
            st.dataframe(message["results"])

# If last message is not from assistant, we need to generate a new response
if st.session_state.messages[-1]["role"] != "assistant":
    with st.chat_message("assistant"):
        response = ""
        resp_container = st.empty()

        messages_to_send = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
        while len(messages_to_send) > 0:
            # Split the conversation into a smaller context window
            chunked_messages = messages_to_send[:10]  # Set this to an appropriate number of tokens (e.g., 10)
            messages_to_send = messages_to_send[len(chunked_messages):]

            # Query OpenAI with the current context window
            response += query_openai(chunked_messages)
            resp_container.markdown(response)

        message = {"role": "assistant", "content": response}
        # Parse the response for a SQL query and execute if available
        sql_match = re.search(r"```sql\n(.*)\n```", response, re.DOTALL)
        if sql_match:
            sql = sql_match.group(1)
            conn = st.session_state.connection
            message["results"] = conn.query(sql)
            st.dataframe(message["results"])
        st.session_state.messages.append(message)



# Feedback functionality
feedback = st.text_input("Feedback:")
thumbs_up = st.button("👍")
thumbs_down = st.button("👎")

# Initialize a set to keep track of messages that have received feedback
if "feedback_messages" not in st.session_state:
    st.session_state.feedback_messages = set()

if st.button("Submit Feedback"):
    # Get the index of the last message (the one with feedback)
    last_message_index = len(st.session_state.messages) - 1

    # Check if feedback for the last message has already been submitted
    if last_message_index in st.session_state.feedback_messages:
        st.write("Feedback already submitted for this message.")
    else:
        # Add the message index to the set to indicate that feedback has been submitted
        st.session_state.feedback_messages.add(last_message_index)

        # Prepare the data for pivoting
        pivot_data = []
        user_message = ""
        assistant_message = ""
        for i, message in enumerate(st.session_state.messages[st.session_state.num_messages_written:], start=st.session_state.num_messages_written):
            if message["role"] == "user":
                user_message = message["content"]
            elif message["role"] == "assistant":
                assistant_message = message["content"]

            pivot_data.append({
                "user": user_message,
                "assistant": assistant_message,
                "system": message["content"] if message["role"] == "system" else "",
                "results": message.get("results", ""),
                "feedback": "",
                "thumbs_up": thumbs_up,
                "thumbs_down": thumbs_down,
            })

        # Write the pivoted data to the CSV file
        with open("feedback.csv", "a+", newline="") as csvfile:
            fieldnames = ["user", "assistant", "system", "results", "feedback", "thumbs_up", "thumbs_down"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if csvfile.tell() == 0:
                writer.writeheader()
            writer.writerows(pivot_data)

        # Write the feedback to CSV file
        with open("feedback.csv", "a", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([feedback, thumbs_up, thumbs_down])

        st.write("Feedback submitted!")









logging.info(" =====  START OF MSG SESSION STATE  ====  ")

logging.info(st.session_state.messages)

logging.info(" =====  END OF MSG SESSION STATE  ====  ")
