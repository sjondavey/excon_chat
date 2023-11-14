import logging

import streamlit as st
import streamlit_authenticator as stauth # https://blog.streamlit.io/streamlit-authenticator-part-1-adding-an-authentication-component-to-your-app/
import openai
import os

import importlib
import src.chat_bot
importlib.reload(src.chat_bot)
from src.chat_bot import ExconManual

import yaml
from yaml.loader import SafeLoader


# App title - Must be first Streamlit command
st.set_page_config(page_title="💬 Excon Manual Question Answering")


authenticator = stauth.Authenticate(
    dict(st.secrets['credentials']),
    st.secrets['cookie']['name'],
    st.secrets['cookie']['key'],
    st.secrets['cookie']['expiry_days'],
    st.secrets['preauthorized']
)

if "logger" not in st.session_state:
    st.session_state["logger"] = logging.getLogger(__name__)
    st.session_state["logger"].setLevel(logging.INFO)
    logging.basicConfig(level=logging.INFO)
    st.session_state["logger"].info("-----------------------------------")
    st.session_state["logger"].info("Logger started")


st.title('Dealer Manual: Question Answering')
name, authentication_status, username = authenticator.login('Login', 'sidebar') # location is 'sidebar' or 'main'
buttons = ['Authorised Dealer (AD)', 'AD with Limited Authority (ADLA)']

if authentication_status:
    st.session_state["logger"].info("Starting at the top")

    st.write(f'Welcome *{name}*')
    st.write(f"I am a question answering bot. How can I assist today?")
    # Credentials
    with st.sidebar:
        st.session_state["logger"].info("Populating sidebar")
        openai.api_key = st.secrets['openai']['OPENAI_API_KEY'] #

        st.title('💬 Chat Parameters')        
        st.divider()

        selected_model = st.sidebar.selectbox('Choose a model', ['gpt-3.5-turbo', 'gpt-4'], key='selected_model')
        temperature = st.sidebar.slider('temperature', min_value=0.00, max_value=2.0, value=0.0, step=0.01)
        max_length = st.sidebar.slider('max_length', min_value=32, max_value=2048, value=512, step=8)
        st.divider()
            
    # Store LLM generated responses
    if "messages" not in st.session_state.keys():
        st.session_state["logger"].info("Creating messages key and setting it to the empty vector")
        st.session_state['messages'] = [] 

    # Display or clear chat messages
    for message in st.session_state.messages:
        st.session_state["logger"].info("Writing messages to chat_message")
        with st.chat_message(message["role"]):
            st.write(message["content"])

    def clear_chat_history():
        st.session_state["logger"].info("Clearing chat history")
        st.session_state['messages'] = [] 

    st.session_state["logger"].info("Adding Clear and Logout buttons")
    st.sidebar.button('Clear Chat History', on_click=clear_chat_history)
    authenticator.logout('Logout', 'sidebar')


    # User-provided prompt
    if prompt := st.chat_input():
        st.session_state["logger"].info(f"--> st.chat_input() called. prompt is: {prompt}")                   
        st.session_state['messages'].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state["logger"].info(f"--> st.chat_input() called. Adding message: {prompt}")                           
        with st.chat_message("assistant"):
            placeholder = st.empty()
            full_response = ""            

            st.session_state["logger"].info(f"Calling OpenAI with prompt: {st.session_state['messages'][-1]['content']}")                           
            response = openai.ChatCompletion.create(
                model=selected_model,
                temperature = temperature,
                max_tokens = max_length,
                messages = st.session_state['messages'])
            text_response = response['choices'][0]['message']['content']
            st.session_state["logger"].info(f"OpenAI responded with: {text_response}")                           
            placeholder.markdown(text_response)
            st.session_state['messages'].append({"role": "assistant", "content": text_response})
            st.session_state["logger"].info(f"Which has now been added to the messages array")                           
    
    st.session_state["logger"].info("^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")

elif authentication_status == False:
    st.error('Username/password is incorrect')
elif authentication_status == None:
    st.warning('Please enter your username and password')
