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
    # print(f"load data called for {ad}")
    with st.spinner(text="Loading the BOP codes – hang tight! This should take a few seconds."):
        path_to_bop_codes_as_parquet_file = "./inputs/bopcodes.parquet"
        df = pd.read_parquet(path_to_bop_codes_as_parquet_file, engine="pyarrow")
        return df

if 'bop_codes' not in st.session_state:
    st.session_state['bop_codes'] = load_bop_codes_data()



# Store LLM generated responses
if "messages_lookup" not in st.session_state.keys():
    #excon.reset_conversation_history()
    st.session_state.messages_lookup = [{"role": "assistant", "content": "Which code are you looking for?"}]

for message in st.session_state.messages_lookup:
    with st.chat_message(message["role"]):
        st.write(message["content"])

def clear_chat_history():
    #excon.reset_conversation_history()
    st.session_state.messages_lookup = [{"role": "assistant", "content": "Which code are you looking for?"}]
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
            #print("Embedding ... ")
            question_embedding = get_ada_embedding(prompt)
            #print("searching ....")
            closest_nodes = get_closest_nodes(st.session_state['bop_codes'], "Embedding", question_embedding, threshold = 0.25)
            #print("found ...")
            #print(closest_nodes)
            # st.dataframe(df[["Category", "Sub-category", "Category Description"]])
            # placeholder = st.empty()

            # if not prompt:
            #     formatted_response = "I was not able to extract a valid index from the value you input. Please try using the format A.1(A)(i)(a)(aa)."
            # else:
            #     response = st.session_state['excon'].get_regulation_detail(prompt)
            #     formatted_response = response
            #     formatted_response = ''
            #     lines = response.split('\n')
            #     for line in lines:
            #         spaces = len(line) - len(line.lstrip())
            #         formatted_response += '- ' + '&nbsp;' * spaces + line.lstrip() + "  \n"
            # placeholder.markdown(formatted_response)
    st_df = st.dataframe(closest_nodes[["Category", "Sub-category", "Category Description", "Inward or Outward"]], hide_index = True)
    st.session_state.messages_lookup.append({"role": "assistant", "content": st_df})



