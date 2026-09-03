"""Unit test suite for Vector Store indexing and hybrid semantic search."""

import pytest

from src.vector.vector_store import (
    VectorStoreManager,
    compute_dense_text_embedding,
    cosine_similarity,
)


def test_embedding_generation_and_cosine_similarity():
    """Test dense text embedding vector generation and normalization."""
    vec1 = compute_dense_text_embedding("Autonomous AI Agents and LLM Ingestion")
    vec2 = compute_dense_text_embedding("Autonomous AI Agents and LLM Ingestion")
    vec3 = compute_dense_text_embedding("Unrelated cooking recipe text")

    assert len(vec1) == 128
    assert len(vec2) == 128

    # Identical texts yield 1.0 cosine similarity
    sim_identical = cosine_similarity(vec1, vec2)
    assert pytest.approx(sim_identical, 0.01) == 1.0

    # Orthogonal/different texts yield lower similarity
    sim_diff = cosine_similarity(vec1, vec3)
    assert sim_diff < 0.90


def test_vector_store_indexing_and_search():
    """Test indexing entity records and searching across the vector store."""
    manager = VectorStoreManager()
    index_res = manager.index_all_records()

    assert index_res["status"] == "success"
    assert index_res["indexedCount"] >= 0

    # Test search query
    results = manager.search(query="AI", limit=5)
    assert isinstance(results, list)

    for item in results:
        assert "id" in item
        assert "similarity_score" in item
        assert "record_type" in item
        assert "payload" in item
