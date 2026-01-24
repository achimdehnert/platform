"""
Core Search Service - Document Chunking

Smart text chunking for long documents.
"""

from typing import List

from .models import Chunk


class DocumentChunker:
    """Smart text chunking for long documents"""

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        strategy: str = "semantic",
    ):
        """
        Initialize chunker

        Args:
            chunk_size: Target tokens per chunk
            chunk_overlap: Overlap tokens between chunks
            strategy: Chunking strategy ("semantic", "sentence", "fixed")
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.strategy = strategy

    def chunk_text(self, text: str, metadata: dict = None) -> List[Chunk]:
        """
        Split text into chunks

        Args:
            text: Text to chunk
            metadata: Metadata to attach to chunks

        Returns:
            List of Chunk objects
        """
        if self.strategy == "semantic":
            return self._semantic_chunking(text, metadata)
        elif self.strategy == "sentence":
            return self._sentence_chunking(text, metadata)
        else:
            return self._fixed_chunking(text, metadata)

    def _semantic_chunking(self, text: str, metadata: dict = None) -> List[Chunk]:
        """Split at paragraph boundaries"""
        chunks = []
        paragraphs = text.split("\n\n")

        current_chunk = []
        current_tokens = 0
        start_char = 0

        for para in paragraphs:
            para_tokens = len(para.split())

            if current_tokens + para_tokens > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_text = "\n\n".join(current_chunk)
                chunks.append(
                    Chunk(
                        idx=len(chunks),
                        text=chunk_text,
                        start_char=start_char,
                        end_char=start_char + len(chunk_text),
                        metadata=metadata or {},
                    )
                )

                # Start new chunk with overlap
                if len(current_chunk) > 1:
                    overlap_text = current_chunk[-1]
                    current_chunk = [overlap_text]
                    current_tokens = len(overlap_text.split())
                    start_char = start_char + len(chunk_text) - len(overlap_text)
                else:
                    current_chunk = []
                    current_tokens = 0
                    start_char = start_char + len(chunk_text)

            current_chunk.append(para)
            current_tokens += para_tokens

        # Add final chunk
        if current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            chunks.append(
                Chunk(
                    idx=len(chunks),
                    text=chunk_text,
                    start_char=start_char,
                    end_char=start_char + len(chunk_text),
                    metadata=metadata or {},
                )
            )

        return chunks

    def _sentence_chunking(self, text: str, metadata: dict = None) -> List[Chunk]:
        """Split at sentence boundaries"""
        # Simple sentence splitting
        sentences = text.replace("! ", "!|").replace("? ", "?|").replace(". ", ".|").split("|")

        chunks = []
        current_chunk = []
        current_tokens = 0
        start_char = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_tokens = len(sentence.split())

            if current_tokens + sentence_tokens > self.chunk_size and current_chunk:
                chunk_text = " ".join(current_chunk)
                chunks.append(
                    Chunk(
                        idx=len(chunks),
                        text=chunk_text,
                        start_char=start_char,
                        end_char=start_char + len(chunk_text),
                        metadata=metadata or {},
                    )
                )

                # Overlap: keep last sentence
                if current_chunk:
                    overlap_text = current_chunk[-1]
                    current_chunk = [overlap_text]
                    current_tokens = len(overlap_text.split())
                    start_char = start_char + len(chunk_text) - len(overlap_text)
                else:
                    current_chunk = []
                    current_tokens = 0
                    start_char = start_char + len(chunk_text)

            current_chunk.append(sentence)
            current_tokens += sentence_tokens

        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunks.append(
                Chunk(
                    idx=len(chunks),
                    text=chunk_text,
                    start_char=start_char,
                    end_char=start_char + len(chunk_text),
                    metadata=metadata or {},
                )
            )

        return chunks

    def _fixed_chunking(self, text: str, metadata: dict = None) -> List[Chunk]:
        """Fixed-size chunking by tokens"""
        words = text.split()
        chunks = []

        chunk_words = self.chunk_size
        overlap_words = self.chunk_overlap
        step = chunk_words - overlap_words

        for i in range(0, len(words), step):
            chunk_text = " ".join(words[i : i + chunk_words])
            start_char = len(" ".join(words[:i]))

            chunks.append(
                Chunk(
                    idx=len(chunks),
                    text=chunk_text,
                    start_char=start_char,
                    end_char=start_char + len(chunk_text),
                    metadata=metadata or {},
                )
            )

            if i + chunk_words >= len(words):
                break

        return chunks


__all__ = ["DocumentChunker"]
