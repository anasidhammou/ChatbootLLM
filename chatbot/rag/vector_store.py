import os
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

# Configure the OpenAI API with the API key from .env
api_key = "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"
if not api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

from chatbot.config import VECTOR_DB_DIR

def create_vector_store(documents, persist_directory=None):
    """
    Create a vector store from document chunks.
    If documents is empty, create a placeholder document to initialize the store.
    """
    if persist_directory is None:
        persist_directory = VECTOR_DB_DIR
    
    if not documents:
        print("No documents provided, adding a placeholder to initialize the vector store.")
        documents = ["Initial placeholder document"]
    
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",  # ou "text-embedding-3-large" pour de meilleures performances
        openai_api_key=api_key
    )
        
    vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=persist_directory
    )
    print(f"Vector store created with {len(documents)} document chunks")
    print(f"Vector store persisted to {persist_directory}")
    return vector_store

def load_vector_store(persist_directory=None):
    """
    Load an existing vector store.
    """
    if persist_directory is None:
        persist_directory = VECTOR_DB_DIR
    
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",  # ou "text-embedding-3-large" pour de meilleures performances
        openai_api_key=api_key
    )
        
    vector_store = Chroma(
        persist_directory=persist_directory,
        embedding_function=embeddings
    )
    return vector_store