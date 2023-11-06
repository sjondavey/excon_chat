import streamlit as st
import importlib
import src.chat_bot
importlib.reload(src.chat_bot)
from src.chat_bot import ExconManual

st.title('Dealer Manual: Section Lookup')

# @st.cache_resource(show_spinner=False)
# def load_data(ad = True):
#     with st.spinner(text="Loading the excon documents and index – hang tight! This should take 30 seconds."):
#         if ad:
#             path_to_manual_as_csv_file = "./inputs/ad_manual.csv"
#             path_to_definitions_as_parquet_file = "./inputs/ad_definitions.parquet"
#             path_to_index_as_parquet_file = "./inputs/ad_index.parquet"
#             chat_for_ad = True
#             log_file = ''
#             log_level = 20
#         else:
#             path_to_manual_as_csv_file = "./inputs/adla_manual.csv"
#             path_to_definitions_as_parquet_file = "./inputs/adla_definitions.parquet"
#             path_to_index_as_parquet_file = "./inputs/adla_index.parquet"
#             chat_for_ad = False
#             log_file = ''
#             log_level = 20

#         excon = ExconManual(path_to_manual_as_csv_file, path_to_definitions_as_parquet_file, path_to_index_as_parquet_file, chat_for_ad = chat_for_ad, log_file=log_file, logging_level=log_level)
#         return excon

# excon = load_data(ad = True)

with st.sidebar:
    st.title('💬 Dealer Manual section lookup')

# Store LLM generated responses
if "messages_lookup" not in st.session_state.keys():
    #excon.reset_conversation_history()
    st.session_state.messages_lookup = [{"role": "assistant", "content": "Which section are you after? Please use the format A.1(A)(i)(a)(aa)"}]

for message in st.session_state.messages_lookup:
    with st.chat_message(message["role"]):
        st.write(message["content"])

def clear_chat_history():
    #excon.reset_conversation_history()
    st.session_state.messages_lookup = [{"role": "assistant", "content": "Which section are you after? Please use the format A.1(A)(i)(a)(aa)"}]
st.sidebar.button('Clear Lookup History', on_click=clear_chat_history)


# User-provided prompt
if prompt := st.chat_input(): 
    st.session_state.messages_lookup.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

# Generate a new response if last message is not from assistant
if st.session_state.messages_lookup[-1]["role"] != "assistant":
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            placeholder = st.empty()
            prompt = st.session_state['excon'].index_checker.extract_valid_reference(prompt)
            if not prompt:
                formatted_response = "I was not able to extract a valid index from the value you input. Please try using the format A.1(A)(i)(a)(aa)."
            else:
                response = st.session_state['excon'].get_regulation_detail(prompt)
                formatted_response = response
                formatted_response = ''
                lines = response.split('\n')
                for line in lines:
                    spaces = len(line) - len(line.lstrip())
                    formatted_response += '- ' + '&nbsp;' * spaces + line.lstrip() + "  \n"
            placeholder.markdown(formatted_response)
    st.session_state.messages_lookup.append({"role": "assistant", "content": formatted_response})



