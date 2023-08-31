import re
import streamlit as st
import pandas as pd
from prompts import get_system_prompt
import openai
import logging
import uuid
import datetime
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', filename='frosty.log', encoding='utf-8', level=logging.DEBUG)

openai.api_type = "azure"
openai.api_base = "https://oai-dev2.openai.azure.com/"
openai.api_version = "2023-03-15-preview"


st.title("☃️ Icicle")
# Initialize the chat messages history
openai.api_key = st.secrets.OPENAI_API_KEY
if "messages" not in st.session_state:
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
        temperature=0,
        messages=messages,
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
            conn = st.experimental_connection("snowpark")
            message["results"] = conn.query(sql)
            st.dataframe(message["results"])
        st.session_state.messages.append(message)





# Load existing feedback data from CSV if available
if "feedback_data" not in st.session_state:
    try:
        existing_feedback_df = pd.read_csv("feedback.csv")
        st.session_state.feedback_data = existing_feedback_df.to_dict(orient="records")
    except FileNotFoundError:
        st.session_state.feedback_data = []

# Generate a new session ID when the app is initialized or refreshed
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# Feedback functionality
feedback = st.text_input("Feedback:")

# Radio buttons for thumbs up and thumbs down
feedback_choice = st.radio("Choose Feedback:", ["👍", "👎"])

thumbs_up = feedback_choice == "👍"
thumbs_down = feedback_choice == "👎"

if st.button("Submit Feedback"):
    user_message = ""
    assistant_message = ""
    system_message = ""
    for i, message in enumerate(st.session_state.messages[st.session_state.num_messages_written:], start=st.session_state.num_messages_written):
        if message["role"] == "user":
            user_message = message["content"]
        elif message["role"] == "assistant":
            assistant_message = message["content"]
        elif message["role"] == "system":
            system_message = message["content"]

    timestamp = datetime.datetime.now()  # Get the current timestamp
    feedback_entry = {
        "Timestamp": timestamp,  # Include the timestamp
        "Session_ID": st.session_state.session_id,
        "ID": len(st.session_state.feedback_data) + 1,
        "User_Message": user_message,
        "Assistant_Message": assistant_message,
        "Prompt": system_message,
        "Feedback": feedback,
        "Thumbs_Up": thumbs_up,
        "Thumbs_Down": thumbs_down
    }

    st.session_state.feedback_data.append(feedback_entry)

    # Update the DataFrame and write to Excel
    feedback_df = pd.DataFrame(st.session_state.feedback_data)
    feedback_df["Thumbs_Up"] = feedback_df["Thumbs_Up"].apply(lambda x: "TRUE" if x else "FALSE")
    feedback_df["Thumbs_Down"] = feedback_df["Thumbs_Down"].apply(lambda x: "TRUE" if x else "FALSE")
    feedback_df.to_csv("feedback.csv", index=False)

    st.write("Feedback submitted!")















logging.info(" =====  START OF MSG SESSION STATE  ====  ")

logging.info(st.session_state.messages)

logging.info(" =====  END OF MSG SESSION STATE  ====  ")