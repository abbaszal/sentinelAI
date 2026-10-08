import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from sentinel.retrieval.retriever import (
    SearchResult,
    build_policy_retriever,
)


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

DEFAULT_BENCHMARK_PATH = Path(
    "data/benchmarks/retrieval_benchmark.json"
)


# ---------------------------------------------------------
# Benchmark data models
# ---------------------------------------------------------

@dataclass
class RetrievalBenchmarkCase:
    """
    One retrieval question with known correct evidence.
    """

    case_id: str
    query: str
    expected_document_id: str
    expected_section: str


@dataclass
class RetrievalCaseResult:
    """
    Evaluation result for one benchmark case.
    """

    case: RetrievalBenchmarkCase

    rank: int | None

    retrieved_document_ids: list[str]
    retrieved_sections: list[str]


@dataclass
class RetrievalMetrics:
    """
    Aggregate metrics for a retrieval evaluation run.
    """

    total_cases: int

    recall_at_1: float
    recall_at_3: float
    recall_at_5: float

    mrr: float


# ---------------------------------------------------------
# Retriever interface
# ---------------------------------------------------------

class RetrieverProtocol(Protocol):
    """
    Any retriever we evaluate should implement
    this search interface.

    This allows us to evaluate:

        TF-IDF
        embeddings
        FAISS
        hybrid retrieval

    using exactly the same benchmark code.
    """

    def search(
        self,
        query: str,
        top_k: int = 3,
    ) -> list[SearchResult]:
        ...


# ---------------------------------------------------------
# Benchmark loading
# ---------------------------------------------------------

def load_retrieval_benchmark(
    path: Path = DEFAULT_BENCHMARK_PATH,
) -> list[RetrievalBenchmarkCase]:

    raw_data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    cases: list[RetrievalBenchmarkCase] = []

    for item in raw_data:

        case = RetrievalBenchmarkCase(
            case_id=item["id"],
            query=item["query"],
            expected_document_id=(
                item["expected_document_id"]
            ),
            expected_section=(
                item["expected_section"]
            ),
        )

        cases.append(case)

    return cases


# ---------------------------------------------------------
# Matching logic
# ---------------------------------------------------------

def is_expected_result(
    result: SearchResult,
    case: RetrievalBenchmarkCase,
) -> bool:
    """
    Determine whether one search result matches
    the expected benchmark evidence.
    """

    return (
        result.chunk.document_id
        == case.expected_document_id
        and
        result.chunk.section
        == case.expected_section
    )


# ---------------------------------------------------------
# Single-case evaluation
# ---------------------------------------------------------

def evaluate_case(
    retriever: RetrieverProtocol,
    case: RetrievalBenchmarkCase,
    top_k: int = 5,
) -> RetrievalCaseResult:

    results = retriever.search(
        query=case.query,
        top_k=top_k,
    )

    correct_rank: int | None = None

    for rank, result in enumerate(
        results,
        start=1,
    ):

        if is_expected_result(
            result,
            case,
        ):
            correct_rank = rank
            break

    return RetrievalCaseResult(
        case=case,
        rank=correct_rank,
        retrieved_document_ids=[
            result.chunk.document_id
            for result in results
        ],
        retrieved_sections=[
            result.chunk.section
            for result in results
        ],
    )


# ---------------------------------------------------------
# Metrics
# ---------------------------------------------------------

def calculate_recall_at_k(
    results: list[RetrievalCaseResult],
    k: int,
) -> float:

    if not results:
        return 0.0

    successful = sum(
        1
        for result in results
        if (
            result.rank is not None
            and result.rank <= k
        )
    )

    return successful / len(results)


def calculate_mrr(
    results: list[RetrievalCaseResult],
) -> float:
    """
    Mean Reciprocal Rank.

    rank 1 -> 1 / 1 = 1.0
    rank 2 -> 1 / 2 = 0.5
    rank 3 -> 1 / 3 = 0.333...
    not found -> 0
    """

    if not results:
        return 0.0

    reciprocal_ranks: list[float] = []

    for result in results:

        if result.rank is None:
            reciprocal_ranks.append(0.0)
        else:
            reciprocal_ranks.append(
                1.0 / result.rank
            )

    return sum(reciprocal_ranks) / len(
        reciprocal_ranks
    )


# ---------------------------------------------------------
# Full evaluation
# ---------------------------------------------------------

def evaluate_retriever(
    retriever: RetrieverProtocol,
    cases: list[RetrievalBenchmarkCase],
    top_k: int = 5,
) -> tuple[
    RetrievalMetrics,
    list[RetrievalCaseResult],
]:

    case_results = [
        evaluate_case(
            retriever=retriever,
            case=case,
            top_k=top_k,
        )
        for case in cases
    ]

    metrics = RetrievalMetrics(
        total_cases=len(case_results),

        recall_at_1=calculate_recall_at_k(
            case_results,
            1,
        ),

        recall_at_3=calculate_recall_at_k(
            case_results,
            3,
        ),

        recall_at_5=calculate_recall_at_k(
            case_results,
            5,
        ),

        mrr=calculate_mrr(
            case_results
        ),
    )

    return metrics, case_results


# ---------------------------------------------------------
# Console reporting
# ---------------------------------------------------------

def print_evaluation_report(
    metrics: RetrievalMetrics,
    results: list[RetrievalCaseResult],
) -> None:

    print()
    print("=" * 70)
    print("SentinelAI Retrieval Evaluation")
    print("=" * 70)

    print()
    print(f"Cases:    {metrics.total_cases}")

    print(
        f"Recall@1: {metrics.recall_at_1:.3f}"
    )

    print(
        f"Recall@3: {metrics.recall_at_3:.3f}"
    )

    print(
        f"Recall@5: {metrics.recall_at_5:.3f}"
    )

    print(
        f"MRR:      {metrics.mrr:.3f}"
    )

    print()
    print("=" * 70)
    print("Per-case results")
    print("=" * 70)

    for result in results:

        rank_display = (
            result.rank
            if result.rank is not None
            else "NOT FOUND"
        )

        print()
        print(
            f"{result.case.case_id}"
        )

        print(
            f"Query: {result.case.query}"
        )

        print(
            "Expected:",
            result.case.expected_document_id,
            "/",
            result.case.expected_section,
        )

        print(
            f"Rank: {rank_display}"
        )

        if result.rank is None:

            print(
                "Retrieved sections:"
            )

            for document_id, section in zip(
                result.retrieved_document_ids,
                result.retrieved_sections,
            ):
                print(
                    f"  - {document_id} / {section}"
                )


# ---------------------------------------------------------
# Command-line run
# ---------------------------------------------------------

if __name__ == "__main__":

    benchmark = load_retrieval_benchmark()

    retriever = build_policy_retriever()

    metrics, results = evaluate_retriever(
        retriever=retriever,
        cases=benchmark,
        top_k=5,
    )

    print_evaluation_report(
        metrics,
        results,
    )