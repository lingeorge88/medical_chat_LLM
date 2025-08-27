# Medical Chatbot LLM
![screenshot](./resources/ragchat.png)
## Overview
A concept application designed specifically for medical laboratory environments, leveraging Large Language Models (LLMs) to provide intelligent, context-aware responses to complex procedural and technical queries.

## Problem Statement

Traditional keyword-based document searches are fundamentally limited in medical laboratory contexts, where:

- **Complex Procedures**: Laboratory protocols often involve multi-step processes that can't be adequately described with simple keywords
- **Technical Terminology**: Medical and laboratory jargon varies significantly across institutions and equipment manufacturers
- **Context Dependencies**: The relevance of information often depends on specific sample types, reagent combinations, or equipment states
- **Limited Search Results**: Keyword searches return exact matches only, missing related procedures, troubleshooting steps, or alternative methods
- **User Experience**: Laboratory technicians need quick, accurate answers without sifting through irrelevant search results

## Solution

This project implements a Retrieval-Augmented Generation (RAG) system that:

1. **Semantic Understanding**: Uses advanced embeddings to understand the meaning behind questions, not just keyword matches
2. **Context-Aware Retrieval**: Retrieves relevant documentation based on semantic similarity and context
3. **Intelligent Responses**: Generates human-like answers that synthesize information from multiple sources
4. **Continuous Learning**: Can be updated with new documentation without retraining the entire system

## Key Features

- **PDF Document Processing**: Automatically extracts and chunks technical documentation
- **Vector Database**: Stores document embeddings in Pinecone for fast similarity search
- **LLM Integration**: Uses OpenAI's GPT models for natural language understanding and response generation
- **Medical Domain Expertise**: Specialized prompts for medical laboratory equipment and procedures
- **Scalable Architecture**: Easy to add new documents and update existing knowledge base

## Use Cases

- **Equipment Troubleshooting**: Quick answers to analyzer errors and maintenance procedures
- **Protocol Guidance**: Step-by-step instructions for complex laboratory procedures
- **Quality Control**: Information about QC profiles, calibration procedures, and validation
- **Training Support**: On-demand reference for laboratory technicians and staff

## Technology Stack

- **LangChain**: Framework for building LLM applications
- **Pinecone**: Vector database for semantic search
- **OpenAI GPT**: Large language model for natural language processing
- **HuggingFace**: Sentence transformers for document embeddings
- **PyPDF**: PDF text extraction and processing

## Getting Started
Live Demo: https://rag-medlab-frontend.onrender.com/

To test locally and upload your own knowledge base: 

1. Install dependencies: `pip install -r requirements.txt`
2. Set up environment variables for API keys
3. Place PDF documentation in the `data/` directory
4. Run the notebook to process documents and build the knowledge base
5. Use the chatbot interface for queries

## Future Enhancements

- Faster response time
- Integration with laboratory information systems
- Real-time document updates
- User feedback and response quality tracking