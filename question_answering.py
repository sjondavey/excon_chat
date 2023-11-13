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

# App title - Must be furst Streamlit command
st.set_page_config(page_title="💬 Excon Manual Question Answering")

#user_input_api = False

authenticator = stauth.Authenticate(
    dict(st.secrets['credentials']),
    st.secrets['cookie']['name'],
    st.secrets['cookie']['key'],
    st.secrets['cookie']['expiry_days'],
    st.secrets['preauthorized']
)

st.title('Dealer Manual: Question Answering')
name, authentication_status, username = authenticator.login('Login', 'sidebar') # location is 'sidebar' or 'main'
buttons = ['Authorised Dealer (AD)', 'AD with Limited Authority (ADLA)']

@st.cache_resource(show_spinner=False)
def load_data(ad = True):
    # print(f"load data called for {ad}")
    with st.spinner(text="Loading the excon documents and index – hang tight! This should take 30 seconds."):
        if ad:
            path_to_manual_as_csv_file = "./inputs/ad_manual.csv"
            path_to_definitions_as_parquet_file = "./inputs/ad_definitions.parquet"
            path_to_index_as_parquet_file = "./inputs/ad_index.parquet"
            chat_for_ad = True
            log_file = ''
            log_level = 20
        else:
            path_to_manual_as_csv_file = "./inputs/adla_manual.csv"
            path_to_definitions_as_parquet_file = "./inputs/adla_definitions.parquet"
            path_to_index_as_parquet_file = "./inputs/adla_index.parquet"
            chat_for_ad = False
            log_file = ''
            log_level = 20
        return ExconManual(path_to_manual_as_csv_file, path_to_definitions_as_parquet_file, path_to_index_as_parquet_file, chat_for_ad = chat_for_ad, log_file=log_file, logging_level=log_level)


if 'manual_to_use' not in st.session_state:
    st.session_state['manual_to_use'] = buttons[0]

if 'excon' not in st.session_state:
    st.session_state['excon'] = load_data(ad = True)

def load_manual():
    st.session_state['manual_to_use'] = st.session_state.manual_type
    if st.session_state['manual_to_use'] == buttons[0]:
        st.session_state['excon'] = load_data(ad = True)
    else:
        st.session_state['excon'] = load_data(ad = False)

    st.session_state['excon'].reset_conversation_history()
    st.session_state.messages = [] #st.session_state['excon'].messages 

if authentication_status:
    st.write(f'Welcome *{name}*')
    st.write(f"I am a bot designed to answer questions based on the {st.session_state['excon'].manual_name}. How can I assist today?")
    # Credentials
    with st.sidebar:
        st.title('💬 Chat Parameters')

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

        # if user_input_api:
        #     openai_api = st.text_input('Enter OpenAI API token:', type='password')
        #     if not (openai_api.startswith('sk-') and len(openai_api)==51):
        #         st.warning('Please enter your credentials!', icon='⚠️')
        #     else:
        #         st.success('Proceed to entering your prompt message!', icon='👉')
        #     st.divider()
        # else: 
        openai.api_key = st.secrets['openai']['OPENAI_API_KEY'] #
        openai_api = st.secrets['openai']['OPENAI_API_KEY']

        #st.subheader('Models and parameters')
        selected_model = st.sidebar.selectbox('Choose a model', ['gpt-3.5-turbo', 'gpt-4'], key='selected_model')
        temperature = st.sidebar.slider('temperature', min_value=0.00, max_value=2.0, value=0.0, step=0.01)
        max_length = st.sidebar.slider('max_length', min_value=32, max_value=2048, value=512, step=8)
        st.divider()
            

    # Store LLM generated responses
    if "messages" not in st.session_state.keys():
        st.session_state['excon'].reset_conversation_history()
        st.session_state.messages = [] # st.session_state['excon'].messages 

    # Display or clear chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    def clear_chat_history():
        st.session_state['excon'].reset_conversation_history()
        st.session_state.messages = [] # st.session_state['excon'].messages 
    st.sidebar.button('Clear Chat History', on_click=clear_chat_history)
    authenticator.logout('Logout', 'sidebar')


    # User-provided prompt
    prompt = st.chat_input()
    if prompt is not None and prompt != "":
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        # Generate a new response if last message is not from assistant
        if len(st.session_state.messages) > 0 and st.session_state.messages[-1]["role"] != "assistant":
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    #print(f'##### {prompt}')
                    st.session_state['excon'].user_provides_input(user_context = prompt, 
                                    threshold = 0.15, 
                                    model_to_use = selected_model, 
                                    temperature = temperature, 
                                    max_tokens = max_length)
                    #print(f'#### Done with API Call')
                    response = st.session_state['excon'].messages[-1]['content']
                    #print(f'##Response: {response}')
                    placeholder = st.empty()
                    full_response = ''
                    for item in response:
                        full_response += item
                        placeholder.markdown(full_response)
                    placeholder.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
            #st.session_state['excon'].messages

elif authentication_status == False:
    st.error('Username/password is incorrect')
elif authentication_status == None:
    st.warning('Please enter your username and password')
