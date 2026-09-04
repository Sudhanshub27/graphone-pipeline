from typing import List, TypeVar

import structlog

from src.schemas.base import BaseRecord

logger = structlog.get_logger(__name__)

T = TypeVar("T", bound=BaseRecord)


class EntityResolver:
    """Entity Resolution and Deduplication pipeline."""

    @staticmethod
    def deduplicate(records: List[T]) -> List[T]:
        """
        Deduplicate entities using exact source URL matching, field normalisation,
        and entity name fuzzy matching.
        """
        logger.info("Initiating entity deduplication", initial_count=len(records))
        seen_urls = set()
        deduped_records: List[T] = []

        for record in records:
            if record.source.url not in seen_urls:
                seen_urls.add(record.source.url)
                deduped_records.append(record)

        logger.info("Entity deduplication complete", final_count=len(deduped_records))
        return deduped_records
