"""Maximal Marginal Relevance (MMR) diversity filter (ADR-087).

Re-ranks search results to balance relevance and diversity.
Reference: Carbonell & Goldstein (1998), OpenClaw src/memory/mmr.ts
"""

from __future__ import annotations

import numpy as np

from platform_search.service import SearchResult


def maximal_marginal_relevance(
    query_embedding: list[float],
    result_embeddings: list[list[float]],
    results: list[SearchResult],
    lambda_param: float = 0.7,
    top_k: int = 10,
) -> list[SearchResult]:
    """Re-rank results for diversity via MMR.

    MMR = lambda * sim(q, d) - (1-lambda) * max(sim(d, d_selected))

    Args:
        query_embedding: Query vector.
        result_embeddings: Embedding vectors for each result.
        results: Search results to re-rank.
        lambda_param: Balance relevance vs diversity (0=diverse, 1=relevant).
        top_k: Number of results to return.

    Returns:
        Re-ranked search results.
    """
    if not results or not result_embeddings:
        return results[:top_k]

    query_vec = np.array(query_embedding)
    doc_vecs = np.array(result_embeddings)

    query_sims = _cosine_similarity_batch(query_vec, doc_vecs)

    selected_indices: list[int] = []
    remaining = set(range(len(results)))

    for _ in range(min(top_k, len(results))):
        best_idx = -1
        best_score = float("-inf")

        for idx in remaining:
            relevance = float(query_sims[idx])

            if selected_indices:
                selected_vecs = doc_vecs[selected_indices]
                redundancy = float(
                    np.max(
                        _cosine_similarity_batch(
                            doc_vecs[idx], selected_vecs
                        )
                    )
                )
            else:
                redundancy = 0.0

            mmr_score = (
                lambda_param * relevance
                - (1 - lambda_param) * redundancy
            )

            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = idx

        if best_idx >= 0:
            selected_indices.append(best_idx)
            remaining.discard(best_idx)

    return [results[i] for i in selected_indices]


def _cosine_similarity_batch(
    vec: np.ndarray,
    matrix: np.ndarray,
) -> np.ndarray:
    """Compute cosine similarity between a vector and a matrix of vectors."""
    if vec.ndim == 1:
        vec = vec.reshape(1, -1)
    if matrix.ndim == 1:
        matrix = matrix.reshape(1, -1)

    vec_norm = vec / (np.linalg.norm(vec, axis=1, keepdims=True) + 1e-10)
    matrix_norm = matrix / (
        np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-10
    )
    similarities: np.ndarray = np.dot(vec_norm, matrix_norm.T).flatten()
    return similarities
