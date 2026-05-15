import json
import os
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# -------------------------------------------------
# LOAD ENVIRONMENT VARIABLES
# -------------------------------------------------
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("Missing OPENROUTER_API_KEY in environment variables")

# -------------------------------------------------
# FASTAPI APP
# -------------------------------------------------
app = FastAPI()

# -------------------------------------------------
# CORS
# -------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------
# LLM
# -------------------------------------------------
llm = ChatOpenAI(
    model="deepseek/deepseek-chat",
    openai_api_key=OPENROUTER_API_KEY,
    openai_api_base="https://openrouter.ai/api/v1"
)

# -------------------------------------------------
# EMBEDDINGS
# -------------------------------------------------
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# -------------------------------------------------
# LAZY LOAD FAISS DATABASE (function)
# -------------------------------------------------
FAISS_INDEX_PATH = "faiss_index"

def get_faiss_db():
    """Load FAISS index if it exists, otherwise return None."""
    if not os.path.exists(FAISS_INDEX_PATH):
        return None
    return FAISS.load_local(
        FAISS_INDEX_PATH,
        embeddings,
        allow_dangerous_deserialization=True
    )

# -------------------------------------------------
# QUESTION REQUEST
# -------------------------------------------------
class QuestionRequest(BaseModel):
    domain: str

# -------------------------------------------------
# GENERATE QUESTIONS
# -------------------------------------------------
@app.post("/generate-question")
def generate_question(req: QuestionRequest):
    prompt = f"""
    Generate 5 professional interview questions
    for {req.domain} jobs.

    Return only the questions.
    """

    try:
        response = llm.invoke(prompt)
        questions = response.content.split("\n")
        clean_questions = [q.strip() for q in questions if q.strip()]
        return {"questions": clean_questions}
    except Exception as e:
        return {"error": str(e)}

# -------------------------------------------------
# SINGLE EVALUATION REQUEST
# -------------------------------------------------
class EvaluationRequest(BaseModel):
    question: str
    answer: str

# -------------------------------------------------
# EVALUATE SINGLE ANSWER
# -------------------------------------------------
@app.post("/evaluate-answer")
def evaluate_answer(req: EvaluationRequest):
    prompt = f"""
    Interview Question:
    {req.question}

    Candidate Answer:
    {req.answer}

    Evaluate professionally.

    Give:
    1. Score out of 10
    2. Strengths
    3. Improvement Suggestions

    Keep it concise.
    """

    try:
        response = llm.invoke(prompt)
        feedback = response.content if hasattr(response, "content") else str(response)

        history_data = {
            "question": req.question,
            "answer": req.answer,
            "feedback": feedback,
            "timestamp": str(datetime.now())
        }

        history_file = Path("history.json")
        if history_file.exists():
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        else:
            history = []

        history.append(history_data)
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4)

        return {"feedback": feedback}
    except Exception as e:
        return {"error": str(e)}

# -------------------------------------------------
# MULTIPLE ANSWERS REQUEST
# -------------------------------------------------
class MultiEvaluationRequest(BaseModel):
    qa_list: list

# -------------------------------------------------
# EVALUATE MULTIPLE ANSWERS
# -------------------------------------------------
@app.post("/evaluate-answers")
def evaluate_answers(req: MultiEvaluationRequest):
    feedbacks = []
    try:
        for item in req.qa_list:
            prompt = f"""
            Interview Question:
            {item['question']}

            Candidate Answer:
            {item['answer']}

            Evaluate professionally.

            Give:
            1. Score out of 10
            2. Strengths
            3. Improvements

            Keep concise.
            """
            response = llm.invoke(prompt)
            feedback = response.content if hasattr(response, "content") else str(response)
            feedbacks.append(feedback)

        return {"feedbacks": feedbacks}
    except Exception as e:
        return {"error": str(e)}

# -------------------------------------------------
# CHAT REQUEST
# -------------------------------------------------
class ChatRequest(BaseModel):
    question: str

# -------------------------------------------------
# ASK PDF (using FAISS)
# -------------------------------------------------
@app.post("/ask-pdf")
def ask_pdf(req: ChatRequest):
    db = get_faiss_db()
    if db is None:
        return {"answer": "FAISS database not found. Please refresh the database first.", "sources": []}

    try:
        docs = db.similarity_search(req.question, k=3)
        if not docs:
            return {"answer": "No relevant information found.", "sources": []}

        context = "\n".join(doc.page_content for doc in docs)
        sources = list({f"Page {doc.metadata.get('page', 'Unknown')}" for doc in docs})

        prompt = f"""
        You are a professional healthcare assistant.

        Answer ONLY from the provided context.

        Context:
        {context}

        Question:
        {req.question}
        """
        response = llm.invoke(prompt)
        answer = response.content if hasattr(response, "content") else str(response)
        return {"answer": answer, "sources": sources}
    except Exception as e:
        return {"error": str(e)}

# -------------------------------------------------
# ASK DOUBT REQUEST
# -------------------------------------------------
class DoubtRequest(BaseModel):
    question: str

# -------------------------------------------------
# ASK DOUBT
# -------------------------------------------------
@app.post("/ask-doubt")
def ask_doubt(req: DoubtRequest):
    db = get_faiss_db()
    if db is None:
        return {"answer": "FAISS database not found. Please refresh the database first."}

    try:
        docs = db.similarity_search(req.question, k=3)
        context = "\n".join(doc.page_content for doc in docs)

        prompt = f"""
        Answer professionally using the context.

        Context:
        {context}

        Question:
        {req.question}
        """
        response = llm.invoke(prompt)
        answer = response.content if hasattr(response, "content") else str(response)
        return {"answer": answer}
    except Exception as e:
        return {"answer": "Sorry, I couldn't find an answer.", "error": str(e)}

# -------------------------------------------------
# REFRESH DATABASE
# -------------------------------------------------
@app.post("/refresh-db")
def refresh_db():
    pdf_path = Path("data/healthcare_manual.pdf")
    if not pdf_path.exists():
        return {"error": "PDF file not found at data/healthcare_manual.pdf"}

    try:
        loader = PyPDFLoader(str(pdf_path))
        documents = loader.load()

        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        docs = splitter.split_documents(documents)

        new_db = FAISS.from_documents(docs, embeddings)
        new_db.save_local(FAISS_INDEX_PATH)
        return {"message": "FAISS database refreshed successfully"}
    except Exception as e:
        return {"error": str(e)}