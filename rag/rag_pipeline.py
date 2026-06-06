"""RAG Pipeline for SentinelIQ.

Provides a retrieval interface over the FAISS vector index built from
policy PDFs. Loads the index from disk at initialisation and caches it
in memory for the duration of the application session.

Requirements: 7.5, 7.6
"""

from __future__ import annotations

import os
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings


class RAGPipeline:
    """FAISS-backed retrieval-augmented generation pipeline.

    Loads a pre-built FAISS index from disk and provides a retrieve()
    method that returns the top-k most relevant policy text chunks for
    a given query string.
    """

    def __init__(
        self,
        index_path: str = "rag/faiss_index",
        embedding_model: str = "models/embedding-001",
    ) -> None:
        """Load FAISS index from disk and cache in memory.

        Args:
            index_path: Path to the directory containing the saved
                FAISS index and docstore files.
            embedding_model: Google GenerativeAI embedding model name
                used when building the index (must match).

        Raises:
            FileNotFoundError: If the index path does not exist.
        """
        index_dir = Path(index_path)
        if not index_dir.exists():
            raise FileNotFoundError(
                f"FAISS index directory not found: {index_path}. "
                "Run rag/build_faiss_index.py first to build the index."
            )

        self._embeddings = GoogleGenerativeAIEmbeddings(
            model=embedding_model,
            google_api_key=os.environ.get("GEMINI_API_KEY"),
        )

        # Load and cache the vectorstore in memory
        self._vectorstore = FAISS.load_local(
            str(index_dir),
            self._embeddings,
            allow_dangerous_deserialization=True,
        )

    def retrieve(self, query: str, k: int = 3) -> list[str]:
        """Retrieve the top-k most relevant policy chunks.

        Args:
            query: Text query derived from the transaction's active
                feature flags and bank name.
            k: Number of top-similar chunks to return (default 3,
                configurable via config.rag_top_k).

        Returns:
            List of up to k policy text chunks (strings) ordered by
            relevance. Returns an empty list if the query is empty.
        """
        if not query or not query.strip():
            return []

        results = self._vectorstore.similarity_search(query, k=k)
        return [doc.page_content for doc in results]
