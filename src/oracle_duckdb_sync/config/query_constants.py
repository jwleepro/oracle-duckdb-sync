"""
Query-related constants for Oracle-DuckDB Sync.

This module defines all query-related constants to avoid magic numbers
and improve maintainability.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class QueryConstants:
    """Constants for query operations."""

    # Default row limits
    DEFAULT_QUERY_LIMIT: int = 100
    """Default number of rows to fetch in queries"""

    # Type detection and conversion
    SAMPLE_SIZE_FOR_TYPE_DETECTION: int = 1000
    """Number of rows to sample for automatic type detection"""

    TYPE_CONVERSION_THRESHOLD: float = 0.9
    """Threshold (0.0-1.0) for automatic type conversion confidence"""

    # Aggregation defaults
    DEFAULT_AGGREGATION_INTERVAL: str = '10 minutes'
    """Default time interval for aggregation queries"""

    # Incremental loading
    INCREMENTAL_FETCH_BATCH_SIZE: int = 10000
    """Batch size for incremental data fetching"""


# Global instance for easy access
QUERY_CONSTANTS = QueryConstants()
