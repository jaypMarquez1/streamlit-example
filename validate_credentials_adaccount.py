
import openai
import re
import streamlit as st
from prompts import get_system_prompt
from streamlit_azure_login import login_component

st.title("☃️ Frosty")


# Request credential
default_credential = DefaultAzureCredential()
token = default_credential.get_token("https://cognitiveservices.azure.com/.default")

# Setup parameters
openai.api_type = "azure_ad"
openai.api_key = token.token

st.button('connect_button')
  
if "messages" not in st.session_state:
    # system prompt includes table information, rules, and prompts the LLM to produce
    # a welcome message to the user.
    st.session_state.messages = [{"role": "system", "content": get_system_prompt()}]
if st.session_state.connected is False:
  
        try:
            conn = st.experimental_connection("snowpark", user=username)
            conn.query("select current_warehouse()")
            
            st.session_state.connection = conn
            st.session_state.connected = True
        except:
            st.info("Please connect with your paysafe email.")
            st.stop()
        # pass

print("+++++    SECRETS ++++\n", st.secrets, "\n+++++    SECRETS ++++\n")
print("++++++++++++ USENAME:", username)

'''
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
        st.session_state.messages.append(message)'''