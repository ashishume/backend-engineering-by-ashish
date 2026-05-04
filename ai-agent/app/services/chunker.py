from __future__ import annotations

import re

import tiktoken


class ApproximateEncoding:
    """Small fallback tokenizer used only when tiktoken cannot load its cache."""

    def encode(self, text: str) -> list[str]:
        return re.findall(r"\S+\s*", text)

    def decode(self, tokens: list[str]) -> str:
        return "".join(tokens)


class TextChunker:
    """Token-aware recursive chunker for RAG documents."""

    def __init__(
        self, chunk_size: int, chunk_overlap: int, encoding_name: str = "cl100k_base"
    ):
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.encoding_name = encoding_name
        self._encoding: tiktoken.Encoding | ApproximateEncoding | None = None

    @property
    def encoding(self) -> tiktoken.Encoding | ApproximateEncoding:
        """Load the tokenizer only when chunking is actually needed."""

        if self._encoding is None:
            try:
                self._encoding = tiktoken.get_encoding(self.encoding_name)
            except Exception:
                self._encoding = ApproximateEncoding()
        return self._encoding

    def split(self, text: str) -> list[str]:
        """Split text into overlapping chunks sized for embedding models.

        The method first splits by paragraph/sentence-like separators, then
        applies token windows. This keeps chunks semantically coherent while
        still handling very large paragraphs.
        """

        sections = self._split_recursively(text, ["\n\n", "\n", ". ", " "])
        chunks: list[str] = []
        current_tokens: list[int] = []
        for section in sections:
            section_tokens = self.encoding.encode(section)
            if len(section_tokens) > self.chunk_size:
                chunks.extend(self._window_tokens(section_tokens))
                current_tokens = []
                continue

            if len(current_tokens) + len(section_tokens) > self.chunk_size:
                chunks.append(self.encoding.decode(current_tokens).strip())
                overlap = (
                    current_tokens[-self.chunk_overlap :] if self.chunk_overlap else []
                )
                current_tokens = [*overlap, *section_tokens]
            else:
                current_tokens.extend(section_tokens)

        if current_tokens:
            chunks.append(self.encoding.decode(current_tokens).strip())

        return [chunk for chunk in chunks if chunk]

    def _split_recursively(self, text: str, separators: list[str]) -> list[str]:
        """Break text into small semantic sections before token windowing."""

        if not separators:
            return [text]

        separator = separators[0]
        parts = text.split(separator)
        if len(parts) == 1:
            return self._split_recursively(text, separators[1:])

        sections: list[str] = []
        for part in parts:
            candidate = part.strip()
            if not candidate:
                continue
            if len(self.encoding.encode(candidate)) <= self.chunk_size:
                sections.append(candidate + ("." if separator == ". " else ""))
            else:
                sections.extend(self._split_recursively(candidate, separators[1:]))
        return sections

    def _window_tokens(self, tokens: list[int]) -> list[str]:
        """Fallback for text spans that cannot be split semantically enough."""

        chunks: list[str] = []
        step = self.chunk_size - self.chunk_overlap
        for start in range(0, len(tokens), step):
            window = tokens[start : start + self.chunk_size]
            if window:
                chunks.append(self.encoding.decode(window).strip())
        return chunks
