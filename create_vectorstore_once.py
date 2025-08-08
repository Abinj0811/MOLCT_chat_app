import os
import warnings
import json
import re
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from langchain_core.documents import Document as LCDocument

# Setup
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
warnings.filterwarnings("ignore")
load_dotenv()

# === Load PDFs ===
pdfs = []
for root, dirs, files in os.walk('pdf'):
    for file in files:
        if file.endswith('.pdf'):
            pdfs.append(os.path.join(root, file))

# === Clean Function ===
def clean_text(text):
    if pd.isna(text):
        return ""
    text = str(text).strip()
    text = re.sub(r'\s+', ' ', text)
    return text

# === Convert Table JSON ===
def convert_table_to_text(table_name, table_data):
    text_chunks = []
    for entry in table_data:
        classification = entry.get("Classification", "").strip()
        sn = entry.get("S/N", "").strip()
        sub_items = entry.get("Sub_Items", [])

        if not classification or not sub_items:
            continue

        sub_items = [item for item in sub_items if item.get("MOL") != "MOL"]

        intro = f"Under the classification \"{classification}\""
        if sn:
            intro = f"For item {sn}, " + intro
        intro += ", the following apply:"

        grouped_output = []
        for item in sub_items:
            sub_class = item.get("Sub_Classification", "").strip()
            approvals, reviews, emails = [], [], []
            co_mgmt = item.get("Co-Mgmt. Dept.", "").strip()

            clause = f"For {sub_class}, " if sub_class else ""
            parts = []
            if approvals := [k for k, v in item.items() if v == "●" and k not in {"Deliberation MM", "Review GPM", "Report MM", "Report A3"}]:
                parts.append(f"approval is required from {', '.join(approvals)}")
            if reviews := [k for k, v in item.items() if v == "●" and k in {"Deliberation MM", "Review GPM", "Report MM", "Report A3"}]:
                parts.append(f"review or deliberation is done by {', '.join(reviews)}")
            if emails := [k for k, v in item.items() if str(v).strip().lower() == "email"]:
                parts.append(f"notification via email to {', '.join(emails)}")
            if co_mgmt:
                parts.append(f"co-management is handled by {co_mgmt}")

            if parts:
                clause += ", and ".join(parts)
                grouped_output.append(clause + ".")


        final_text = intro + " " + " ".join(grouped_output)
        text_chunks.append(final_text)

    return text_chunks

# === Convert Committee JSON ===
LEGEND_LABELS = {
    "◎": "Chairperson",
    "●": "Secretariat",
    "○": "Member",
    "△": "Sub-member"
}

def convert_committee_structure_to_text(page_name, page_data):
    text_docs = []

    if page_name == "Page4_Committee":
        for committee_name, sections in page_data.items():
            for section_title, members in sections.items():
                if not members:
                    continue
                role_sentences = []
                for person_title, mark in members.items():
                    # Detect and extract role symbol from value (not key)
                    mark_symbol = ""
                    if isinstance(mark, str):
                        for symbol in LEGEND_LABELS:
                            if symbol in mark:
                                mark_symbol = symbol
                                break
                    role = LEGEND_LABELS.get(mark_symbol, "Unknown Role")
                    role_sentences.append(f"{person_title} is the {role} in {section_title}")
                if role_sentences:
                    full_text = f"In the {committee_name} under {section_title}, " + "; ".join(role_sentences) + "."
                    text_docs.append(LCDocument(
                        page_content=full_text,
                        metadata={"source": "committee", "page": page_name, "committee": committee_name}
                    ))


    # elif page_name == "Page5_Table1":
    #     for committee_name, roles in page_data.items():
    #         role_sentences = []
    #         for person_title, mark in roles.items():
    #             marks = mark if isinstance(mark, list) else [mark]
    #             for m in marks:
    #                 mark_symbol = m.strip()
    #                 # Try to extract just the symbol (◎, ●, etc.)
    #                 for symbol in LEGEND_LABELS:
    #                     if symbol in mark_symbol:
    #                         mark_symbol = symbol
    #                         break
    #                 role = LEGEND_LABELS.get(mark_symbol, "Unknown Role")
    #                 role_sentences.append(f"{person_title} is the {role}")
    #         if role_sentences:
    #             full_text = f"In the {committee_name}, " + "; ".join(role_sentences) + "."
    #             text_docs.append(LCDocument(
    #                 page_content=full_text,
    #                 metadata={"source": "committee", "page": page_name, "committee": committee_name}
    #             ))

                
    elif page_name == "Page5_Table1":
        for committee_name, departments in page_data.items():
            role_sentences = []
            for department_name, mark in departments.items():
                marks = mark if isinstance(mark, list) else [mark]
                for m in marks:
                    mark_symbol = m.strip()
                    for symbol in LEGEND_LABELS:
                        if symbol in mark_symbol:
                            mark_symbol = symbol
                            break
                    role = LEGEND_LABELS.get(mark_symbol, "Unknown Role")
                    if mark_symbol in LEGEND_LABELS:
                        role_sentences.append(
                            f"The {committee_name} is the Head of Department (HOD) for {department_name}, and holds the role of {role}"
                        )
            if role_sentences:
                full_text = "; ".join(role_sentences) + "."
                text_docs.append(LCDocument(
                    page_content=full_text,
                    metadata={"source": "committee", "page": page_name, "committee": committee_name}
                ))

    return text_docs

# === Load JSONs and Convert ===
table_text_docs = []
try:
    with open("authority_json.json", "r", encoding="utf-8") as f:
        tables_json = json.load(f)
    for table_name, table_data in tables_json.items():
        sentences = convert_table_to_text(table_name, table_data)
        for sentence in sentences:
            table_text_docs.append(LCDocument(
                page_content=sentence,
                metadata={"source": "table", "table_name": table_name}
            ))
    print(f"✅ Converted {len(table_text_docs)} table entries to text documents")
except Exception as e:
    print(f"⚠️ Error loading table data: {e}")

try:
    with open("combined_output.json", "r", encoding="utf-8") as f:
        committee_json = json.load(f)

    for page_key, page_data in committee_json.items():
        if isinstance(page_data, dict):
            docs = convert_committee_structure_to_text(page_key, page_data)
            table_text_docs.extend(docs)
        else:
            print(f"⚠️ Skipped {page_key} - invalid format.")
    print(f"✅ Total documents from tables and committees: {len(table_text_docs)}")
    # === SAVE GENERATED SENTENCES FOR REFERENCE ===
    os.makedirs("debug_outputs", exist_ok=True)

    # Save table-converted text
    with open("debug_outputs/table_sentences.txt", "w", encoding="utf-8") as f_table:
        for doc in table_text_docs:
            if doc.metadata.get("source") == "table":
                f_table.write(doc.page_content + "\n\n")

    # Save committee-converted text
    with open("debug_outputs/committee_sentences.txt", "w", encoding="utf-8") as f_comm:
        for doc in table_text_docs:
            if doc.metadata.get("source") == "committee":
                f_comm.write(doc.page_content + "\n\n")

    print("✅ Saved table and committee sentences to 'debug_outputs/'")

except Exception as e:
    print(f"⚠️ Error loading committee structure: {e}")

# === Extract PDF Page Text ===
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, PdfFormatOption, WordFormatOption
from docling.pipeline.simple_pipeline import SimplePipeline
from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline

text_docs = []
input_paths = [Path(doc) for doc in pdfs]
doc_converter = DocumentConverter(
    allowed_formats=[InputFormat.PDF, InputFormat.IMAGE, InputFormat.DOCX],
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_cls=StandardPdfPipeline, backend=PyPdfiumDocumentBackend),
        InputFormat.DOCX: WordFormatOption(pipeline_cls=SimplePipeline)
    },
)

conv_results = doc_converter.convert_all(input_paths)
for result in conv_results:
    text_docs.append(LCDocument(
        page_content=result.document.export_to_markdown(),
        metadata={"source": "pdf"}
    ))

# === Add Footer Notes if any ===
if os.path.exists("footer_notes.json"):
    with open("footer_notes.json", "r", encoding="utf-8") as f:
        footer_data = json.load(f)
    for para in footer_data:
        if para.strip():
            text_docs.append(LCDocument(
                page_content=para.strip(),
                metadata={"source": "footer"}
            ))
    print(f"✅ Loaded {len(footer_data)} footer notes into text_docs")

# === Chunking ===
from langchain_text_splitters import RecursiveCharacterTextSplitter
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)
table_chunks = text_splitter.split_documents(table_text_docs)
text_chunks = text_splitter.split_documents(text_docs)
all_chunks = table_chunks + text_chunks

print(f"✅ Created {len(table_chunks)} chunks from table text")
print(f"✅ Created {len(text_chunks)} chunks from PDF/footers")

# === Embedding + FAISS Vector Store ===
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.docstore.in_memory import InMemoryDocstore
import faiss
from langchain_openai import OpenAIEmbeddings

# embeddings = OllamaEmbeddings(model='nomic-embed-text', base_url="http://localhost:11434")
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-large",  # or "text-embedding-ada-002"
    openai_api_key=os.getenv("OPENAI_API_KEY")
)

dim = len(embeddings.embed_query("sample query"))
index = faiss.IndexFlatL2(dim)

vector_store = FAISS(
    embedding_function=embeddings,
    index=index,
    docstore=InMemoryDocstore(),
    index_to_docstore_id={}
)
vector_store.add_documents(all_chunks)

# === Save Vector Store ===
db_path = "./app/vectorstores/faiss_index/MOLCT_openai_large"
vector_store.save_local(db_path)

print(f"✅ Vector store saved at {db_path}")
print(f"Total chunks stored: {len(all_chunks)}")

# === Test Queries ===
print("\n--- Testing Sample Queries ---")
queries = [
    "payment on behalf of others US$1million",
    "leasing IT asset US$200,000",
    "BDM approval required",
    "Who is the Chairperson of DX Committee?",
    "Who is the Head of Department?"
]
for q in queries:
    results = vector_store.similarity_search(q, k=2)
    print(f"\nQuery: {q}")
    for i, res in enumerate(results):
        print(f"  {i+1}: {res.page_content[:150]}...")
