"""
GitHub Events Ingestion Module
Handles API extraction and data loading for PipeOne.
"""

from .github_client import GitHubClient

__all__ = ["GitHubClient"]
