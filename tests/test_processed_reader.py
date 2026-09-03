from src.dashboard.processed_reader import (
    get_all_processed_records,
    get_processed_entity_log,
    get_processed_stats,
    read_jsonl_records,
)


def test_processed_reader_functions():
    # Read non-existent file returns empty list
    records = read_jsonl_records("non_existent_file.jsonl")
    assert isinstance(records, list)

    all_data = get_all_processed_records()
    assert "startups" in all_data
    assert "products" in all_data
    assert "research_papers" in all_data
    assert "jobs" in all_data
    assert "news" in all_data

    stats = get_processed_stats()
    assert "totalRecords" in stats
    assert "entities" in stats

    res_log = get_processed_entity_log()
    assert "summary" in res_log
    assert "entries" in res_log
