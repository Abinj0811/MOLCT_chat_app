# import os
# import warnings
# from dotenv import load_dotenv
# from pathlib import Path
# import json
# import pdfplumber
# import pandas as pd
# import re

# # Suppress warnings and allow FAISS + Chroma together
# os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
# warnings.filterwarnings("ignore")
# load_dotenv()

# # Step 1: Collect PDF files
# pdfs = []
# for root, dirs, files in os.walk('pdf_folder'):
#     for file in files:
#         if file.endswith('.pdf'):
#             pdfs.append(os.path.join(root, file))

# # === TABLE EXTRACTION LOGIC (from test.py) ===
# def clean_text(text):
#     if pd.isna(text):
#         return ""
#     text = str(text).strip()
#     text = re.sub(r'\s+', ' ', text)
#     return text

# def is_currency(text):
#     if not isinstance(text, str):
#         return False
#     return any(symbol in text for symbol in ["¥", "$", "US$"])

# def extract_sn(text):
#     if not isinstance(text, str):
#         return None, text
#     match = re.match(r'^(\d+)(?:\s+|\.|\))?(.*)', text.strip())
#     if match:
#         return match.group(1), match.group(2).strip()
#     return None, text

# def validate_table(df):
#     if len(df.columns) < 2:
#         return None
#     df = df.applymap(clean_text)
#     df.replace("", pd.NA, inplace=True)
#     return df

# columns = [
#     "Extra","S/N", "Classification", "MOL", "BDM", "A1", "A2", "A3", "A4", "A5",
#     "Co-Mgmt. Dept.", "Deliberation MM", "Report MM", "Report A3", "Review GPM", "CC Dept."
# ]

# # Step 2: Extract tables and normal content
# from langchain_core.documents import Document as LCDocument

# table_docs = []   # Each table as a single document
# text_docs = []    # All non-table content

# # --- Use JSON as the source for table data ---
# json_path = "selected_pages_tables_structured.json"
# try:
#     with open(json_path, "r", encoding="utf-8") as f:
#         tables_json = json.load(f)

#     for table_name, rows in tables_json.items():
#         for row in rows:
#             sn = row.get("S/N", "")
#             classification = row.get("Classification", "")
#             sub_items = row.get("Sub_Items", [])

#             if not sub_items:
#                 continue

#             # Convert sub-items into DataFrame
#             df = pd.DataFrame(sub_items)

#             # Build markdown with table + header context
#             header = f"Table: {table_name}\nS/N: {sn}\nClassification: {classification}\n"
#             table_md = df.to_markdown(index=False)

#             table_docs.append(LCDocument(
#                 page_content=header + table_md
#             ))
#         print(f"✅ Loaded {len(table_docs)} table documents from JSON")
# except Exception as e:
#     print(f"⚠️ Error loading tables from JSON: {str(e)}")   

# # --- Extract the rest of the content as before, but for text_docs ---
# from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
# from docling.datamodel.base_models import InputFormat
# from docling.document_converter import DocumentConverter, PdfFormatOption, WordFormatOption
# from docling.pipeline.simple_pipeline import SimplePipeline
# from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline

# input_paths = [Path(doc) for doc in pdfs]
# doc_converter = DocumentConverter(
#     allowed_formats=[
#         InputFormat.PDF,
#         InputFormat.IMAGE,
#         InputFormat.DOCX,
#         InputFormat.HTML,
#         InputFormat.PPTX,
#         InputFormat.ASCIIDOC,
#         InputFormat.MD,
#     ],
#     format_options={
#         InputFormat.PDF: PdfFormatOption(
#             pipeline_cls=StandardPdfPipeline, backend=PyPdfiumDocumentBackend
#         ),
#         InputFormat.DOCX: WordFormatOption(
#             pipeline_cls=SimplePipeline
#         ),
#     },
# )

# conv_results = doc_converter.convert_all(input_paths)
# for result in conv_results:
#     text_docs.append(LCDocument(
#         page_content=result.document.export_to_markdown()
#     ))

# # Step 4: Chunking (only for non-table content)
# from langchain_text_splitters import RecursiveCharacterTextSplitter
# text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)
# text_chunks = text_splitter.split_documents(text_docs)

# # Combine table docs (un-chunked) and text chunks
# all_chunks = table_docs + text_chunks

# # Step 5: Embedding and Vector Store
# from langchain_ollama import OllamaEmbeddings
# from langchain_community.vectorstores import FAISS
# from langchain_community.docstore.in_memory import InMemoryDocstore
# import faiss
# from langchain_openai import OpenAIEmbeddings
# import os

# embeddings = OllamaEmbeddings(model='nomic-embed-text', base_url="http://localhost:11434")

# # embeddings = OpenAIEmbeddings(
# #     model="text-embedding-3-small",  # or "text-embedding-ada-002"
# #     openai_api_key=os.getenv("OPENAI_API_KEY")
# # )

# single_vector = embeddings.embed_query("sample query")

# index = faiss.IndexFlatL2(len(single_vector))
# vector_store = FAISS(
#     embedding_function=embeddings,
#     index=index,
#     docstore=InMemoryDocstore(),
#     index_to_docstore_id={}
# )

# vector_store.add_documents(all_chunks)

# # Step 6: Save Vector Store
# db_path = "./app/vectorstores/faiss_index/MOLCT_excel_full"
# vector_store.save_local(db_path)

# print(f"✅ Vector store created and saved at {db_path}")


import os
import warnings
from dotenv import load_dotenv
from pathlib import Path
import json
import pdfplumber
import pandas as pd
import re

# Suppress warnings and allow FAISS + Chroma together
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
warnings.filterwarnings("ignore")
load_dotenv()

# Step 1: Collect PDF files
pdfs = []
for root, dirs, files in os.walk('pdf_folder'):
    for file in files:
        if file.endswith('.pdf'):
            pdfs.append(os.path.join(root, file))

# === TABLE EXTRACTION LOGIC (from test.py) ===
def clean_text(text):
    if pd.isna(text):
        return ""
    text = str(text).strip()
    text = re.sub(r'\s+', ' ', text)
    return text

def is_currency(text):
    if not isinstance(text, str):
        return False
    return any(symbol in text for symbol in ["¥", "$", "US$"])

def extract_sn(text):
    if not isinstance(text, str):
        return None, text
    match = re.match(r'^(\d+)(?:\s+|\.|\))?(.*)', text.strip())
    if match:
        return match.group(1), match.group(2).strip()
    return None, text

def validate_table(df):
    if len(df.columns) < 2:
        return None
    df = df.applymap(clean_text)
    df.replace("", pd.NA, inplace=True)
    return df

def convert_table_to_text(table_name, table_data):
    """
    Convert JSON table data into natural language sentences
    """
    text_chunks = []
    
    for entry in table_data:
        sn = entry.get("S/N", "")
        classification = entry.get("Classification", "")
        sub_items = entry.get("Sub_Items", [])
        
        if not sub_items:
            continue
            
        # Create base context for this classification
        base_context = f"Table: {table_name}"
        if sn:
            base_context += f", Serial Number: {sn}"
        if classification:
            base_context += f", Classification: {classification}"
        
        # Process each sub-item
        for item in sub_items:
            # Skip header rows (usually the first item with column names)
            if item.get("MOL") == "MOL" and item.get("BDM") == "BDM":
                continue
                
            sub_classification = item.get("Sub_Classification", "")
            
            # Create a sentence for this specific item
            sentence = base_context
            if sub_classification:
                sentence += f", Sub-classification: {sub_classification}"
            
            # Add approval authorities and requirements
            authorities = []
            requirements = []
            
            for key, value in item.items():
                if key in ["Sub_Classification"]:
                    continue
                    
                if "●" in value:
                    if "MM" in key or "GPM" in key:
                        requirements.append(f"{key} required")
                    else:
                        authorities.append(f"{key} approval required")
                elif value and value != "●" and value.strip():
                    if "Email" in value:
                        requirements.append(f"{key}: {value}")
                    else:
                        requirements.append(f"{key}: {value}")
            
            # Combine authorities and requirements into natural language
            if authorities:
                sentence += f". Approval required from: {', '.join(authorities)}"
            if requirements:
                sentence += f". Requirements: {', '.join(requirements)}"
            
            # Add period if not present
            if not sentence.endswith('.'):
                sentence += "."
                
            text_chunks.append(sentence)
    
    return text_chunks

columns = [
    "Extra","S/N", "Classification", "MOL", "BDM", "A1", "A2", "A3", "A4", "A5",
    "Co-Mgmt. Dept.", "Deliberation MM", "Report MM", "Report A3", "Review GPM", "CC Dept."
]

# Step 2: Extract tables and normal content
from langchain_core.documents import Document as LCDocument

table_text_docs = []   # Converted table text as documents
text_docs = []    # All non-table content

# --- Convert JSON table data to text sentences ---
json_path = "selected_pages_tables_structured.json"
try:
    with open(json_path, "r", encoding="utf-8") as f:
        tables_json = json.load(f)

    for table_name, table_data in tables_json.items():
        # Convert table to text sentences
        text_sentences = convert_table_to_text(table_name, table_data)
        
        # Create documents from text sentences
        for sentence in text_sentences:
            table_text_docs.append(LCDocument(
                page_content=sentence,
                metadata={"source": "table", "table_name": table_name}
            ))
    
    print(f"✅ Converted {len(table_text_docs)} table entries to text documents")
    
    # Print a few examples to see the conversion
    print("\n--- Sample converted table entries ---")
    for i, doc in enumerate(table_text_docs[:3]):
        print(f"{i+1}. {doc.page_content}")
        
except Exception as e:
    print(f"⚠️ Error loading tables from JSON: {str(e)}")   

# --- Extract the rest of the content as before, but for text_docs ---
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, PdfFormatOption, WordFormatOption
from docling.pipeline.simple_pipeline import SimplePipeline
from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline

input_paths = [Path(doc) for doc in pdfs]
doc_converter = DocumentConverter(
    allowed_formats=[
        InputFormat.PDF,
        InputFormat.IMAGE,
        InputFormat.DOCX,
        InputFormat.HTML,
        InputFormat.PPTX,
        InputFormat.ASCIIDOC,
        InputFormat.MD,
    ],
    format_options={
        InputFormat.PDF: PdfFormatOption(
            pipeline_cls=StandardPdfPipeline, backend=PyPdfiumDocumentBackend
        ),
        InputFormat.DOCX: WordFormatOption(
            pipeline_cls=SimplePipeline
        ),
    },
)

conv_results = doc_converter.convert_all(input_paths)
for result in conv_results:
    text_docs.append(LCDocument(
        page_content=result.document.export_to_markdown(),
        metadata={"source": "pdf"}
    ))
# Load footer notes (explanatory paragraphs) as separate documents
footer_path = "footer_notes.json"
if os.path.exists(footer_path):
    with open(footer_path, "r", encoding="utf-8") as f:
        footer_data = json.load(f)
    
    for para in footer_data:
        if para.strip():
            text_docs.append(LCDocument(
                page_content=para.strip(),
                metadata={"source": "footer"}
            ))
    print(f"✅ Loaded {len(footer_data)} footer notes into text_docs")


# Step 4: Chunking (for both table text and regular content)
from langchain_text_splitters import RecursiveCharacterTextSplitter
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)

# Chunk table text documents
table_chunks = text_splitter.split_documents(table_text_docs)
print(f"✅ Created {len(table_chunks)} chunks from table text")

# Chunk regular text documents
text_chunks = text_splitter.split_documents(text_docs)
print(f"✅ Created {len(text_chunks)} chunks from PDF text")

# Combine all chunks
all_chunks = table_chunks + text_chunks

# Step 5: Embedding and Vector Store
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.docstore.in_memory import InMemoryDocstore
import faiss
from langchain_openai import OpenAIEmbeddings
import os

embeddings = OllamaEmbeddings(model='nomic-embed-text', base_url="http://localhost:11434")

# embeddings = OpenAIEmbeddings(
#     model="text-embedding-3-small",  # or "text-embedding-ada-002"
#     openai_api_key=os.getenv("OPENAI_API_KEY")
# )

single_vector = embeddings.embed_query("sample query")

index = faiss.IndexFlatL2(len(single_vector))
vector_store = FAISS(
    embedding_function=embeddings,
    index=index,
    docstore=InMemoryDocstore(),
    index_to_docstore_id={}
)

vector_store.add_documents(all_chunks)

# Step 6: Save Vector Store
db_path = "./app/vectorstores/faiss_index/MOLCT_excel_full_footers"
vector_store.save_local(db_path)

print(f"✅ Vector store created and saved at {db_path}")
print(f"Total chunks in vector store: {len(all_chunks)}")
print(f"- Table text chunks: {len(table_chunks)}")
print(f"- PDF text chunks: {len(text_chunks)}")

# Optional: Test a sample query to see if it works
print("\n--- Testing sample queries ---")
test_queries = [
    "payment on behalf of others US$1million",
    "leasing IT asset US$200,000",
    "BDM approval required"
]

for query in test_queries:
    results = vector_store.similarity_search(query, k=2)
    print(f"\nQuery: '{query}'")
    for i, result in enumerate(results):
        print(f"  Result {i+1}: {result.page_content[:150]}...")
