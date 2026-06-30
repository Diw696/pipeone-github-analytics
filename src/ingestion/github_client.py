"""
GitHub Events API Client with Database Integration
Handles authentication, data extraction, and PostgreSQL storage.

Author: Diwakar Kaushik
Project: PipeOne - H1: APIs to Warehouse
"""

import os
import sys
import json
import logging
from typing import Dict, Any, Optional
import requests
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GitHubClient:
    """
    Client for interacting with the GitHub Events API and PostgreSQL database.
    
    Handles authentication, rate limiting, event extraction, and database persistence.
    """
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self):
        """
        Initialize GitHub API client and database connection.
        
        Raises:
            SystemExit: If GITHUB_TOKEN or database credentials are missing.
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
        
        logger.info("GitHub API client initialized successfully")
        
        # Initialize database connection
        self.db_conn = self._connect_to_database()
    
    def _connect_to_database(self) -> Optional[psycopg2.extensions.connection]:
        """
        Establish connection to PostgreSQL database.
        
        Returns:
            psycopg2.connection: Database connection object or None if failed
        """
        # Retrieve database credentials from environment
        db_config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': os.getenv('POSTGRES_PORT', '5432'),
            'database': os.getenv('POSTGRES_DB', 'pipeone_warehouse'),
            'user': os.getenv('POSTGRES_USER', 'pipeone_user'),
            'password': os.getenv('POSTGRES_PASSWORD')
        }
        
        # Validate required credentials
        if not db_config['password']:
            logger.error("POSTGRES_PASSWORD not found in environment variables")
            logger.error("Please set POSTGRES_PASSWORD in your .env file")
            sys.exit(1)
        
        try:
            conn = psycopg2.connect(**db_config)
            logger.info(f"Database connection established: {db_config['database']}")
            return conn
        except psycopg2.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            sys.exit(1)
    
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
    
    def save_events_to_db(self, repo_name: str, events: list) -> Dict[str, int]:
        """
        Save fetched events to PostgreSQL database with idempotency.
        
        Args:
            repo_name: Repository name in format "owner/repo"
            events: List of event dictionaries from GitHub API
        
        Returns:
            dict: Statistics with 'inserted' and 'duplicates' counts
        """
        if not events:
            logger.warning(f"No events to save for {repo_name}")
            return {"inserted": 0, "duplicates": 0}
        
        cursor = None
        inserted_count = 0
        duplicate_count = 0
        
        try:
            cursor = self.db_conn.cursor()
            
            # SQL INSERT with idempotency (ON CONFLICT DO NOTHING)
            insert_sql = """
            INSERT INTO github_events_raw (event_id, repo_name, event_type, raw_payload)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (event_id) DO NOTHING;
            """
            
            logger.info(f"Saving {len(events)} events for {repo_name} to database...")
            
            for event in events:
                # Extract core fields
                event_id = event.get('id')
                event_type = event.get('type')
                
                # Serialize entire event as JSONB
                raw_payload = json.dumps(event)
                
                # Execute insert
                cursor.execute(insert_sql, (event_id, repo_name, event_type, raw_payload))
                
                # Track if row was actually inserted (rowcount > 0) or skipped (duplicate)
                if cursor.rowcount > 0:
                    inserted_count += 1
                else:
                    duplicate_count += 1
            
            # Commit transaction
            self.db_conn.commit()
            
            logger.info(
                f"✓ Database write complete for {repo_name}: "
                f"{inserted_count} new, {duplicate_count} duplicates skipped"
            )
            
            return {"inserted": inserted_count, "duplicates": duplicate_count}
        
        except psycopg2.Error as e:
            logger.error(f"Database error while saving events: {e}")
            self.db_conn.rollback()
            return {"inserted": 0, "duplicates": 0, "error": str(e)}
        
        finally:
            if cursor:
                cursor.close()
    
    def close(self):
        """Close HTTP session and database connection."""
        self.session.close()
        logger.info("GitHub API session closed")
        
        if self.db_conn:
            self.db_conn.close()
            logger.info("Database connection closed")


def main():
    """
    Week 1 pipeline execution: Fetch events from all target repositories and save to database.
    """
    # Initialize client (connects to both GitHub API and PostgreSQL)
    client = GitHubClient()
    
    # Define the official target repository list array
    target_repositories = [
        "facebook/react",
        "microsoft/vscode",
        "vercel/next.js"
    ]
    
    logger.info("Starting Week 1 pipeline execution across target repositories...")
    
    # Track overall statistics
    total_fetched = 0
    total_inserted = 0
    total_duplicates = 0
    
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
                events = result['events']
                event_count = result['event_count']
                total_fetched += event_count
                
                print(f"✓ Fetched {event_count} events from GitHub API")
                print(f"  Rate limit remaining: {result['rate_limit_remaining']}")
                
                # Save events to database
                db_result = client.save_events_to_db(repo, events)
                total_inserted += db_result.get('inserted', 0)
                total_duplicates += db_result.get('duplicates', 0)
                
                print(f"✓ Database write: {db_result['inserted']} new, {db_result['duplicates']} duplicates")
            else:
                print(f"✗ Failed to process {repo}: {result['error']}")
        
        # Final summary
        print("\n" + "="*60)
        print("PIPELINE EXECUTION SUMMARY")
        print("="*60)
        print(f"Total events fetched: {total_fetched}")
        print(f"Total events inserted: {total_inserted}")
        print(f"Total duplicates skipped: {total_duplicates}")
        print(f"Success rate: {(total_inserted / total_fetched * 100) if total_fetched > 0 else 0:.1f}%")
        print("="*60)
        
        logger.info("Pipeline loop complete! All repositories verified.")
        
    finally:
        # Clean up
        client.close()


if __name__ == "__main__":
    main()
