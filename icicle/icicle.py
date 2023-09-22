import re
import time
import streamlit as st
import pandas as pd
from pandas.io.formats.style import Styler
from prompts import get_system_prompt, get_snowflakeerror_prompt, get_summary_prompt
import openai
import logging
import uuid
import datetime
from snowflake.snowpark.exceptions import SnowparkSQLException
import snowflake.connector
import tiktoken
from streamlit_extras.app_logo import add_logo
from sqlglot import parse_one, exp
from msal_streamlit_authentication import msal_authentication

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', filename='frosty.log', encoding='utf-8', level=logging.INFO)

openai.api_type = "azure"
openai.api_base = "https://oai-dev2.openai.azure.com/"
openai.api_version = "2023-03-15-preview"

custom_theme = f"""
  
    <style>
    .stApp {{
        background-color: #F8F9FE;  /* Change to your desired background color */
    }}
    
    .css-uc1cuc {{
        background-color: #F8F9FE;  /* Change to your desired header background color */
        color: var(--light-mode-core-text-only-body-copy,#333);  /* Change text color to contrast with the header background */
        font-family: Source Sans Pro;
        font-size: 14px;
        font-style: normal;
        font-wieght: 600;
        line-hieght: 16px;/*114.286%*/
    }}
    .css-j7ljls {{
        background-color: #F8F9FE;  /* Change to your desired header background color */
        color: var(--light-mode-core-text-only-body-copy,#333);  /* Change text color to contrast with the header background */
        font-family: Source Sans Pro;
        font-size: 14px;
        font-style: normal;
        font-wieght: 600;
        line-hieght: 16px;/*114.286%*/
    }}
    .css-1c7y2kd {{
        background-color: #E5E6F8;  /* Change to your desired header background color */
        color: var(--light-mode-core-text-only-body-copy,#333);  /* Change text color to contrast with the header background */
        font-family: Source Sans Pro;
        font-size: 14px;
        font-style: normal;
        font-wieght: 600;
        line-hieght: 16px;/*114.286%*/    
    }}
    .css-1x5kdwo {{
        background-color: #F2F1FD;  /* Change to your desired header background color */
        color: var(--light-mode-core-text-only-body-copy,#333);  /* Change text color to contrast with the header background */
        font-family: Source Sans Pro;
        font-size: 14px;
        font-style: normal;
        font-wieght: 600;
        line-hieght: 16px;/*114.286%*/    
    }}
    .css-18ni7ap {{
        background-color: #F8F9FE;  /* Change to your desired header background color */
        color: var(--light-mode-core-text-only-body-copy,#333);  /* Change text color to contrast with the header background */
        font-family: Source Sans Pro;
        font-size: 14px;
        font-style: normal;
        font-wieght: 600;
        line-hieght: 16px;/*114.286%*/
        [data-testid="stSidebarNav"]
        background-image: url('img/Group.png');
        display: flex;
        width: 82.325px;
        height: 34px;
        padding: 9.435px 9.71px 9.435px 9.709px;
        justify-content: center;
        align-items: center;
        flex-shrink: 0;
        }}
    .css-90vs21 {{
        background-color: #F8F9FE;  /* Change to your desired header background color */
        color: var(--light-mode-core-text-only-body-copy,#333);  /* Change text color to contrast with the header background */
        font-family: Source Sans Pro;
        font-size: 14px;
        font-style: normal;
        font-wieght: 600;
        line-hieght: 16px;/*114.286%*/
        }}


    .stImage {{
        display: flex;
        width: 282.325px;
        height: 34px;
        padding: 9.435px 9.71px 9.435px 9.709px;
        justify-content: center;
        align-items: center;
        flex-shrink: 0;}}

   </style>

          """
    
logo_url = "icicle_streamlit/assets/paysafe_logo.png"
st.image(logo_url)

st.markdown(custom_theme, unsafe_allow_html=True)

st.title("🧊Icicle")

# Initialize the sso authentication
if "session_value" not in st.session_state:
  st.session_state.session_value = None

if st.session_state.session_value == None:
    with st.spinner("Authenticating"):
        value = msal_authentication(
            auth={
                "clientId": st.secrets.SSO_CLIENT_ID,
                "authority": st.secrets.SSO_AUTHORITY,
                "redirectUri": "/",
                "postLogoutRedirectUri": "/"
            },
            cache={
                "cacheLocation": "sessionStorage",
                "storeAuthStateInCookie": False
            },
            login_request={
                "scopes": [st.secrets.SSO_SCOPES]
            },
            class_name="stButton",
            key=1
        )
        if value != None:
            st.session_state.session_value = value
            st.session_state.is_authenticated = True
            st.experimental_rerun()
        else:
            time.sleep(1)
            st.warning("You must authenticate before proceeding!")
            st.stop()

# Initialize the chat messages history
openai.api_key = st.secrets.OPENAI_API_KEY
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": get_system_prompt()}]

# Get the number of messages already written to the Snowflake
if "num_messages_written" not in st.session_state:
    st.session_state.num_messages_written = 0

# Generate a new session ID when the app is initialized or refreshed
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# Prompt for user input and save
if prompt := st.chat_input():
    st.session_state.messages.append({"role": "user", "content": prompt})

# Source: https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
def num_tokens_from_messages(messages, model="gpt-3.5-turbo-0613"):
    """Return the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        print("Warning: model not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    if model in {
        "gpt-3.5-turbo-0613",
        "gpt-3.5-turbo-16k-0613",
        "gpt-4-0314",
        "gpt-4-32k-0314",
        "gpt-4-0613",
        "gpt-4-32k-0613",
        }:
        tokens_per_message = 3
        tokens_per_name = 1
    elif model == "gpt-3.5-turbo-0301":
        tokens_per_message = 4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
        tokens_per_name = -1  # if there's a name, the role is omitted
    elif "gpt-3.5-turbo" in model:
        print("Warning: gpt-3.5-turbo may update over time. Returning num tokens assuming gpt-3.5-turbo-0613.")
        return num_tokens_from_messages(messages, model="gpt-3.5-turbo-0613")
    elif "gpt-4" in model:
        print("Warning: gpt-4 may update over time. Returning num tokens assuming gpt-4-0613.")
        return num_tokens_from_messages(messages, model="gpt-4-0613")
    else:
        raise NotImplementedError(
            f"""num_tokens_from_messages() is not implemented for model {model}. See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens."""
        )
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
    return num_tokens

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

def insert_system_prompt(system_message):
    conn = snowflake.connector.connect(
        account=st.secrets.connections.snowpark.account,
        user=st.secrets.connections.snowpark.user,
        password=st.secrets.connections.snowpark.password,
        database=st.secrets.connections.snowpark.database,
        schema='LOG_AI',
        warehouse=st.secrets.connections.snowpark.warehouse,
        role='DEV_FR_ICICLE'
    )

    cursor = conn.cursor()

    # Check if the system_message already exists
    cursor.execute("SELECT id FROM SYSTEM_MESSAGE_HISTORY WHERE system_message = %s", (system_message,))
    result = cursor.fetchone()

    if result:
        system_message_id = result[0]
    else:
        # Insert the system prompt into the SYSTEM_MESSAGE_HISTORY table without specifying the 'id' columnn
        cursor.execute("""
        INSERT INTO SYSTEM_MESSAGE_HISTORY (system_message)
        VALUES (%s)
        """, (system_message,))

        # Retrieve the ID of the newly inserted prompt
        cursor.execute("SELECT id FROM SYSTEM_MESSAGE_HISTORY WHERE system_message = %s", (system_message,))
        result = cursor.fetchone()
        system_message_id = result[0]

    conn.commit()
    conn.close()

    return system_message_id

message_id = str(uuid.uuid4())
system_message = get_system_prompt()
system_message_id = insert_system_prompt(system_message)

def write_messages_to_snowflake(user_message, assistant_message):

    

    timestamp = datetime.datetime.now()  

    conn = snowflake.connector.connect(
        account=st.secrets.connections.snowpark.account,
        user=st.secrets.connections.snowpark.user,
        password=st.secrets.connections.snowpark.password,
        database=st.secrets.connections.snowpark.database,
        schema='LOG_AI',
        warehouse=st.secrets.connections.snowpark.warehouse,
        role='DEV_FR_ICICLE'
    )

    cursor = conn.cursor()

    cursor.execute(f"SELECT MAX(message_id) FROM MESSAGE_LOG WHERE session_id='{st.session_state.session_id}'")
    result = cursor.fetchone()
    max_id = result[0] if result[0] is not None else 0
    new_id = str(max_id + 1)

    

    # Initialize Snowflake connection
    log_entry = {
        "timestamp": timestamp,
        "session_id": st.session_state.session_id,
        "id": message_id,
        "message_id": new_id,
        "user_message": user_message["content"],
        "assistant_message": assistant_message["content"],
        "system_message_id": system_message_id,
        "username": st.session_state.session_value["account"]["username"]
    }

    # Insert feedback data from icicle into the Snowflake
    append_query = """
    INSERT INTO MESSAGE_LOG (
        timestamp,
        session_id,
        id,
        message_id,
        user_message,
        assistant_message,
        system_message_id,
        username
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """

    cursor.execute(append_query, (
        log_entry["timestamp"],
        log_entry["session_id"],
        log_entry["id"],
        log_entry["message_id"],
        log_entry["user_message"],
        log_entry["assistant_message"],
        log_entry["system_message_id"],
        log_entry["username"]
    ))

    conn.commit()
    conn.close()


# same dataframe will be formatted the same way, so we can use a cache 
def format_dataframe(df:pd.DataFrame, sql:str) -> Styler: 
    #st.dataframe(df) # show additional unformated dataframe for debugging

    # Define the format dictionary
    format_dict = {
        "date": "{:%Y-%m-%d}",
        "int": "{:,d}",
        "float": "{:,.2f}",
        "string": "{:s}"
    }

    # Define keyword based format dictionary
    key_format_dict = {
        "revenue": "{:,.2f}",
        "year": "{:d}",
        "date": "{:%Y-%m-%d}",
        "percent": "{:,.2f}%",
    }
    # make the index start with 1 instead of 0
    df.index += 1 
    # infer the data type of the data frame using infer_objects() method
    df = df.convert_dtypes(infer_objects=True, convert_string=True, convert_integer=True, convert_boolean=True, convert_floating=True)
    df = df.infer_objects()

    # categorise columns as dimensions and measures
    groupbycolumns = []
    dimensions = []
    measures = []
    for group in parse_one(sql).find_all(exp.Group):
        for col in group.expressions:
            groupbycolumns.append(col.name.lower())

    for col in df.columns:
        if col.lower() in groupbycolumns:
            dimensions.append(col)
        elif pd.api.types.is_string_dtype(df[col].dtype) and not pd.api.types.is_object_dtype(df[col].dtype):
            dimensions.append(col)
        else: 
            measures.append(col)

    styled_columns = {}
    # format dimensions as string
    for col in dimensions:
        styled_columns[col] = format_dict["string"]
    
    # first try to convert remaining object types into their respective data types (hard convert)
    for col in measures:
        if pd.api.types.is_object_dtype(df[col].dtype):
            df[col] = df[col].apply(pd.to_datetime, errors='ignore')
            if not pd.api.types.is_object_dtype(df[col].dtype): continue
            df[col] = df[col].apply(pd.to_numeric, errors='ignore')

    # set format based on data types
    for col in measures:
        if pd.api.types.is_datetime64_dtype(df[col].dtype):
            styled_columns[col] = format_dict["date"]
        elif pd.api.types.is_integer_dtype(df[col].dtype):
            styled_columns[col] = format_dict["int"]
        elif pd.api.types.is_float_dtype(df[col].dtype):
            styled_columns[col] = format_dict["float"]

        # Key based formatting (keep out for now)
        for key in key_format_dict:
            if key in col.lower():
                styled_columns[col] = key_format_dict[key]
                break

    return df.style.format(styled_columns, na_rep="")

# display the existing chat messages
for message in st.session_state.messages:
    if message["role"] == "system":
        continue
    with st.chat_message(message["role"]):
        st.write(message["content"])
        if "results" in message:
            st.dataframe(message["results"])


max_tokens_before_summary = 16000
messages_to_exclude_from_summary = 5
max_retries = 3
num_retries = 0
# If last message is not from assistant, we need to generate a new response
while num_retries < max_retries and st.session_state.messages[-1]["role"] != "assistant":
    try:
        with st.chat_message("assistant"):
            response = ""
            resp_container = st.empty()

            # Summarize messages
            messages_to_send = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
            num_tokens = num_tokens_from_messages(messages_to_send, model="gpt-3.5-turbo-16k-0613")
            # print(f"messages: {len(messages_to_send)}, tokens: {num_tokens}")
            if num_tokens > max_tokens_before_summary:
                summary_size = len(st.session_state.messages) - messages_to_exclude_from_summary
                messages_to_summerize = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[:summary_size]]
                messages_to_summerize.append({"role": "user", "content": get_summary_prompt()})
                response = query_openai(messages_to_summerize)
                message = {"role": "assistant", "content": response}
                
                # remove messages that are summarized from the state
                del st.session_state.messages[1:summary_size]
                # insert summary message after system message [0]
                st.session_state.messages.insert(1, message)
                
            # Query OpenAI with the current context window
            response = query_openai(messages_to_send)
            resp_container.markdown(response)
            message = {"role": "assistant", "content": response}

            # Parse the response for a SQL query and execute if available
            sql_match = re.search(r"```sql\n(.*)\n```", response, re.DOTALL)
            if sql_match:
                sql = sql_match.group(1)
                conn = st.experimental_connection("snowpark")
                message["sql"] = sql
                df = conn.query(sql)
                message["results"] = format_dataframe(df, sql)
                st.dataframe(message["results"])
                num_retries = 0

            write_messages_to_snowflake(user_message=st.session_state.messages[-1], assistant_message=message)

    except SnowparkSQLException as e:
        num_retries += 1
        st.session_state.messages.append(message)
        message = {"role": "user", "content": get_snowflakeerror_prompt(e.message)}
        with st.chat_message(message["role"]):
            st.write(message["content"])
    finally:
        st.session_state.messages.append(message)


# If previous message has results, try to visualize them
if "results" in st.session_state.messages[-1]:
    graph_option = st.selectbox("Select Visuals", ["None", "Bar Chart", "Line Chart"])
    if graph_option != "None" :
        graph_data = message["results"]
        groupbycolumns = []
        measures = []
        dimensions = []
        dimension = ""
        
        for group in parse_one(st.session_state.messages[-1]["sql"]).find_all(exp.Group):
            for col in group.expressions:
                groupbycolumns.append(col.name.lower())

        for col in graph_data.columns:
            if col.lower() in groupbycolumns:
                dimensions.append(col)
            else: 
                measures.append(col)

        if len(dimensions) > 1:
            dimension = st.selectbox("Select Dimension", dimensions)
        else:
            dimension = (dimensions or [""])[0]

        if graph_option == "Line Chart" :
            st.line_chart(data=graph_data, y=measures, x=dimension)
        else:
            st.bar_chart(data=graph_data, y=measures, x=dimension)
    

##### Feedback

if "feedback_data" not in st.session_state:
    st.session_state.feedback_data = []

def submit():
    feedback_choice = st.session_state.feedback_choice
    feedback = st.session_state.feedback
    thumbs_up = feedback_choice == "👍"
    thumbs_down = feedback_choice == "👎"

    user_message = ""
    assistant_message = ""
    for i, message in enumerate(st.session_state.messages[st.session_state.num_messages_written:], start=st.session_state.num_messages_written):
        if message["role"] == "user":
            user_message = message["content"]
        elif message["role"] == "assistant":
            assistant_message = message["content"]

    timestamp = datetime.datetime.now()

    conn = snowflake.connector.connect(
        account=st.secrets.connections.snowpark.account,
        user=st.secrets.connections.snowpark.user,
        password=st.secrets.connections.snowpark.password,
        database=st.secrets.connections.snowpark.database,
        schema='LOG_AI',
        warehouse=st.secrets.connections.snowpark.warehouse,
        role='DEV_FR_ICICLE'
    )
    cursor = conn.cursor()

    # Initialize Snowflake connection
    feedback_entry = {
        "feedback_timestamp": timestamp,
        "session_id": st.session_state.session_id,
        "message_id": message_id,
        "user_message": user_message,
        "assistant_message": assistant_message,
        "system_message_id": system_message_id,
        "feedback": feedback,
        "thumbs_up": thumbs_up,
        "thumbs_down": thumbs_down,
        "username": st.session_state.session_value["account"]["username"]
    }

    # Insert feedback data into Snowflake
    append_query = """
    INSERT INTO feedback_log (
        feedback_timestamp,
        session_id,
        message_id,
        user_message,
        assistant_message,
        system_message_id,
        feedback,
        thumbs_up,
        thumbs_down,
        username
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    cursor.execute(append_query, (
        feedback_entry["feedback_timestamp"],
        feedback_entry["session_id"],
        feedback_entry["message_id"],
        feedback_entry["user_message"],
        feedback_entry["assistant_message"],
        feedback_entry["system_message_id"],
        feedback_entry["feedback"],
        feedback_entry["thumbs_up"],
        feedback_entry["thumbs_down"],
        feedback_entry["username"]

    ))

    conn.commit()

    st.write("Feedback submitted!")

    conn.close()



with st.expander("Provide Feedback"):
    with st.form(key="feedback_form", clear_on_submit=True):
        st.session_state.feedback_choice = st.radio("Choose Feedback:", ["👍", "👎"])
        st.session_state.feedback = st.text_input("Feedback:")

        if st.form_submit_button("Submit Feedback"):
            submit()

col1, col2, col3 , col4, col5 = st.columns(5)

with col1:
    pass
with col2:
    pass
with col4:
    pass
with col5:
    pass
with col3 :
    if st.button(" 🗑️ Clear Chat"):
        st.session_state.messages = st.session_state.messages[:2]
        st.experimental_rerun()

    ## Logout Button 
    ## Peter: caused me endless loops so I commented it out.
    # value = msal_authentication(
    #     auth={
    #         "clientId": st.secrets.SSO_CLIENT_ID,
    #         "authority": st.secrets.SSO_AUTHORITY,
    #         "redirectUri": "/",
    #         "postLogoutRedirectUri": "/"
    #     },
    #     cache={
    #         "cacheLocation": "sessionStorage",
    #         "storeAuthStateInCookie": False
    #     },
    #     login_request={
    #         "scopes": [st.secrets.SSO_SCOPES]
    #     },
    #     class_name="stButton",
    #     key=1
    # )



logging.info(" =====  START OF MSG SESSION STATE  ====  ")

logging.info(st.session_state.messages)

logging.info(" =====  END OF MSG SESSION STATE  ====  ")

logging.info(" =====  START OF MSG SESSION STATE  ====  ")

logging.info(st.session_state.messages)

logging.info(" =====  END OF MSG SESSION STATE  ====  ")
