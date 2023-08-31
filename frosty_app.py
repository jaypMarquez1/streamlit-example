import openai
import re
import streamlit as st
from iceprompts import get_system_prompt



st.title("Paysafe App")



# Initialize the chat messages history
openai.api_type = "azure"
openai.api_key = st.secrets.OPENAI_API_KEY
openai.api_base = st.secrets.OPENAPI_API_BASE
openai.api_version = "2023-05-15" 



# Adding some texts to explain the purpose of the app
#_______________Optionnal_______________________
st.sidebar.header('Natural language to SQL queries. ')

st.sidebar.image("snow.png", use_column_width=True)

st.sidebar.image("openai.png", use_column_width=True)
st.sidebar.write("""
         ######  This app uses streamlit and OpenAI APIs to translate natural 
            language queries into SQL statements with ease. Simply input your natural language query, and our app will generate the corresponding SQL statement for you to execute.
         """)
st.header('Translate natural language to SQL queries.')
#___________________________________________________


if "messages" not in st.session_state:
    # system prompt includes table information, rules, and prompts the LLM to produce
    # a welcome message to the user.
    st.session_state.messages = [{"role": "system", "content": get_system_prompt()}]

# Prompt for user input and save
if prompt := st.chat_input():
    st.session_state.messages.append({"role": "user", "content": prompt})

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
        for delta in openai.ChatCompletion.create(
            deployment_id = "gpt-35-turbo-16k_icicle2",
            model="gpt-3.5-turbo",
            messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
            stream=True,
        ):
            response += delta.choices[0].delta.get("content", "")
            resp_container.markdown(response)

        message = {"role": "assistant", "content": response}
        # Parse the response for a SQL query and execute if available
        sql_match = re.search(r"```sql\n(.*)\n```", response, re.DOTALL)
        if sql_match:
            sql = sql_match.group(1)
            conn = st.experimental_connection("snowpark")
            message["results"] = conn.query(sql)
            st.dataframe(message["results"])
        st.session_state.messages.append(message)