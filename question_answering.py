import logging

import streamlit as st
import openai
import os
import bcrypt
from openai import OpenAI


import importlib
import src.chat_bot
importlib.reload(src.chat_bot)
from src.chat_bot import ExconManual


logger = logging.getLogger(__name__)
if "logger" not in st.session_state:
    st.session_state["logger"] = logging.getLogger(__name__)
    log_level = logging.INFO
    st.session_state["logger"].setLevel(log_level)
    logging.basicConfig(level=log_level)
    st.session_state["logger"].debug("-----------------------------------")
    st.session_state["logger"].debug("Logger started")

### Password
def check_password():
    """Returns `True` if the user had a correct password."""

    def login_form():
        """Form with widgets to collect user information"""
        with st.form("Credentials"):
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.form_submit_button("Log in", on_click=password_entered)

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        pwd_raw = st.session_state['password']
        if st.session_state["username"] in st.secrets[
            "passwords"
        ] and bcrypt.checkpw(
            pwd_raw.encode(),
            st.secrets.passwords[st.session_state["username"]].encode(),
        ):
            st.session_state["password_correct"] = True
            st.session_state["logger"].info(f"New questions From: {st.session_state['username']}")
            del st.session_state["password"]  # Don't store the username or password.
            del pwd_raw
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    # Return True if the username + password is validated.
    if st.session_state.get("password_correct", False):
        return True

    # Show inputs for username + password.
    login_form()
    if "password_correct" in st.session_state:
        st.error("😕 User not known or password incorrect")
    return False

if not check_password():
    st.stop()


# App title - Must be first Streamlit command
st.set_page_config(page_title="💬 Excon Manual Question Answering")

st.title('Dealer Manual: Question Answering')
buttons = ['Authorised Dealer (AD)', 'AD with Limited Authority (ADLA)']

@st.cache_resource(show_spinner=False)
def load_data(ad = True):
    st.session_state["logger"].debug(f'--> cache_resource called again to reload data')
    with st.spinner(text="Loading the excon documents and index – hang tight! This should take 5 seconds."):
        openai_client = OpenAI(api_key = st.secrets['openai']['OPENAI_API_KEY'])
        if ad:
            path_to_manual_as_csv_file = "./inputs/ad_manual.csv"
            path_to_definitions_as_parquet_file = "./inputs/ad_definitions.parquet"
            path_to_index_as_parquet_file = "./inputs/ad_index.parquet"
            chat_for_ad = True
            log_file = ''
            log_level = 20

            path_to_manual_plus = "./inputs/ad_manual_plus.csv"
            path_to_index_plus = "./inputs/ad_index_plus.parquet"

            excon = ExconManual(st.session_state['openai_client'],
                                path_to_manual_as_csv_file, 
                                path_to_definitions_as_parquet_file, 
                                path_to_index_as_parquet_file, 
                                chat_for_ad = chat_for_ad, 
                                log_file=log_file, 
                                logging_level=log_level, 
                                manual = path_to_manual_plus, # **kwargs
                                index = path_to_index_plus) 

        else:
            path_to_manual_as_csv_file = "./inputs/adla_manual.csv"
            path_to_definitions_as_parquet_file = "./inputs/adla_definitions.parquet"
            path_to_index_as_parquet_file = "./inputs/adla_index.parquet"
            chat_for_ad = False

            log_file = ''
            log_level = 20
            excon = ExconManual(path_to_manual_as_csv_file, path_to_definitions_as_parquet_file, path_to_index_as_parquet_file, chat_for_ad = chat_for_ad, log_file=log_file, logging_level=log_level)

        st.session_state["logger"].info(f"Load data called. Loading data for {excon.user_type}")
        return excon


if 'manual_to_use' not in st.session_state:
    st.session_state["logger"].debug("Adding \'manual_to_use\' to keys")
    st.session_state['manual_to_use'] = buttons[0]

if 'excon' not in st.session_state:
    st.session_state["logger"].debug('Adding \'Excon\' to keys')
    st.session_state['excon'] = load_data(ad = True)

if 'openai_api' not in st.session_state:
    st.session_state['openai_api'] = st.secrets['openai']['OPENAI_API_KEY'] #
    st.session_state['openai_client'] = OpenAI(api_key = st.secrets['openai']['OPENAI_API_KEY'])
    # openai.api_key = st.secrets['openai']['OPENAI_API_KEY'] #
    #openai_api = st.secrets['openai']['OPENAI_API_KEY']


def load_manual():
    st.session_state['manual_to_use'] = st.session_state.manual_type
    st.session_state["logger"].debug(f'Loading new manual: {st.session_state.manual_type}')
    if st.session_state['manual_to_use'] == buttons[0]:
        st.session_state['excon'] = load_data(ad = True)
    else:
        st.session_state['excon'] = load_data(ad = False)

    st.session_state['excon'].reset_conversation_history()
    st.session_state['messages'] = [] 

if 'selected_model' not in st.session_state.keys():
    st.session_state['model_options'] = ['gpt-3.5-turbo', 'gpt-4']
    st.session_state['selected_model'] = 'gpt-3.5-turbo'
    st.session_state['selected_model_index'] = st.session_state['model_options'].index(st.session_state['selected_model'])


st.write(f"I am a bot designed to answer questions based on the {st.session_state['excon'].manual_name}. How can I assist today?")
# Credentials
with st.sidebar:

    if st.session_state['manual_to_use'] == buttons[0]:
        index = 0
    else: 
        index = 1
    state = st.radio(label = 'Choose the manual:',
                        options = buttons,
                        index = index,
                        on_change = load_manual,
                        key = 'manual_type')
    
    st.divider()

    #st.subheader('Models and parameters')
        
    st.session_state['selected_model'] = st.sidebar.selectbox('Choose a model', st.session_state['model_options'], key='user_selected_model', index = st.session_state['selected_model_index'])
    st.session_state['selected_model_index'] = st.session_state['model_options'].index(st.session_state['selected_model'])
    temperature = 0.0
    max_length = 800
    # temperature = st.sidebar.slider('temperature', min_value=0.00, max_value=2.0, value=0.0, step=0.01)
    # max_length = st.sidebar.slider('max_length', min_value=32, max_value=2048, value=512, step=8)
    st.divider()
        
# Store LLM generated responses
if "messages" not in st.session_state.keys():
    st.session_state["logger"].debug("Adding \'messages\' to keys")
    st.session_state['excon'].reset_conversation_history()
    st.session_state['messages'] = [] 

# Display or clear chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

def clear_chat_history():
    st.session_state["logger"].debug("Clearing \'messages\'")
    st.session_state['excon'].reset_conversation_history()
    st.session_state['messages'] = [] 
st.sidebar.button('Clear Chat History', on_click=clear_chat_history)


# User-provided prompt
if prompt := st.chat_input(disabled=not st.session_state['openai_api']):
    st.session_state["logger"].debug(f"st.chat_input() called. Value returned is: {prompt}")        
    if prompt is not None and prompt != "":
        st.session_state['messages'].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            placeholder = st.empty()

            with st.spinner("Thinking..."):
                st.session_state["logger"].debug(f"Making call to excon manual with prompt: {prompt}")
                response = st.session_state['excon'].chat_completion(user_context = prompt, 
                                threshold = 0.15, 
                                model_to_use = st.session_state['selected_model'], 
                                temperature = temperature, 
                                max_tokens = max_length)
                st.session_state["logger"].debug(f"Response received")
                st.session_state["logger"].debug(f"Text Returned from excon manual chat: {response}")
                placeholder.markdown(response)
            st.session_state['messages'].append({"role": "assistant", "content": response})
            st.session_state["logger"].debug("Response added the the queue")
    
