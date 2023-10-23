import streamlit as st
import importlib
import src.chat_bot
importlib.reload(src.chat_bot)
from src.chat_bot import ExconManual

st.title('Dealer Manual: Section Lookup')

@st.cache_resource(show_spinner=False)
def load_data():
    with st.spinner(text="Loading the excon documents and index – hang tight! This should take 30 seconds."):
        excon = ExconManual("./logs/streamlit_lookup.log")
        return excon

excon = load_data()

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
            prompt = excon.index_checker.extract_valid_reference(prompt)
            if not prompt:
                formatted_response = "I was not able to extract a valid index from the value you input. Please try using the format A.1(A)(i)(a)(aa)."
            else:
                response = excon.get_regulation_detail(prompt)
                formatted_response = response
                formatted_response = ''
                lines = response.split('\n')
                for line in lines:
                    spaces = len(line) - len(line.lstrip())
                    formatted_response += '- ' + '&nbsp;' * spaces + line.lstrip() + "  \n"
            placeholder.markdown(formatted_response)
    st.session_state.messages_lookup.append({"role": "assistant", "content": formatted_response})



