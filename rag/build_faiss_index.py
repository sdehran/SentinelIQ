"""FAISS Index Builder for SentinelIQ RAG Pipeline.

Ingests policy PDFs from rag/policy_docs/, chunks them at 500 characters
with 50-character overlap, embeds using Google GenerativeAI Embeddings
(models/embedding-001), and persists the FAISS index + docstore to
rag/faiss_index/.

Requirements: 7.1, 7.2, 7.3, 7.4
"""

from __future__ import annotations

import os
from pathlib import Path

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings


class FAISSIndexBuilder:
    """Builds a FAISS vector index from policy PDF documents.

    The builder loads all PDFs from the specified directory, splits them
    into chunks of 500 characters with 50-character overlap, embeds each
    chunk using Google GenerativeAI Embeddings (models/embedding-001),
    and saves the resulting FAISS index and docstore to disk.
    """

    def __init__(
        self,
        pdf_dir: str = "rag/policy_docs",
        output_path: str = "rag/faiss_index",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        embedding_model: str = "models/embedding-001",
    ) -> None:
        """Initialise the FAISS index builder.

        Args:
            pdf_dir: Directory containing source policy PDFs.
            output_path: Directory where the FAISS index will be saved.
            chunk_size: Maximum number of characters per text chunk.
            chunk_overlap: Number of overlapping characters between chunks.
            embedding_model: Google GenerativeAI embedding model name.
        """
        self.pdf_dir = Path(pdf_dir)
        self.output_path = Path(output_path)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embedding_model = embedding_model

    def build(self) -> None:
        """Load PDFs, chunk, embed, and save the FAISS index to disk.

        Raises:
            FileNotFoundError: If the PDF directory does not exist or
                contains no PDF files.
            ValueError: If no text chunks are produced from the PDFs.
        """
        if not self.pdf_dir.exists():
            raise FileNotFoundError(
                f"PDF directory not found: {self.pdf_dir}"
            )

        # Collect all PDF files
        pdf_files = sorted(self.pdf_dir.glob("*.pdf"))
        if not pdf_files:
            raise FileNotFoundError(
                f"No PDF files found in {self.pdf_dir}"
            )

        # Load all PDFs into LangChain documents
        all_documents = []
        for pdf_path in pdf_files:
            loader = PyPDFLoader(str(pdf_path))
            documents = loader.load()
            all_documents.extend(documents)

        # Split documents into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        chunks = text_splitter.split_documents(all_documents)

        if not chunks:
            raise ValueError(
                "No text chunks produced from the PDF documents."
            )

        # Create embeddings
        embeddings = GoogleGenerativeAIEmbeddings(
            model=self.embedding_model,
            google_api_key=os.environ.get("GEMINI_API_KEY"),
        )

        # Build FAISS vectorstore from chunks
        vectorstore = FAISS.from_documents(chunks, embeddings)

        # Save index and docstore to disk
        self.output_path.mkdir(parents=True, exist_ok=True)
        vectorstore.save_local(str(self.output_path))

        print(
            f"FAISS index built successfully: {len(chunks)} chunks "
            f"from {len(pdf_files)} PDFs saved to {self.output_path}"
        )


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    builder = FAISSIndexBuilder()
    builder.build()
