"""
The core processing + equivalency pipeline:

  upload -> extract (document_intelligence) -> chunk -> embed (ai) ->
  index (search_store) -> [later] retrieve + summarize (ai)

All through the apps/common dual-path (real/stub) modules, so this module
behaves identically whether USE_SQLITE/Azure credentials are real or stubbed.
"""
from apps.common import ai, blob_store, document_intelligence, search_store

from .models import Credential, CredentialChunk, CredentialRecord

SEARCH_INDEX_NAME = "credential_chunks"


def process_credential(credential: Credential) -> Credential:
    """Runs the full extract -> chunk -> embed -> index pipeline for one credential."""
    raw_bytes = blob_store.download_document(credential.blob_path)
    extracted = document_intelligence.extract_records(raw_bytes, filename=credential.blob_path)

    # Idempotent re-processing: wipe any previous records/chunks for this credential.
    credential.records.all().delete()
    credential.chunks.all().delete()

    created_records = []
    for row in extracted:
        created_records.append(
            CredentialRecord.objects.create(
                credential=credential,
                course_or_subject=row.get("course_or_subject", ""),
                grade_or_score=row.get("grade_or_score", ""),
                term=row.get("term", ""),
            )
        )

    chunk_items = []
    for index, record in enumerate(created_records):
        chunk_text = (
            f"{credential.applicant.full_name} studied {record.course_or_subject} "
            f"at {credential.institution} during {record.term}, "
            f"achieving a grade/score of {record.grade_or_score or 'N/A'}."
        )
        search_doc_id = f"credential-{credential.id}-chunk-{index}"
        chunk = CredentialChunk.objects.create(
            credential=credential,
            chunk_text=chunk_text,
            chunk_index=index,
            search_doc_id=search_doc_id,
        )
        vector = ai.generate_embedding(chunk_text)
        chunk_items.append({
            "id": search_doc_id,
            "vector": vector,
            "payload": {
                "credential_id": credential.id,
                "chunk_id": chunk.id,
                "chunk_text": chunk_text,
                "course_or_subject": record.course_or_subject,
                "institution": credential.institution,
            },
        })

    if chunk_items:
        search_store.upsert_chunks(SEARCH_INDEX_NAME, chunk_items)

    credential.status = Credential.Status.PROCESSED
    credential.save(update_fields=["status"])
    return credential


def reindex_all_processed_credentials() -> int:
    """
    Rebuilds the in-memory search index from CredentialChunk rows already in
    the database. Used to self-heal the stub in-memory index (which only
    lives for a single process) after a fresh process start, e.g. right
    after `migrate` loads seed data in a brand new dev server process.
    No-op (returns 0) when running against a real Azure AI Search index.
    """
    chunks = CredentialChunk.objects.select_related("credential")
    items = []
    for chunk in chunks:
        vector = ai.generate_embedding(chunk.chunk_text)
        items.append({
            "id": chunk.search_doc_id,
            "vector": vector,
            "payload": {
                "credential_id": chunk.credential_id,
                "chunk_id": chunk.id,
                "chunk_text": chunk.chunk_text,
                "institution": chunk.credential.institution,
            },
        })
    if items:
        search_store.upsert_chunks(SEARCH_INDEX_NAME, items)
    return len(items)


def ensure_index_populated() -> None:
    size = search_store.index_size(SEARCH_INDEX_NAME)
    if size == 0:
        reindex_all_processed_credentials()


def answer_equivalency_question(question_text: str, credential: Credential | None = None, top_k: int = 5):
    """
    Embeds the question, retrieves the most relevant coursework chunks (all
    credentials, or scoped to one), and asks the chat model for a plain
    language equivalency recommendation citing the retrieved coursework.

    Returns (answer_text, retrieved_chunk_ids).
    """
    ensure_index_populated()
    query_vector = ai.generate_embedding(question_text)
    # Over-fetch then filter so a credential-scoped question still gets top_k
    # relevant results even when the in-memory/real index is shared across
    # all credentials.
    raw_results = search_store.search(SEARCH_INDEX_NAME, query_vector, top_k=max(top_k * 4, top_k))

    if credential is not None:
        scoped = [r for r in raw_results if r["payload"].get("credential_id") == credential.id]
        results = scoped[:top_k] if scoped else raw_results[:top_k]
    else:
        results = raw_results[:top_k]

    context_lines = "\n".join(f"- {r['payload'].get('chunk_text', '')}" for r in results) or "(no matching coursework found)"
    system_prompt = (
        "You are an admissions assistant helping a reviewer assess transfer-credit / "
        "credential equivalency. Use only the provided coursework excerpts, and cite "
        "the specific coursework you relied on."
    )
    user_prompt = (
        f"Question: {question_text}\n\n"
        f"Retrieved coursework excerpts:\n{context_lines}\n\n"
        "Provide a short, plain-language equivalency recommendation."
    )
    answer_text = ai.chat_completion(system_prompt, user_prompt)
    retrieved_chunk_ids = [r["payload"].get("chunk_id") for r in results if r["payload"].get("chunk_id") is not None]
    return answer_text, retrieved_chunk_ids
