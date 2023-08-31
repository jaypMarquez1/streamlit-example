import openai
import streamlit as st

openai.api_type = "azure"
openai.api_key = st.secrets["OPENAI_API_KEY"]
openai.api_base = st.secrets["OPENAPI_API_BASE"]
openai.api_version = "2023-05-15" 

st.title("☃️ Frosty")

 # Initialize the chat messages history
if "messages" not in st.session_state.keys():
    st.session_state.messages = [{"role": "assistant", "content": "How can I help?"}]

# Prompt for user input and save
if prompt := st.chat_input():
    st.session_state.messages.append({"role": "user", "content": prompt})

# display the existing chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# If last message is not from assistant, we need to generate a new response
if st.session_state.messages[-1]["role"] != "assistant":
    # Call LLM
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            r = openai.ChatCompletion.create(
                deployment_id = "gpt-35-turbo-16k_icicle2",
                model="gpt-3.5-turbo",
                messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
            )
            response = r.choices[0].message.content
            st.write(response)

    message = {"role": "assistant", "content": response}
    st.session_state.messages.append(message)
    

