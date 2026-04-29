from __future__ import annotations
from pathlib import Path
from fastapi import UploadFile
from pypdf import PdfReader
from io import BytesIO


class DocumentLoader:
    """Extract plain text from supported upload formats.

    The loader intentionally returns only text. Chunking, embeddings, and
    metadata enrichment live in separate services so parsing failures are easy
    to isolate from retrieval behavior.
    """

    supported_extensions = {".pdf", ".txt", ".md"}

    async def load(self, upload: UploadFile, max_upload_mb: int) -> tuple[str, str]:
        """Read an uploaded file and return `(text, extension)`.

        Raises `ValueError` for unsupported files, oversized payloads, or files
        that parse successfully but contain no meaningful text.
        """

        filename = upload.filename or "document"
        extension = Path(filename).suffix.lower()
        if extension not in self.supported_extensions:
            raise ValueError("Only PDF, TXT, and MD files are supported")

        raw = await upload.read()
        max_bytes = max_upload_mb * 1024 * 1024
        if len(raw) > max_bytes:
            raise ValueError(f"File is too large. Max upload size is {max_upload_mb}MB")

        if extension == ".pdf":
            text = self._load_pdf(raw)
        else:
            text = raw.decode("utf-8", errors="ignore")

        normalized = self._normalize_text(text)
        if not normalized:
            raise ValueError("The uploaded document did not contain readable text")

        return normalized, extension.lstrip(".")

    def _load_pdf(self, raw: bytes) -> str:
        """Extract text from each PDF page while tolerating sparse pages."""

        reader = PdfReader(BytesIO(raw))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(pages)

    def _normalize_text(self, text: str) -> str:
        """Collapse excessive whitespace while preserving paragraph boundaries."""

        lines = [line.strip() for line in text.replace("\r", "\n").split("\n")]
        paragraphs: list[str] = []
        current: list[str] = []

        for line in lines:
            if line:
                current.append(line)
            elif current:
                paragraphs.append(" ".join(current))
                current = []

        if current:
            paragraphs.append(" ".join(current))

        return "\n\n".join(paragraphs).strip()
