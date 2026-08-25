"""
Vector service for FAQ embeddings using OpenAI and Pinecone.

Handles:
- Generating embeddings via OpenAI text-embedding-3-small (with dimension=1024)
- Upserting / deleting FAQ vectors in Pinecone
- Querying similar FAQs for a project
- Generating grounded LLM answers via OpenAI gpt-4o-mini
"""

import logging
import os
import uuid

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration (read once at module import)
# ---------------------------------------------------------------------------
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "bdo-faq-index")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

EMBEDDING_MODEL = "text-embedding-3-small"  # OpenAI embedding model
EMBEDDING_DIMENSION = 1024  # matches Pinecone index dimension (supported by text-embedding-3)
CHAT_MODEL = "gpt-4o-mini"  # OpenAI fast & affordable chat model

# ---------------------------------------------------------------------------
# Lazy singletons
# ---------------------------------------------------------------------------
_pc_client = None
_pc_index = None
_openai_client = None


def _get_pinecone_index():
    """Return Pinecone Index handle (lazily initialised)."""
    global _pc_client, _pc_index
    if _pc_index is None:
        from pinecone import Pinecone
        _pc_client = Pinecone(api_key=PINECONE_API_KEY)
        _pc_index = _pc_client.Index(PINECONE_INDEX_NAME)
    return _pc_index


def _get_openai_client():
    """Return OpenAI client (lazily initialised)."""
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI
        _openai_client = OpenAI(api_key=OPENAI_API_KEY)
    return _openai_client


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------

def get_embedding(text: str) -> list:
    """Generate an embedding vector for *text* using OpenAI."""
    client = _get_openai_client()
    response = client.embeddings.create(
        input=text,
        model=EMBEDDING_MODEL,
        dimensions=EMBEDDING_DIMENSION,
    )
    return response.data[0].embedding


# ---------------------------------------------------------------------------
# Pinecone CRUD
# ---------------------------------------------------------------------------

def upsert_faq_to_pinecone(faq) -> str:
    """
    Upsert a ProjectFAQ instance into Pinecone.

    If ``faq.pinecone_doc_id`` already exists it will be reused (update),
    otherwise a new document ID is generated.

    Returns the Pinecone document ID that was upserted.
    """
    index = _get_pinecone_index()

    # Build the text blob that will be embedded
    doc_text = (
        f"Project: {faq.project.name}\n"
        f"Question: {faq.question}\n"
        f"Answer: {faq.answer}"
    )

    vector = get_embedding(doc_text)

    # Reuse existing ID or create a new one
    doc_id = faq.pinecone_doc_id or f"faq_{faq.id}_{uuid.uuid4().hex[:8]}"

    metadata = {
        "faq_id": faq.id,
        "project_id": faq.project_id,
        "project_name": faq.project.name,
        "question": faq.question,
        "answer": faq.answer,
    }

    index.upsert(vectors=[(doc_id, vector, metadata)])
    logger.info("Upserted FAQ %s to Pinecone as %s", faq.id, doc_id)
    return doc_id


def delete_faq_from_pinecone(doc_id):
    """Delete a vector from Pinecone by its document ID (no-op if *doc_id* is falsy)."""
    if not doc_id:
        return
    try:
        index = _get_pinecone_index()
        index.delete(ids=[doc_id])
        logger.info("Deleted Pinecone vector %s", doc_id)
    except Exception:
        logger.exception("Failed to delete Pinecone vector %s", doc_id)


# ---------------------------------------------------------------------------
# Similarity search
# ---------------------------------------------------------------------------

def query_project_faqs(project_id: int, query_text: str, top_k: int = 5) -> list:
    """
    Embed *query_text* and search Pinecone for the most relevant FAQs
    belonging to *project_id*.

    Returns a list of dicts: ``[{"score": float, "question": str, "answer": str, "faq_id": int}, ...]``
    """
    index = _get_pinecone_index()
    query_vector = get_embedding(query_text)

    results = index.query(
        vector=query_vector,
        top_k=top_k,
        filter={"project_id": {"$eq": project_id}},
        include_metadata=True,
    )

    matches = []
    for match in results.get("matches", []):
        meta = match.get("metadata", {})
        matches.append({
            "score": round(match["score"], 4),
            "question": meta.get("question", ""),
            "answer": meta.get("answer", ""),
            "faq_id": meta.get("faq_id"),
            "doc_id": match["id"],
        })
    return matches


# ---------------------------------------------------------------------------
# LLM answer generation
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a helpful project assistant for the "{project_name}" project.
Your job is to answer user questions ONLY based on the FAQ knowledge base provided below.

Rules:
1. Answer using ONLY the provided FAQ context. Do NOT make up information.
2. If the answer is found in the FAQs, provide a clear, direct answer.
3. If no relevant FAQ matches the question, say: "I don't have information about that in the project FAQs. Please add a relevant FAQ or contact the team."
4. Be concise and helpful.
5. When referencing information, mention which FAQ question it came from.

FAQ Knowledge Base:
{faq_context}
"""


def generate_agent_answer(project_name: str, question: str, retrieved_faqs: list, chat_history=None) -> dict:
    """
    Generate an answer grounded in *retrieved_faqs* using OpenAI chat completion.

    Returns ``{"answer": str, "sources": list[dict]}``.
    """
    client = _get_openai_client()

    # Build FAQ context block
    if retrieved_faqs:
        faq_lines = []
        for i, faq in enumerate(retrieved_faqs, 1):
            faq_lines.append(
                f"FAQ #{i} (Relevance: {faq['score']:.0%}):\n"
                f"  Q: {faq['question']}\n"
                f"  A: {faq['answer']}"
            )
        faq_context = "\n\n".join(faq_lines)
    else:
        faq_context = "(No FAQs matched the user's question.)"

    system = SYSTEM_PROMPT.format(project_name=project_name, faq_context=faq_context)

    messages = [{"role": "system", "content": system}]

    if chat_history:
        for msg in chat_history:
            role = "assistant" if msg.get("role") == "model" else msg.get("role", "user")
            messages.append({"role": role, "content": msg.get("text", "")})

    messages.append({"role": "user", "content": question})

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=messages,
        temperature=0.3,
        max_tokens=1024,
    )

    answer_text = response.choices[0].message.content or "Sorry, I could not generate an answer."

    sources = [
        {
            "faq_id": faq["faq_id"],
            "question": faq["question"],
            "score": faq["score"],
        }
        for faq in retrieved_faqs
        if faq["score"] >= 0.50
    ]

    return {"answer": answer_text, "sources": sources}
