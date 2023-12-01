import logging

import streamlit as st
import openai
import os

import importlib
import src.chat_bot
importlib.reload(src.chat_bot)
from src.chat_bot import ExconManual

import yaml
from yaml.loader import SafeLoader

logger = logging.getLogger(__name__)

# App title - Must be first Streamlit command
st.set_page_config(page_title="💬 Excon Manual Question Answering")


if "logger" not in st.session_state:
    st.session_state["logger"] = logging.getLogger(__name__)
    log_level = logging.WARNING
    st.session_state["logger"].setLevel(log_level)
    logging.basicConfig(level=log_level)
    st.session_state["logger"].info("-----------------------------------")
    st.session_state["logger"].info("Logger started")

st.title('Dealer Manual: Question Answering')
buttons = ['Authorised Dealer (AD)', 'AD with Limited Authority (ADLA)']

@st.cache_resource(show_spinner=False)
def load_data(ad = True):
    st.session_state["logger"].info(f'--> cache_resource called again to reload data')
    with st.spinner(text="Loading the excon documents and index – hang tight! This should take 5 seconds."):
        if ad:
            path_to_manual_as_csv_file = "./inputs/ad_manual.csv"
            path_to_definitions_as_parquet_file = "./inputs/ad_definitions.parquet"
            path_to_index_as_parquet_file = "./inputs/ad_index.parquet"
            chat_for_ad = True
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
    st.session_state["logger"].info("Adding \'manual_to_use\' to keys")
    st.session_state['manual_to_use'] = buttons[0]

if 'excon' not in st.session_state:
    st.session_state["logger"].info('Adding \'Excon\' to keys')
    st.session_state['excon'] = load_data(ad = True)

if 'openai_api' not in st.session_state:
    st.session_state['openai_api'] = None


def load_manual():
    st.session_state['manual_to_use'] = st.session_state.manual_type
    st.session_state["logger"].info(f'Loading new manual: {st.session_state.manual_type}')
    if st.session_state['manual_to_use'] == buttons[0]:
        st.session_state['excon'] = load_data(ad = True)
    else:
        st.session_state['excon'] = load_data(ad = False)

    st.session_state['excon'].reset_conversation_history()
    st.session_state['messages'] = [] 



st.write(f"I am a bot designed to answer questions based on the {st.session_state['excon'].manual_name}. How can I assist today?")
# Credentials
with st.sidebar:
    if not st.session_state['openai_api']:
        st.session_state["logger"].info(f'No token saved in session_state')
        st.session_state['openai_api'] = st.text_input('Enter API token:', type='password')
    else:
        st.session_state["logger"].info(f'Existing token in session_state. Using it to repopulate the field')
        st.session_state['openai_api'] = st.text_input('Enter API token:', value = st.session_state['openai_api'],type='password')

    if not (st.session_state['openai_api'].startswith('sk-') and len(st.session_state['openai_api'])==51):
        st.session_state["logger"].info(f'Token NOT valid')
        st.session_state["logger"].info(f"Startswith sk-: {st.session_state['openai_api'].startswith('sk-')}")
        st.session_state["logger"].info(f"Token Length: {len(st.session_state['openai_api'])}")
        st.warning('Please enter your credentials!', icon='⚠️')
        st.session_state['openai_api'] = None
    else:
        st.session_state["logger"].info(f'Token is valid')
        st.success('Proceed to entering your prompt message!', icon='👉')
        openai.api_key = st.session_state['openai_api']

    st.divider()

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
    selected_model = st.sidebar.selectbox('Choose a model', ['gpt-3.5-turbo', 'gpt-4'], key='selected_model')
    temperature = 0.0
    max_length = 800
    # temperature = st.sidebar.slider('temperature', min_value=0.00, max_value=2.0, value=0.0, step=0.01)
    # max_length = st.sidebar.slider('max_length', min_value=32, max_value=2048, value=512, step=8)
    st.divider()
        
# Store LLM generated responses
if "messages" not in st.session_state.keys():
    st.session_state["logger"].info("Adding \'messages\' to keys")
    st.session_state['excon'].reset_conversation_history()
    st.session_state['messages'] = [] 

# Display or clear chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

def clear_chat_history():
    st.session_state["logger"].info("Clearing \'messages\'")
    st.session_state['excon'].reset_conversation_history()
    st.session_state['messages'] = [] 
st.sidebar.button('Clear Chat History', on_click=clear_chat_history)


# User-provided prompt
if prompt := st.chat_input(disabled=not st.session_state['openai_api']):
    st.session_state["logger"].info(f"st.chat_input() called. Value returned is: {prompt}")        
    if prompt is not None and prompt != "":
        st.session_state['messages'].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            placeholder = st.empty()

            with st.spinner("Thinking..."):
                st.session_state["logger"].info(f"Making call to excon manual with prompt: {prompt}")
                response = st.session_state['excon'].chat_completion(user_context = prompt, 
                                threshold = 0.15, 
                                model_to_use = selected_model, 
                                temperature = temperature, 
                                max_tokens = max_length)
                st.session_state["logger"].info(f"Response received")
                st.session_state["logger"].info(f"Text Returned from excon manual chat: {response}")
                placeholder.markdown(response)
            st.session_state['messages'].append({"role": "assistant", "content": response})
            st.session_state["logger"].info("Response added the the queue")
    
