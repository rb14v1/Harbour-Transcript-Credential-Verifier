"""
Thin wrapper around azure-search-documents (vector + hybrid search).

Real Azure AI Search is used when both AZURE_SEARCH_ENDPOINT and
AZURE_SEARCH_KEY are set. Otherwise this falls back to an in-process,
in-memory store: a plain Python list of {id, vector, payload} dicts per
"index name", with cosine-similarity top-k search implemented with no
external dependencies. This fallback only needs to live for a single
process/test run - like Qdrant's ":memory:" mode in sibling apps - there is
no persistence requirement.
"""
import math

from decouple import config

AZURE_SEARCH_ENDPOINT = config("AZURE_SEARCH_ENDPOINT", default="")
AZURE_SEARCH_KEY = config("AZURE_SEARCH_KEY", default="")

# index_name -> {doc_id: {"id": ..., "vector": [...], "payload": {...}}}
_MEMORY_STORE: dict[str, dict[str, dict]] = {}


def _is_configured() -> bool:
    return bool(AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def upsert_chunks(index_name: str, items: list[dict]) -> int:
    """items: list of {id, vector, payload}. Returns count upserted."""
    if _is_configured():
        return _upsert_real(index_name, items)

    store = _MEMORY_STORE.setdefault(index_name, {})
    for item in items:
        store[str(item["id"])] = item
    return len(items)


def search(index_name: str, query_vector: list[float], top_k: int = 5) -> list[dict]:
    """Returns [{id, score, payload}, ...] sorted by descending score."""
    if _is_configured():
        return _search_real(index_name, query_vector, top_k)

    store = _MEMORY_STORE.get(index_name, {})
    scored = [
        {
            "id": item["id"],
            "score": _cosine_similarity(query_vector, item["vector"]),
            "payload": item["payload"],
        }
        for item in store.values()
    ]
    scored.sort(key=lambda entry: entry["score"], reverse=True)
    return scored[:top_k]


def clear_index(index_name: str) -> None:
    """Test/dev helper: wipes one in-memory index. No-op in real mode."""
    _MEMORY_STORE.pop(index_name, None)


def index_size(index_name: str):
    """Returns the in-memory doc count, or None when running against a real
    (not stubbed) Azure AI Search index, where a cheap local count isn't
    available/needed."""
    if _is_configured():
        return None
    return len(_MEMORY_STORE.get(index_name, {}))


def _get_search_client(index_name: str):
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents import SearchClient

    return SearchClient(
        endpoint=AZURE_SEARCH_ENDPOINT,
        index_name=index_name,
        credential=AzureKeyCredential(AZURE_SEARCH_KEY),
    )


def _upsert_real(index_name: str, items: list[dict]) -> int:
    client = _get_search_client(index_name)
    documents = [
        {"id": str(item["id"]), "vector": item["vector"], **item["payload"]}
        for item in items
    ]
    client.upload_documents(documents=documents)
    return len(documents)


def _search_real(index_name: str, query_vector: list[float], top_k: int) -> list[dict]:
    from azure.search.documents.models import VectorizedQuery

    client = _get_search_client(index_name)
    vector_query = VectorizedQuery(vector=query_vector, k_nearest_neighbors=top_k, fields="vector")
    results = client.search(search_text=None, vector_queries=[vector_query], top=top_k)

    output = []
    for result in results:
        payload = {k: v for k, v in result.items() if not k.startswith("@") and k not in ("id", "vector")}
        output.append({
            "id": result["id"],
            "score": result.get("@search.score", 0.0),
            "payload": payload,
        })
    return output
