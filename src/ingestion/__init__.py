"""
Multi-Source Ingestion Module
Handles API extraction and data loading for PipeOne.

Connectors:
  - GitHubClient: GitHub Events API ingestion
  - HackerNewsClient: Hacker News API ingestion
"""

from .github_client import GitHubClient
from .hn_client import HackerNewsClient

__all__ = ["GitHubClient", "HackerNewsClient"]

