import streamlit as st
import importlib
import src.embeddings
importlib.reload(src.embeddings)
from src.embeddings import get_ada_embedding, get_closest_nodes
import pandas as pd

st.title('Dealer Manual: BOP Codes')


with st.sidebar:
    st.title('💬 BOP codes lookup')

@st.cache_resource(show_spinner=False)
def load_bop_codes_data():
    with st.spinner(text="Loading the BOP codes – hang tight! This should take a few seconds."):
        path_to_bop_codes_as_parquet_file = "./inputs/bopcodes.parquet"
        df = pd.read_parquet(path_to_bop_codes_as_parquet_file, engine="pyarrow")
        return df

if 'bop_codes' not in st.session_state:
    st.session_state['bop_codes'] = load_bop_codes_data()


# Store LLM generated responses
if "bop_lookup" not in st.session_state.keys():
    st.session_state['bop_lookup'] = [{"role": "assistant", "content": "Which code are you looking for?"}]

for message in st.session_state['bop_lookup']:
    with st.chat_message(message["role"]):
        st.write(message["content"])


def clear_chat_history():
    #excon.reset_conversation_history()
    st.session_state['bop_lookup'] = [{"role": "assistant", "content": "Which code are you looking for?"}]
st.sidebar.button('Clear Lookup History', on_click=clear_chat_history)


# User-provided prompt
if prompt := st.chat_input(disabled= ('password_correct' not in st.session_state or not st.session_state["password_correct"])): 
    st.session_state['bop_lookup'].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

# Generate a new response if last message is not from assistant
if st.session_state['bop_lookup'][-1]["role"] != "assistant":
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            question_embedding = get_ada_embedding(st.session_state['openai_client'], prompt)
            closest_nodes = get_closest_nodes(st.session_state['bop_codes'], "Embedding", question_embedding, threshold = 0.25)

    df = closest_nodes[["Category", "Sub-category", "Category Description", "Inward or Outward"]]
    st_df = st.dataframe(closest_nodes[["Category", "Sub-category", "Category Description", "Inward or Outward"]], hide_index = True)
    st.session_state['bop_lookup'].append({"role": "assistant", "content": df})



