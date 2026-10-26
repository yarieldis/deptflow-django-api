import tempfile

from django.test import SimpleTestCase, override_settings

from core.storage import StorageProvider


class StorageProviderTests(SimpleTestCase):
    def test_save_open_delete_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with override_settings(MEDIA_ROOT=tmpdir):
                provider = StorageProvider()
                key = provider.save(b"hello world")
                self.assertTrue(provider.exists(key))
                with provider.open(key) as f:
                    self.assertEqual(f.read(), b"hello world")
                provider.delete(key)
                self.assertFalse(provider.exists(key))

    def test_generated_key_is_opaque(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with override_settings(MEDIA_ROOT=tmpdir):
                provider = StorageProvider()
                key = provider.save(b"data")
                self.assertTrue(key.startswith("documents/"))
                self.assertEqual(len(key.split("/")[-1]), 32)

    def test_explicit_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with override_settings(MEDIA_ROOT=tmpdir):
                provider = StorageProvider()
                key = provider.save(b"data", key="custom/path.txt")
                self.assertEqual(key, "custom/path.txt")
