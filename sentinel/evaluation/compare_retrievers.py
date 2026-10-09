from sentinel.evaluation.retrieval_eval import (
    evaluate_retriever,
    load_retrieval_benchmark,
)

from sentinel.retrieval.retriever import (
    build_policy_retriever,
)

from sentinel.retrieval.embedding_retriever import (
    build_embedding_retriever,
)


def print_metrics(
    name,
    metrics,
):
    print()
    print(name)
    print("-" * 50)

    print(
        f"Recall@1: "
        f"{metrics.recall_at_1:.3f}"
    )

    print(
        f"Recall@3: "
        f"{metrics.recall_at_3:.3f}"
    )

    print(
        f"Recall@5: "
        f"{metrics.recall_at_5:.3f}"
    )

    print(
        f"MRR:      "
        f"{metrics.mrr:.3f}"
    )


def main():

    benchmark = load_retrieval_benchmark()

    print()
    print("=" * 70)
    print("SentinelAI Retriever Comparison")
    print("=" * 70)





    tfidf_retriever = (
        build_policy_retriever()
    )

    tfidf_metrics, _ = evaluate_retriever(
        retriever=tfidf_retriever,
        cases=benchmark,
        top_k=5,
    )

    print_metrics(
        "TF-IDF",
        tfidf_metrics,
    )





    embedding_retriever = (
        build_embedding_retriever()
    )

    embedding_metrics, _ = evaluate_retriever(
        retriever=embedding_retriever,
        cases=benchmark,
        top_k=5,
    )

    print_metrics(
        "Embeddings + FAISS",
        embedding_metrics,
    )

    print()
    print("=" * 70)


if __name__ == "__main__":
    main()