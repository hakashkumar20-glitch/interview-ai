from langchain_community.document_loaders import PyPDFLoader

from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain_community.vectorstores import FAISS

from langchain_huggingface import HuggingFaceEmbeddings

# Load PDF
loader = PyPDFLoader("data/healthcare_manual.pdf")

documents = loader.load()

# Split text into chunks
splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50
)

docs = splitter.split_documents(documents)

# Embedding model
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# Create FAISS vector database
db = FAISS.from_documents(docs, embeddings)

# Save database locally
db.save_local("faiss_index")

print("FAISS database created successfully")