"""Standalone, auditable collocation-feedback agent."""
from .agents import CollocAgent
from .corpus import CorpusIndex

__all__ = ["CollocAgent", "CorpusIndex"]
__version__ = "0.1.0"
