"""
GitHub Events API Client
Securely handles authentication and requests to the GitHub Events API.
"""

import os
import logging
import sys
from typing import Optional, Dict, Any
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
    A client for interacting with the GitHub Events API.
    
    Attributes:
        base_url (str): The base URL for GitHub API
        session (requests.Session): HTTP session with authentication headers
    """
    
    BASE_URL = "https://api.github.com"
    EVENTS_ENDPOINT = "/events"
    
    def __init__(self):
        """
        Initialize the GitHub API client with secure token loading.
        
        Raises:
            SystemExit: If GITHUB_TOKEN is not found in environment variables
        """
        # Load environment variables from .env file
        load_dotenv()
        
        # Retrieve GitHub token from environment
        self.github_token: Optional[str] = os.getenv("GITHUB_TOKEN")
        
        # Validate token presence
        if not self.github_token:
            logger.error(
                "GITHUB_TOKEN not found in environment variables. "
                "Please set it in your .env file."
            )
            sys.exit(1)
        
        # Initialize requests session
        self.session = requests.Session()
        
        # Set authorization headers
        self.session.headers.update({
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "PipeOne-GitHub-Analytics"
        })
        
        logger.info("GitHub API client initialized successfully")
    
    def get_public_events(self, per_page: int = 100, page: int = 1) -> Dict[str, Any]:
        """
        Fetch public GitHub events from the Events API.
        
        Args:
            per_page (int): Number of events per page (max 100)
            page (int): Page number for pagination
            
        Returns:
            Dict containing:
                - status_code (int): HTTP status code
                - data (list): List of event objects if successful
                - error (str): Error message if request failed
                - rate_limit (dict): Rate limit information
        """
        url = f"{self.BASE_URL}{self.EVENTS_ENDPOINT}"
        params = {
            "per_page": min(per_page, 100),  # GitHub max is 100
            "page": page
        }
        
        try:
            logger.info(f"Fetching events: page={page}, per_page={per_page}")
            response = self.session.get(url, params=params, timeout=30)
            
            # Extract rate limit information
            rate_limit_info = {
                "limit": response.headers.get("X-RateLimit-Limit"),
                "remaining": response.headers.get("X-RateLimit-Remaining"),
                "reset": response.headers.get("X-RateLimit-Reset")
            }
            
            # Check response status
            if response.status_code == 200:
                logger.info(
                    f"Successfully fetched {len(response.json())} events. "
                    f"Rate limit remaining: {rate_limit_info['remaining']}"
                )
                return {
                    "status_code": response.status_code,
                    "data": response.json(),
                    "rate_limit": rate_limit_info
                }
            else:
                logger.error(
                    f"Failed to fetch events. Status: {response.status_code}, "
                    f"Response: {response.text}"
                )
                return {
                    "status_code": response.status_code,
                    "error": response.text,
                    "rate_limit": rate_limit_info
                }
                
        except requests.exceptions.Timeout:
            logger.error("Request timed out while fetching GitHub events")
            return {
                "status_code": 408,
                "error": "Request timeout"
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            return {
                "status_code": 500,
                "error": str(e)
            }
    
    def check_rate_limit(self) -> Dict[str, Any]:
        """
        Check current rate limit status for authenticated requests.
        
        Returns:
            Dict containing rate limit information
        """
        url = f"{self.BASE_URL}/rate_limit"
        
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                rate_data = response.json()
                logger.info(f"Rate limit check successful: {rate_data}")
                return {
                    "status_code": response.status_code,
                    "data": rate_data
                }
            else:
                logger.error(f"Rate limit check failed: {response.status_code}")
                return {
                    "status_code": response.status_code,
                    "error": response.text
                }
        except requests.exceptions.RequestException as e:
            logger.error(f"Rate limit check failed: {str(e)}")
            return {
                "status_code": 500,
                "error": str(e)
            }
    
    def close(self):
        """Close the HTTP session."""
        self.session.close()
        logger.info("GitHub API client session closed")


def main():
    """
    Main function to demonstrate GitHub API client usage.
    """
    # Initialize client
    client = GitHubClient()
    
    try:
        # Check rate limit
        logger.info("Checking rate limit...")
        rate_limit_response = client.check_rate_limit()
        
        if rate_limit_response["status_code"] == 200:
            core_limit = rate_limit_response["data"]["resources"]["core"]
            logger.info(
                f"API Rate Limit: {core_limit['remaining']}/{core_limit['limit']} "
                f"remaining"
            )
        
        # Fetch public events
        logger.info("Fetching public GitHub events...")
        events_response = client.get_public_events(per_page=10, page=1)
        
        if events_response["status_code"] == 200:
            events = events_response["data"]
            logger.info(f"Successfully retrieved {len(events)} events")
            
            # Display first event as example
            if events:
                first_event = events[0]
                logger.info(
                    f"Sample event: type={first_event['type']}, "
                    f"actor={first_event['actor']['login']}, "
                    f"repo={first_event['repo']['name']}"
                )
        else:
            logger.error(f"Failed to fetch events: {events_response.get('error')}")
    
    finally:
        # Clean up
        client.close()


if __name__ == "__main__":
    main()
