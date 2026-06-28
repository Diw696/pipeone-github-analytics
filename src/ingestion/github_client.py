"""
GitHub Events API Client
Handles authentication and data extraction from GitHub Events API.

Author: Diwakar Kaushik
Project: PipeOne - H1: APIs to Warehouse
"""

import os
import sys
import logging
from typing import Dict, Any, Optional
import requests
from dotenv import load_dotenv


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GitHubClient:
    """
    Client for interacting with the GitHub Events API.
    
    Handles authentication, rate limiting, and event extraction.
    """
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self):
        """
        Initialize GitHub API client.
        
        Raises:
            SystemExit: If GITHUB_TOKEN is not found in environment.
        """
        # Load environment variables from .env file
        load_dotenv()
        
        # Retrieve and validate GitHub token
        self.token = os.getenv("GITHUB_TOKEN")
        if not self.token:
            logger.error("GITHUB_TOKEN not found in environment variables")
            logger.error("Please set GITHUB_TOKEN in your .env file")
            sys.exit(1)
        
        # Initialize requests session with auth headers
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "PipeOne-GitHub-Analytics"
        })
        
        logger.info("GitHubClient initialized successfully")
    
    def check_rate_limit(self) -> Dict[str, Any]:
        """
        Check current GitHub API rate limit status.
        
        Returns:
            dict: Rate limit information with remaining requests and reset time.
        """
        try:
            url = f"{self.BASE_URL}/rate_limit"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            core_limit = data["resources"]["core"]
            
            logger.info(
                f"Rate limit: {core_limit['remaining']}/{core_limit['limit']} remaining"
            )
            
            return {
                "remaining": core_limit["remaining"],
                "limit": core_limit["limit"],
                "reset": core_limit["reset"]
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to check rate limit: {e}")
            return {"error": str(e)}
    
    def fetch_events(self, repo_name: str, per_page: int = 30) -> Dict[str, Any]:
        """
        Fetch recent events for a GitHub repository.
        
        Args:
            repo_name: Repository in format "owner/repo" (e.g., "vercel/next.js")
            per_page: Number of events per page (max 100, default 30)
        
        Returns:
            dict: Response containing events list or error message.
        """
        try:
            url = f"{self.BASE_URL}/repos/{repo_name}/events"
            params = {"per_page": min(per_page, 100)}
            
            logger.info(f"Fetching events for {repo_name}")
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            events = response.json()
            
            # Log rate limit info from response headers
            remaining = response.headers.get("X-RateLimit-Remaining")
            logger.info(f"Fetched {len(events)} events. Rate limit remaining: {remaining}")
            
            return {
                "repo_name": repo_name,
                "event_count": len(events),
                "events": events,
                "rate_limit_remaining": remaining
            }
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.error(f"Repository not found: {repo_name}")
                return {"error": f"Repository not found: {repo_name}"}
            elif e.response.status_code == 403:
                logger.error("Rate limit exceeded or access forbidden")
                return {"error": "Rate limit exceeded"}
            else:
                logger.error(f"HTTP error: {e}")
                return {"error": str(e)}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return {"error": str(e)}
    
    def close(self):
        """Close the HTTP session."""
        self.session.close()
        logger.info("GitHubClient session closed")


def main():
    """
    Week 1 pipeline execution: Fetch events from all target repositories.
    """
    # Initialize client
    client = GitHubClient()
    
    # Define the official target repository list array
    target_repositories = [
        "facebook/react",
        "microsoft/vscode",
        "vercel/next.js"
    ]
    
    logger.info("Starting Week 1 pipeline execution across target repositories...")
    
    try:
        # Loop through each repository dynamically
        for repo in target_repositories:
            print("\n" + "="*60)
            print(f"PROCESSING REPOSITORY: {repo}")
            print("="*60)
            
            # Check rate limit balance proactively before executing the network call
            rate_limit = client.check_rate_limit()
            if "error" in rate_limit:
                logger.warning(f"Rate limit check failed, continuing anyway...")
            
            # Fetch the live stream payload array
            result = client.fetch_events(repo, per_page=30)
            
            if "error" not in result:
                event_count = result['event_count']
                print(f"✓ Successfully processed {event_count} recent events for {repo}")
                print(f"  Rate limit remaining: {result['rate_limit_remaining']}")
            else:
                print(f"✗ Failed to process {repo}: {result['error']}")
        
        print("\n" + "="*60)
        print("Pipeline loop complete! All repositories verified.")
        print("="*60)
        
    finally:
        # Clean up
        client.close()


if __name__ == "__main__":
    main()
