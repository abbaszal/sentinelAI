import numpy as np
import faiss

from sentence_transformers import SentenceTransformer

from sentinel.retrieval.documents import (
    DocumentChunk,
    load_policy_chunks,
)

from sentinel.retrieval.retriever import SearchResult


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

DEFAULT_EMBEDDING_MODEL = (
    "sentence-transformers/all-MiniLM-L6-v2"
)


# ---------------------------------------------------------
# Embedding Retriever
# ---------------------------------------------------------

class EmbeddingPolicyRetriever:
    """
    Semantic policy retriever using:

        Sentence Transformers
        +
        FAISS

    Pipeline:

        policy chunks
            ↓
        dense embeddings
            ↓
        normalized vectors
            ↓
        FAISS index
            ↓
        semantic nearest-neighbor search
    """

    def __init__(
        self,
        chunks: list[DocumentChunk],
        model_name: str = DEFAULT_EMBEDDING_MODEL,
    ) -> None:

        if not chunks:
            raise ValueError(
                "EmbeddingPolicyRetriever requires "
                "at least one chunk."
            )

        self.chunks = chunks
        self.model_name = model_name

        # Force CPU use explicitly.
        self.model = SentenceTransformer(
            model_name,
            device="cpu",
        )

        # Convert chunks to searchable text.
        texts = [
            self._chunk_to_search_text(chunk)
            for chunk in chunks
        ]

        # Create dense embeddings.
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        # FAISS expects float32 arrays.
        self.embeddings = np.asarray(
            embeddings,
            dtype=np.float32,
        )

        self.embeddings = np.ascontiguousarray(
            self.embeddings
        )

        # Determine embedding dimensionality automatically.
        dimension = self.embeddings.shape[1]

        # Inner-product index.
        #
        # Because embeddings are normalized,
        # inner product behaves like cosine similarity.
        self.index = faiss.IndexFlatIP(
            dimension
        )

        # Add all policy vectors to FAISS.
        self.index.add(
            self.embeddings
        )

    # -----------------------------------------------------
    # Internal helper
    # -----------------------------------------------------

    @staticmethod
    def _chunk_to_search_text(
        chunk: DocumentChunk,
    ) -> str:
        """
        Include title and section metadata together
        with content.

        Example:

            NovaShop Payment Policy
            Duplicate Payments
            A possible duplicate payment exists...
        """

        return "\n".join(
            [
                chunk.title,
                chunk.section,
                chunk.content,
            ]
        )

    # -----------------------------------------------------
    # Search
    # -----------------------------------------------------

    def search(
        self,
        query: str,
        top_k: int = 3,
    ) -> list[SearchResult]:

        query = query.strip()

        if not query:
            return []

        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than 0."
            )

        # Do not ask FAISS for more results
        # than actually exist.
        k = min(
            top_k,
            len(self.chunks),
        )

        # Embed query using the SAME model.
        query_embedding = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        query_embedding = np.asarray(
            query_embedding,
            dtype=np.float32,
        )

        query_embedding = np.ascontiguousarray(
            query_embedding
        )

        # Search FAISS.
        scores, indexes = self.index.search(
            query_embedding,
            k,
        )

        results: list[SearchResult] = []

        for score, index in zip(
            scores[0],
            indexes[0],
        ):

            # FAISS may return -1 when nothing exists
            # for a requested position.
            if index < 0:
                continue

            results.append(
                SearchResult(
                    chunk=self.chunks[index],
                    score=float(score),
                )
            )

        return results


# ---------------------------------------------------------
# Factory
# ---------------------------------------------------------

def build_embedding_retriever(
    chunk_size: int = 200,
    overlap: int = 40,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
) -> EmbeddingPolicyRetriever:

    chunks = load_policy_chunks(
        chunk_size=chunk_size,
        overlap=overlap,
    )

    return EmbeddingPolicyRetriever(
        chunks=chunks,
        model_name=model_name,
    )


# ---------------------------------------------------------
# Manual demo
# ---------------------------------------------------------

if __name__ == "__main__":

    retriever = build_embedding_retriever()

    query = (
        "Can I stop my purchase before dispatch?"
    )

    results = retriever.search(
        query=query,
        top_k=5,
    )

    print()
    print(f"Query: {query}")
    print("=" * 70)

    for rank, result in enumerate(
        results,
        start=1,
    ):

        print()
        print(f"Rank: {rank}")

        print(
            f"Score: {result.score:.4f}"
        )

        print(
            f"Document: "
            f"{result.chunk.document_id}"
        )

        print(
            f"Section: "
            f"{result.chunk.section}"
        )

        print()
        print(result.chunk.content)

        print("-" * 70)