import uuid

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage


class StorageProvider:
    """Backend-agnostic file storage behind an opaque key.

    The database stores only the opaque ``storage_key``; bytes are handled by
    Django's configured default storage (filesystem by default, S3/Azure via
    django-storages later). The domain never parses the key.
    """

    def save(self, content, *, key: str | None = None) -> str:
        """Persist ``content`` and return its opaque storage key.

        Accepts bytes/str (wrapped in a ``ContentFile``), Django file objects
        (with ``.chunks()``), or other file-like objects (read into memory).
        """
        if key is None:
            key = self._generate_key()
        if isinstance(content, (str, bytes, bytearray, memoryview)):
            content = ContentFile(content)
        elif not hasattr(content, "chunks"):
            content = ContentFile(content.read())
        return default_storage.save(key, content)

    def open(self, key: str):
        return default_storage.open(key, "rb")

    def exists(self, key: str) -> bool:
        return default_storage.exists(key)

    def delete(self, key: str) -> None:
        if default_storage.exists(key):
            default_storage.delete(key)

    def url(self, key: str) -> str:
        return default_storage.url(key)

    @staticmethod
    def _generate_key() -> str:
        return f"documents/{uuid.uuid4().hex}"
