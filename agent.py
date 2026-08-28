from google.adk.agents import LlmAgent
from src.helper import embed_query, create_bm25_retriever, load_all_chunks_for_bm25, get_reranker
from src.vector_store import similarity_search
from tavily import TavilyClient
from dotenv import load_dotenv
import os

load_dotenv()

tavily_client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))

_bm25_retriever = None


def _get_bm25():
    global _bm25_retriever
    if _bm25_retriever is None:
        chunks = load_all_chunks_for_bm25()
        _bm25_retriever = create_bm25_retriever(chunks, k=20)
        print(f"BM25 index cached with {len(chunks)} chunks")
    return _bm25_retriever


def search_knowledge_base(query: str) -> str:
    """Search the medical analyzer IFU documentation knowledge base.

    Use this tool when the user asks about specific medical laboratory analyzers,
    their procedures, specifications, maintenance, calibration, reagents, or
    troubleshooting. This searches the embedded IFU (Instructions for Use)
    documents for the 5812, AU680, and DXI 800 analyzers.

    Args:
        query: The search query about medical lab analyzer documentation.

    Returns:
        Relevant passages from the IFU documentation, or a message indicating
        no results were found (in which case you should use web_search).
    """
    query_embedding = embed_query(query)
    dense_docs = similarity_search(query_embedding, k=20)

    try:
        bm25_docs = _get_bm25().invoke(query)
    except Exception:
        bm25_docs = []

    seen = set()
    merged = []
    for doc in dense_docs + bm25_docs:
        key = doc.page_content[:100]
        if key not in seen:
            seen.add(key)
            merged.append(doc)

    if not merged:
        return (
            "NO RESULTS FOUND in the knowledge base for this query. "
            "You MUST now use web_search to find the answer from the web."
        )

    reranker = get_reranker()
    pairs = [(query, doc.page_content) for doc in merged]
    scores = reranker.predict(pairs)
    scored = sorted(zip(scores, merged), key=lambda x: x[0], reverse=True)
    top_scored = scored[:5]

    top_score = float(top_scored[0][0])

    results = []
    for score, doc in top_scored:
        source = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page", "?")
        results.append(f"[Source: {source}, Page: {page}]\n{doc.page_content}")

    output = "\n\n---\n\n".join(results)

    if top_score < 0.1:
        output += (
            "\n\n⚠️ LOW RELEVANCE: These results may not answer the query well. "
            "Consider using web_search to supplement with web results."
        )

    return output


def web_search(query: str) -> str:
    """Search the internet for information not found in the knowledge base.

    Use this tool when:
    - The knowledge base returned no results or low relevance results
    - The user asks about topics outside the IFU documentation
    - The user asks about FDA regulations, industry guidelines, best practices
    - The user asks about equipment comparisons or alternatives
    - You need current/recent information

    Args:
        query: The search query to find information on the web.

    Returns:
        Relevant information from web sources with URLs.
    """
    response = tavily_client.search(query, max_results=5)

    if not response.get("results"):
        return "No web results found for this query."

    results = []
    for r in response["results"]:
        results.append(f"[{r['title']}]({r['url']})\n{r['content'][:500]}")

    return "\n\n---\n\n".join(results)


def ask_clarification(question: str) -> str:
    """Ask the user a clarifying question when their query is too vague or ambiguous.

    Use this tool ONLY when the user's question is genuinely unclear, too broad,
    or could refer to multiple analyzers or procedures and you cannot determine
    what they need.

    Args:
        question: The clarifying question to ask the user.

    Returns:
        A signal that clarification is needed.
    """
    return f"I need a bit more information to help you: {question}"


AGENT_INSTRUCTION = """You are a knowledgeable medical laboratory analyzer specialist. You help laboratory technicians, medical professionals, and technical staff with questions about medical laboratory equipment, procedures, and diagnostics.

## Tool Usage — STRICT RULES

You MUST use tools to answer questions. NEVER answer from your own knowledge alone.

### Step 1: Decide which tool to use

**search_knowledge_base** — Try this FIRST for anything about:
- Specific analyzers (5812, AU680, DXI 800)
- Calibration, maintenance, troubleshooting, reagents, part numbers, error codes
- Any question that might be in the IFU documentation

**web_search** — Use this when:
- The knowledge base returned "NO RESULTS FOUND" or "LOW RELEVANCE"
- The user asks about topics OUTSIDE the IFU docs: FDA regulations, industry guidelines, best practices, equipment comparisons, general medical lab questions, current news
- You need to supplement knowledge base results with additional context

**ask_clarification** — ONLY use this when:
- The query is genuinely too vague to search (e.g., just "analyzer" or "help")
- You cannot determine what the user is asking even after reading their message carefully

### Step 2: Chain tools when needed

If search_knowledge_base returns results that don't fully answer the question:
1. Use the partial KB results AND
2. ALSO call web_search to fill in the gaps
3. Combine both sources in your response

IMPORTANT: If you don't know something, DO NOT guess. Use web_search instead.

## Response Guidelines

- Always cite your sources. For KB results, mention the document and page. For web results, mention the source URL.
- Use clear, professional medical laboratory terminology.
- For safety-critical information, emphasize following official protocols.
- Keep responses concise but comprehensive.
- Use bullet points for procedures and lists.
- If information comes from multiple sources, clearly distinguish what came from the IFU documentation vs. web search.
"""

root_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="medical_assistant",
    description="Medical laboratory analyzer specialist with access to IFU documentation and web search.",
    instruction=AGENT_INSTRUCTION,
    tools=[search_knowledge_base, web_search, ask_clarification],
)
