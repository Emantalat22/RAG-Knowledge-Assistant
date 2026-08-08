# RAG Knowledge Assistant

A Retrieval-Augmented Generation (RAG) based knowledge assistant that allows users to work with PDF documents and ask questions based on their content.

## Overview

This project combines document processing, text embeddings, vector search, and a language model to retrieve relevant information from uploaded documents and generate answers based on the retrieved content.

## Features

- PDF document processing
- Text extraction and chunking
- Semantic embeddings
- Similarity-based document retrieval
- ChromaDB vector database
- RAG-based question answering
- PDF/document ingestion
- FastAPI backend
- Frontend interface
- Ollama integration
- Document upload functionality

## Technologies Used

- Python
- FastAPI
- ChromaDB
- Ollama
- Sentence Transformers
- PyMuPDF
- HTML/CSS/JavaScript
- Git & GitHub

## Project Structure

```text
RAG-Knowledge-Assistant/
│
├── frontend/
├── documents/
│
├── chroma_test.py
├── embedding_test.py
├── fastapi_app.py
├── ingest_service.py
├── ingest.py
├── ollama_test.py
├── pdf_reader.py
├── rag_embeddings.py
├── rag.py
├── retrieval_test.py
├── similarity_test.py
├── upload_api.py
│
├── requirements.txt
└── README.md