"""
Thin wrapper around azure-storage-blob.

Real Azure Blob Storage is used when AZURE_STORAGE_CONNECTION_STRING is set.
Otherwise this falls back to writing/reading files under
MEDIA_ROOT/blob_stub/<container>/ on local disk, with identical function
signatures either way, so callers never need to know which mode is active.
"""
import os
import uuid

from decouple import config
from django.conf import settings

AZURE_STORAGE_CONNECTION_STRING = config("AZURE_STORAGE_CONNECTION_STRING", default="")


def _is_configured() -> bool:
    return bool(AZURE_STORAGE_CONNECTION_STRING)


def _stub_dir(container: str) -> str:
    path = os.path.join(str(settings.MEDIA_ROOT), "blob_stub", container)
    os.makedirs(path, exist_ok=True)
    return path


def _read_bytes(file) -> bytes:
    if hasattr(file, "read"):
        data = file.read()
        if hasattr(file, "seek"):
            try:
                file.seek(0)
            except Exception:
                pass
    else:
        data = file
    if isinstance(data, str):
        data = data.encode("utf-8")
    return data


def upload_document(file, container: str, blob_name: str = None) -> str:
    """Uploads a file-like object or bytes, returns an opaque blob_path."""
    original_name = getattr(file, "name", "upload.bin")
    blob_name = blob_name or f"{uuid.uuid4().hex}_{os.path.basename(str(original_name))}"
    data = _read_bytes(file)

    if _is_configured():
        from azure.storage.blob import BlobServiceClient

        client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        try:
            client.create_container(container)
        except Exception:
            pass  # container already exists
        blob_client = client.get_blob_client(container=container, blob=blob_name)
        blob_client.upload_blob(data, overwrite=True)
        return f"azure://{container}/{blob_name}"

    directory = _stub_dir(container)
    full_path = os.path.join(directory, blob_name)
    with open(full_path, "wb") as f:
        f.write(data)
    return f"stub://{container}/{blob_name}"


def download_document(blob_path: str) -> bytes:
    """Reads back whatever was stored at blob_path, in either mode."""
    if blob_path.startswith("azure://"):
        rest = blob_path[len("azure://"):]
        container, blob_name = rest.split("/", 1)
        from azure.storage.blob import BlobServiceClient

        client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        blob_client = client.get_blob_client(container=container, blob=blob_name)
        return blob_client.download_blob().readall()

    if blob_path.startswith("stub://"):
        rest = blob_path[len("stub://"):]
        container, blob_name = rest.split("/", 1)
        full_path = os.path.join(_stub_dir(container), blob_name)
        with open(full_path, "rb") as f:
            return f.read()

    raise ValueError(f"Unrecognized blob_path format: {blob_path!r}")
