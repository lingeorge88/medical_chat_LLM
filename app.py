from flask import Flask, send_from_directory, request, jsonify
from flask_cors import CORS
from src.helper import download_embeddings
from langchain_pinecone import PineconeVectorStore
from langchain_openai import ChatOpenAI
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from src.prompt import *
import os

app = Flask(__name__, static_folder="frontend/build", static_url_path="")

# Configure CORS with specific origins
CORS(
    app,
    origins=[
        "http://localhost:3000",  # Local development
        "https://rag-medlab-frontend.onrender.com",  # frontend url
        "https://rag-medlab-frontend.onrender.com/",
    ],
    methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
    supports_credentials=True,
)

load_dotenv()

PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

embeddings = download_embeddings()

index_name = "medical-lab-chatbot"
# Embed each chunk and upsert the embeddings into your Pinecone index.
docsearch = PineconeVectorStore.from_existing_index(
    index_name=index_name, embedding=embeddings
)

retriever = docsearch.as_retriever(search_type="similarity", search_kwargs={"k": 3})

chatModel = ChatOpenAI(model="gpt-5-mini")
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        ("human", "{input}"),
    ]
)

question_answer_chain = create_stuff_documents_chain(chatModel, prompt)
rag_chain = create_retrieval_chain(retriever, question_answer_chain)


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/get", methods=["GET", "POST", "OPTIONS"])
def chat():
    # Handle preflight OPTIONS request
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    try:
        # Handle both form data and JSON
        if request.content_type == "application/json":
            msg = request.json.get("msg", "")
        else:
            msg = request.form.get("msg", "")

        if not msg:
            return jsonify({"error": "No message provided"}), 400

        print(f"Input: {msg}")
        response = rag_chain.invoke({"input": msg})
        print(f"Response: {response['answer']}")

        # Return JSON response for better compatibility
        return jsonify({"answer": response["answer"]}), 200

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


# Add a health check endpoint
@app.route("/health")
def health():
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    # Use PORT from environment variable
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
