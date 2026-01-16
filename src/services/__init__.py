"""External service integrations."""

from .tavily_service import TavilyService
from .deepseek_service import DeepSeekService
from .source_config import (
    SourceConfig,
    SourcePriority,
    get_expanded_therapeutic_areas,
    get_expanded_phases,
)

__all__ = [
    "TavilyService",
    "DeepSeekService",
    "SourceConfig",
    "SourcePriority",
    "get_expanded_therapeutic_areas",
    "get_expanded_phases",
]
