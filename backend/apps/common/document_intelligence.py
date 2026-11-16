"""
Thin wrapper around azure-ai-documentintelligence.

Real Azure Document Intelligence is used when both
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and AZURE_DOCUMENT_INTELLIGENCE_KEY are
set (production would call the "prebuilt-document" model, or ideally a
custom-trained transcript/credential model, against the uploaded file).

Otherwise this falls back to a deterministic stub: it reads the raw text of
the uploaded document (uploads in tests/dev are plain text, one line per
course/credit entry) and parses it into structured course/subject rows.
Lines that don't parse cleanly still produce a reproducible fake record via
a SHA256-seeded derivation, so results are stable across runs.
"""
import hashlib
import re

from decouple import config

AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT = config("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT", default="")
AZURE_DOCUMENT_INTELLIGENCE_KEY = config("AZURE_DOCUMENT_INTELLIGENCE_KEY", default="")

_GRADES = ["A", "A-", "B+", "B", "B-", "C+", "C", "Pass"]
_TERMS = ["Fall 2019", "Spring 2020", "Fall 2020", "Spring 2021", "Fall 2021", "Spring 2022"]


def _is_configured() -> bool:
    return bool(AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and AZURE_DOCUMENT_INTELLIGENCE_KEY)


def extract_records(raw_bytes: bytes, filename: str = "") -> list[dict]:
    """Returns a list of {course_or_subject, grade_or_score, term} dicts."""
    if _is_configured():
        return _extract_real(raw_bytes)
    return _extract_stub(raw_bytes, filename)


def _extract_real(raw_bytes: bytes) -> list[dict]:
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.core.credentials import AzureKeyCredential

    client = DocumentIntelligenceClient(
        endpoint=AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT,
        credential=AzureKeyCredential(AZURE_DOCUMENT_INTELLIGENCE_KEY),
    )
    # NOTE: production usage should train and call a custom "transcript"
    # model; "prebuilt-document" is used here as a reasonable generic
    # fallback that still returns key/value fields and tables.
    poller = client.begin_analyze_document("prebuilt-document", body=raw_bytes)
    result = poller.result()

    records = []
    for table in getattr(result, "tables", []) or []:
        rows: dict[int, dict[int, str]] = {}
        for cell in table.cells:
            rows.setdefault(cell.row_index, {})[cell.column_index] = cell.content
        for row in rows.values():
            values = [row.get(i, "") for i in sorted(row.keys())]
            if len(values) >= 3 and values[0]:
                records.append({
                    "course_or_subject": values[0],
                    "grade_or_score": values[1],
                    "term": values[2],
                })
    if not records:
        records.append({"course_or_subject": "General Studies", "grade_or_score": "N/A", "term": "N/A"})
    return records


def _extract_stub(raw_bytes: bytes, filename: str = "") -> list[dict]:
    try:
        text = raw_bytes.decode("utf-8", errors="ignore")
    except Exception:
        text = ""

    records = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        parts = [p.strip() for p in re.split(r"[|,\t]", line) if p.strip()]
        if not parts:
            continue
        if len(parts) >= 3:
            records.append({
                "course_or_subject": parts[0],
                "grade_or_score": parts[1],
                "term": parts[2],
            })
        else:
            seed = hashlib.sha256((parts[0] + filename).encode("utf-8")).hexdigest()
            records.append({
                "course_or_subject": parts[0],
                "grade_or_score": _seeded_choice(seed, 0, _GRADES),
                "term": _seeded_choice(seed, 8, _TERMS),
            })

    if not records:
        seed = hashlib.sha256((text or filename or "empty-document").encode("utf-8")).hexdigest()
        records.append({
            "course_or_subject": "General Studies",
            "grade_or_score": _seeded_choice(seed, 0, _GRADES),
            "term": _seeded_choice(seed, 8, _TERMS),
        })
    return records


def _seeded_choice(hex_seed: str, offset: int, options: list[str]) -> str:
    chunk = hex_seed[offset:offset + 8] or hex_seed[:8]
    return options[int(chunk, 16) % len(options)]
