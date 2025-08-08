import streamlit as st
import os
# import json
# ------------------- FAQ Logging Utilities using SQLite ------------------- #
from faq_manager import init_db, log_faq, get_top_faqs
from dotenv import load_dotenv
from typing import List
import time
from langchain_openai import OpenAIEmbeddings

from langchain_community.vectorstores import FAISS
from langchain_ollama.embeddings import OllamaEmbeddings
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_ollama import ChatOllama
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain_openai import ChatOpenAI
import re

# ------------------- Load environment ------------------- #
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ------------------- Prompt and Chain ------------------- #
# (Inside your Streamlit app file, e.g., app.py)
prompt_template = """
You are a Compliance Assistant for MOL Chemical Tankers Pvt Ltd. Your task is to answer questions strictly based on the provided internal regulatory context, which includes approval matrices, authority roles, and procedural guidelines.

Instructions:
1. Do **not** mention page numbers, table names, or metadata.
2. Do **not** speculate or provide information outside the context.
3. Your answer must be a direct, concise sentence using the roles, conditions, or procedures exactly as stated in the context.
4. If the answer cannot be derived from the context, respond with:
   "**Not found in available regulations.**"
5. If the question refers to MOL Chemical Tankers Pvt Ltd generally, start with:
   "MOL Chemical Tankers Pvt Ltd is a global leader in chemical tanker shipping, committed to operational excellence, regulatory compliance, and effective corporate governance."

Question: {question}
Context: {context}
Answer:
"""



prompt = ChatPromptTemplate.from_template(prompt_template)

def format_docs(docs):
    return "\n\n".join([doc.page_content for doc in docs])

# ------------------- Load Vector Store ------------------- #
embeddings = OllamaEmbeddings(model='nomic-embed-text', base_url="http://localhost:11434")

# embeddings = OpenAIEmbeddings(
#     model="text-embedding-3-small",  # or "text-embedding-ada-002"
#     openai_api_key=os.getenv("OPENAI_API_KEY")
# )

def normalize_query(text: str) -> str:
    replacements = {
        r"\b(global and regional directors|global or regional directors|regional and global directors)\b": "Global/Regional Directors",
        r"\bglobal directors\b": "Global/Regional Directors",
        r"\bregional directors\b": "Global/Regional Directors",
    }

    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


db_path = "./app/vectorstores/faiss_index/MOLCT_excel_full_footers"
vector_store = FAISS.load_local(db_path, embeddings=embeddings, allow_dangerous_deserialization=True)
retriever = vector_store.as_retriever(search_type="mmr", search_kwargs={"k": 3, "fetch_k": 100, "lambda_mult": 1})

model = ChatGroq(
    groq_api_key=os.getenv("GROQ_API_KEY"), 
    model="moonshotai/kimi-k2-instruct")

# model = ChatOpenAI(
#     model="gpt-3.5-turbo",
#     openai_api_key=os.getenv("OPENAI_API_KEY"),
#     temperature=0.2,
#     max_tokens=1000
# )


# model = ChatOllama(
#             model="phi4:latest",
#             base_url="http://192.168.0.49:2255",
#             streaming=True,
#             # callbacks=[StreamingStdOutCallbackHandler()],
#         )
rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | model
    | StrOutputParser()
)


# ------------------- Streamlit Setup ------------------- #
init_db()

predefined_faqs = [
    "What approval is required for investments over $1 million?",
    "What are the financial limits for lease contracts?",
    "Who has authority to approve vessel acquisitions?",
    "What are the responsibilities of the Group Accounting & Finance Department?",
    "What is the process for claim settlement under insurance coverage?",
]

if "messages" not in st.session_state:
    st.session_state.messages = []
if 'user_input' not in st.session_state:
    st.session_state['user_input'] = ""

# st.set_page_config(
#     page_title="MCTSPR Assistant",
#     page_icon="Logo/molct.png",
#     layout="wide",
#     initial_sidebar_state="expanded",
# )

# ------------------- UI Layout ------------------- #
st.title("🤖 MOLCT Management Approval Assistant")

with st.sidebar:
    st.image("Logo/molct.png", use_container_width=True)
    st.markdown("### 📋 MOLCT Management Approval")
    st.markdown("*Official Management Approval Assistant*")
    st.markdown("---")
    
    menu = ["🏠 Home", "🤖 Chatbot Assistant"]
    choice = st.selectbox("Navigate", menu)

# ------------------- Home ------------------- #
if choice == "🏠 Home":
    st.markdown("""
    ### Welcome to MOLCT Management Approval Assistant

    This assistant helps you navigate MOL Chemical Tankers' official authority regulations.
    
    #### ✅ Features:
    - Smart document search
    - Financial approval limits
    - Department authority lookup
    - FAQ and prompt memory
    """)

# ------------------- Assistant Chat ------------------- #
elif choice == "🤖 Chatbot Assistant":

    st.sidebar.subheader("Predefined Questions")
    for q in predefined_faqs:
        if st.sidebar.button(q, key=f"pre_{q}"):
            st.session_state['user_input'] = q

    st.sidebar.subheader("🔥 Popular Questions")
    for q in get_top_faqs():
        if st.sidebar.button(q, key=f"top_{q}"):
            st.session_state['user_input'] = q

    # Show chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_input = st.chat_input("Ask about MOLCT Management Approval...")
    if st.session_state['user_input']:
        user_input = st.session_state['user_input']
        st.session_state['user_input'] = ""

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            response_placeholder.markdown("⌛ Analyzing regulations...")
            try:
                normalized_input = normalize_query(user_input)
                response = rag_chain.invoke(normalized_input)

            except Exception as e:
                response = f"❌ Error: {e}"

            typed = ""
            for char in response:
                typed += char
                response_placeholder.markdown(typed)  # Use `write` instead of `markdown`
                time.sleep(0.01)



            response_placeholder.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
            log_faq(user_input)

# ------------------- Footer ------------------- #
footer = """
<style>
.footer {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background-color: #0066cc;
    color: white;
    text-align: center;
    padding: 10px;
    font-size: 12px;
    z-index: 1000;
}
</style>
<div class="footer">
    © 2025 MOLCT Management Approval Assistant | Powered by AIServices
</div>
"""
st.markdown(footer, unsafe_allow_html=True)
