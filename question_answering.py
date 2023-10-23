import streamlit as st
import openai
import os

import importlib
import src.chat_bot
importlib.reload(src.chat_bot)
from src.chat_bot import ExconManual

# App title
st.set_page_config(page_title="💬 Excon Manual Question Answering")

st.title('Dealer Manual: Question Answering')

@st.cache_resource(show_spinner=False)
def load_data():
    with st.spinner(text="Loading the excon documents and index – hang tight! This should take 30 seconds."):
        #excon = ExconManual("./logs/streamlit.log")
        excon = ExconManual("")
        return excon

excon = load_data()


# Credentials
with st.sidebar:
    st.title('💬 Chat Parameters')
    
    user_input_api = True
    print("waiting for API key")
    if user_input_api:
        openai_api = st.text_input('Enter OpenAI API token:', type='password')
        if not (openai_api.startswith('sk-') and len(openai_api)==51):
            st.warning('Please enter your credentials!', icon='⚠️')
        else:
            st.success('Proceed to entering your prompt message!', icon='👉')
    else: 
        openai_api = os.environ['OPENAI_API_KEY'] 

    st.subheader('Models and parameters')
    selected_model = st.sidebar.selectbox('Choose a model', ['gpt-3.5-turbo', 'gpt-4'], key='selected_model')
    temperature = st.sidebar.slider('temperature', min_value=0.00, max_value=2.0, value=0.0, step=0.01)
    max_length = st.sidebar.slider('max_length', min_value=32, max_value=2048, value=512, step=8)
        

# Store LLM generated responses
if "messages" not in st.session_state.keys():
    excon.reset_conversation_history()
    st.session_state.messages = excon.messages 

# Display or clear chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

def clear_chat_history():
    excon.reset_conversation_history()
    st.session_state.messages = excon.messages 
st.sidebar.button('Clear Chat History', on_click=clear_chat_history)


# User-provided prompt
if prompt := st.chat_input(disabled=not openai_api): 
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

# Generate a new response if last message is not from assistant
if st.session_state.messages[-1]["role"] != "assistant":
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            excon.user_provides_input(user_context = prompt, 
                              threshold = 0.15, 
                              model_to_use = selected_model, 
                              temperature = temperature, 
                              max_tokens = max_length)
            response = excon.messages[-1]['content']
            #print(f'##Response: {response}')
            placeholder = st.empty()
            full_response = ''
            for item in response:
                full_response += item
                placeholder.markdown(full_response)
            placeholder.markdown(full_response)
    st.session_state.messages = excon.messages