import numpy as np
import faiss

from sentence_transformers import SentenceTransformer

from sentinel.retrieval.documents import (
    DocumentChunk,
    load_policy_chunks,
)

from sentinel.retrieval.retriever import SearchResult






DEFAULT_EMBEDDING_MODEL = (
    "sentence-transformers/all-MiniLM-L6-v2"
)






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


        self.model = SentenceTransformer(
            model_name,
            device="cpu",
        )


        texts = [
            self._chunk_to_search_text(chunk)
            for chunk in chunks
        ]


        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )


        self.embeddings = np.asarray(
            embeddings,
            dtype=np.float32,
        )

        self.embeddings = np.ascontiguousarray(
            self.embeddings
        )


        dimension = self.embeddings.shape[1]





        self.index = faiss.IndexFlatIP(
            dimension
        )


        self.index.add(
            self.embeddings
        )





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



        k = min(
            top_k,
            len(self.chunks),
        )


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


        scores, indexes = self.index.search(
            query_embedding,
            k,
        )

        results: list[SearchResult] = []

        for score, index in zip(
            scores[0],
            indexes[0],
        ):



            if index < 0:
                continue

            results.append(
                SearchResult(
                    chunk=self.chunks[index],
                    score=float(score),
                )
            )

        return results






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