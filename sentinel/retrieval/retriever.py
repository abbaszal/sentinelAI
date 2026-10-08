from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from sentinel.retrieval.documents import (
    DocumentChunk,
    load_policy_chunks,
)


# ---------------------------------------------------------
# Search result model
# ---------------------------------------------------------

@dataclass
class SearchResult:
    """
    Represents one retrieved policy chunk together with
    its similarity score.
    """

    chunk: DocumentChunk
    score: float


# ---------------------------------------------------------
# Policy retriever
# ---------------------------------------------------------

class PolicyRetriever:
    """
    Simple TF-IDF based retrieval system for NovaShop
    policy documents.

    The retriever:

    1. receives policy chunks
    2. converts them into TF-IDF vectors
    3. converts a user query into the same vector space
    4. compares the query against every chunk
    5. returns the highest scoring chunks
    """

    def __init__(
        self,
        chunks: list[DocumentChunk],
    ) -> None:

        if not chunks:
            raise ValueError(
                "PolicyRetriever requires at least one chunk."
            )

        self.chunks = chunks

        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
        )

        texts = [
            self._chunk_to_search_text(chunk)
            for chunk in chunks
        ]

        self.chunk_matrix = (
            self.vectorizer.fit_transform(texts)
        )

    # -----------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------

    @staticmethod
    def _chunk_to_search_text(
        chunk: DocumentChunk,
    ) -> str:
        """
        Combine useful chunk metadata with the actual
        content before indexing.

        Including the section title helps queries such as:

            "duplicate payment"

        match a section called:

            "Duplicate Payments"
        """

        return " ".join(
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
        min_score: float = 0.0,
    ) -> list[SearchResult]:
        """
        Search policy chunks using TF-IDF cosine similarity.

        Args:
            query:
                User search query.

            top_k:
                Maximum number of results to return.

            min_score:
                Ignore results below this similarity score.

        Returns:
            Ranked list of SearchResult objects.
        """

        query = query.strip()

        if not query:
            return []

        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than 0."
            )

        query_vector = (
            self.vectorizer.transform([query])
        )

        similarities = cosine_similarity(
            query_vector,
            self.chunk_matrix,
        )[0]

        ranked_indexes = similarities.argsort()[::-1]

        results: list[SearchResult] = []

        for index in ranked_indexes:

            score = float(
                similarities[index]
            )

            if score < min_score:
                continue

            results.append(
                SearchResult(
                    chunk=self.chunks[index],
                    score=score,
                )
            )

            if len(results) >= top_k:
                break

        return results


# ---------------------------------------------------------
# Factory function
# ---------------------------------------------------------

def build_policy_retriever(
    chunk_size: int = 200,
    overlap: int = 40,
) -> PolicyRetriever:
    """
    Load NovaShop policy documents, chunk them and build
    a TF-IDF policy retriever.
    """

    chunks = load_policy_chunks(
        chunk_size=chunk_size,
        overlap=overlap,
    )

    return PolicyRetriever(chunks)


# ---------------------------------------------------------
# Convenience search function
# ---------------------------------------------------------

def search_policy(
    query: str,
    top_k: int = 3,
) -> list[SearchResult]:
    """
    Convenience function for simple policy searches.

    For now this builds the retriever when called.

    Later we will keep one retriever/index loaded in memory
    instead of rebuilding it for every search.
    """

    retriever = build_policy_retriever()

    return retriever.search(
        query=query,
        top_k=top_k,
    )



if __name__ == "__main__":

    retriever = build_policy_retriever()

    query = "customer was charged twice"

    results = retriever.search(
        query=query,
        top_k=3,
    )

    print()
    print(f"Query: {query}")
    print("=" * 60)

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
            f"Document: {result.chunk.title}"
        )
        print(
            f"Section: {result.chunk.section}"
        )
        print(
            f"Source: {result.chunk.source}"
        )
        print()
        print(result.chunk.content)
        print("-" * 60)