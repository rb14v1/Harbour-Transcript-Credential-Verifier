"""
Thin wrapper around Azure OpenAI chat completions and embeddings, via the
`openai` package's AzureOpenAI client.

Real calls are made when both AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY
are set. Otherwise this produces deterministic stub output: stub chat text
built from the inputs, and stub embedding vectors that are SHA256-seeded so
they are reproducible across runs (same text -> same vector -> same search
results), exactly EMBEDDING_DIMENSIONS floats long.
"""
import hashlib
import struct

from decouple import config

AZURE_OPENAI_ENDPOINT = config("AZURE_OPENAI_ENDPOINT", default="")
AZURE_OPENAI_API_KEY = config("AZURE_OPENAI_API_KEY", default="")
AZURE_OPENAI_API_VERSION = config("AZURE_OPENAI_API_VERSION", default="2024-10-21")

OPENAI_CHAT_MODEL = config("OPENAI_CHAT_MODEL", default="gpt-5.4-mini")
OPENAI_EMBEDDING_MODEL = config("OPENAI_EMBEDDING_MODEL", default="text-embedding-3-large")
EMBEDDING_DIMENSIONS = 1536


def _is_configured() -> bool:
    return bool(AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY)


def _client():
    from openai import AzureOpenAI

    return AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
    )


def pad_vector(seed_bytes: bytes, dimensions: int = EMBEDDING_DIMENSIONS) -> list[float]:
    """Deterministically expands a seed into a fixed-length unit-ish vector."""
    vector: list[float] = []
    counter = 0
    while len(vector) < dimensions:
        digest = hashlib.sha256(seed_bytes + counter.to_bytes(4, "big")).digest()
        for i in range(0, len(digest) - 3, 4):
            if len(vector) >= dimensions:
                break
            value = struct.unpack(">I", digest[i:i + 4])[0]
            vector.append((value / 0xFFFFFFFF) * 2 - 1)
        counter += 1
    return vector[:dimensions]


def generate_embedding(text: str) -> list[float]:
    if _is_configured():
        client = _client()
        response = client.embeddings.create(model=OPENAI_EMBEDDING_MODEL, input=text)
        return list(response.data[0].embedding)

    seed = hashlib.sha256(text.encode("utf-8")).digest()
    return pad_vector(seed)


def chat_completion(system_prompt: str, user_prompt: str) -> str:
    if _is_configured():
        client = _client()
        response = client.chat.completions.create(
            model=OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content

    seed = hashlib.sha256((system_prompt + "||" + user_prompt).encode("utf-8")).hexdigest()
    return (
        f"[stub-ai:{seed[:12]}] Deterministic stub response (no AZURE_OPENAI_* configured). "
        "Based on the retrieved coursework excerpts provided, the subject matter appears "
        "related to the question asked; a human reviewer should confirm final equivalency."
    )
