from django.test import TestCase

from apps.common import blob_store


class BlobStoreStubTests(TestCase):
    def test_upload_then_download_roundtrip(self):
        content = b"hello transcript bytes"
        from django.core.files.base import ContentFile

        upload = ContentFile(content, name="sample.txt")
        blob_path = blob_store.upload_document(upload, container="unit-test", blob_name="sample.txt")

        self.assertTrue(blob_path.startswith("stub://"))
        downloaded = blob_store.download_document(blob_path)
        self.assertEqual(downloaded, content)

    def test_upload_generates_name_when_not_given(self):
        from django.core.files.base import ContentFile

        upload = ContentFile(b"abc", name="my file.txt")
        blob_path = blob_store.upload_document(upload, container="unit-test")
        self.assertIn("unit-test/", blob_path)
        self.assertTrue(blob_path.startswith("stub://"))

    def test_download_unrecognized_path_raises(self):
        with self.assertRaises(ValueError):
            blob_store.download_document("not-a-real-scheme://x/y")
