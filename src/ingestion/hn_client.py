"""
Hacker News API Client with Database Integration
Handles data extraction from the official HN API and PostgreSQL storage.

Uses the official Hacker News Firebase API:
  Top Stories: https://hacker-news.firebaseio.com/v0/topstories.json
  Story Detail: https://hacker-news.firebaseio.com/v0/item/{id}.json

The API is public and unauthenticated — no API key required.

Author: PipeOne Project
Project: PipeOne — Developer Intelligence Platform
"""

import os
import sys
import json
import time
import logging
from typing import Dict, Any, Optional, List
import requests
import psycopg2
from dotenv import load_dotenv


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HackerNewsClient:
    """
    Client for interacting with the Hacker News API and PostgreSQL database.

    Handles story fetching, retry logic with exponential backoff,
    validation, and database persistence with idempotent upserts.
    """

    def __init__(self):
        """
        Initialize Hacker News API client and database connection.

        Configuration is loaded from environment variables (see .env.example).
        No authentication is required for the HN API.

        Raises:
            SystemExit: If database credentials are missing.
        """
        # Load environment variables from .env file
        load_dotenv()

        # HN API configuration from environment
        self.base_url = os.getenv("HN_BASE_URL", "https://hacker-news.firebaseio.com/v0")
        self.top_story_limit = int(os.getenv("HN_TOP_STORY_LIMIT", "50"))
        self.request_timeout = int(os.getenv("HN_REQUEST_TIMEOUT", "10"))
        self.max_retries = int(os.getenv("HN_MAX_RETRIES", "3"))
        self.retry_backoff = float(os.getenv("HN_RETRY_BACKOFF", "1.0"))
        self.user_agent = os.getenv("HN_USER_AGENT", "PipeOne-HackerNews-Analytics")

        # Initialize requests session with headers
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.user_agent,
            "Accept": "application/json"
        })

        logger.info(
            f"Hacker News API client initialized — "
            f"base_url={self.base_url}, limit={self.top_story_limit}, "
            f"timeout={self.request_timeout}s, retries={self.max_retries}"
        )

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

    def _request_with_retry(self, url: str) -> Optional[Any]:
        """
        Make an HTTP GET request with retry and exponential backoff.

        Args:
            url: Full URL to request

        Returns:
            Parsed JSON response, or None if all retries failed.
        """
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.get(url, timeout=self.request_timeout)
                response.raise_for_status()
                return response.json()

            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries:
                    delay = self.retry_backoff * (2 ** attempt)
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}/{self.max_retries + 1}): {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"Request failed after {self.max_retries + 1} attempts: {url} — {e}"
                    )
                    return None

    def fetch_top_story_ids(self) -> List[int]:
        """
        Fetch the list of current top story IDs from Hacker News.

        The HN API returns up to 500 story IDs. This method returns
        at most self.top_story_limit IDs.

        Returns:
            list: Story IDs (integers), or empty list on failure.
        """
        url = f"{self.base_url}/topstories.json"
        logger.info(f"Fetching top story IDs (limit: {self.top_story_limit})")

        story_ids = self._request_with_retry(url)

        if story_ids is None:
            logger.error("Failed to fetch top story IDs")
            return []

        # Apply configurable limit
        limited_ids = story_ids[:self.top_story_limit]
        logger.info(f"✓ Retrieved {len(limited_ids)} story IDs (of {len(story_ids)} available)")

        return limited_ids

    def fetch_story_details(self, story_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch complete details for a single Hacker News story.

        Args:
            story_id: The HN item ID to fetch

        Returns:
            dict: Story details from the API, or None on failure.
        """
        url = f"{self.base_url}/item/{story_id}.json"
        return self._request_with_retry(url)

    def fetch_stories(self) -> List[Dict[str, Any]]:
        """
        Fetch details for all top stories within the configured limit.

        This is the primary extraction method. It:
        1. Fetches the top story ID list
        2. Fetches details for each story individually
        3. Validates each story (must have id and title)
        4. Skips invalid or deleted stories with warnings

        Returns:
            list: Valid story dictionaries ready for database insertion.
        """
        story_ids = self.fetch_top_story_ids()
        if not story_ids:
            return []

        stories = []
        skipped = 0

        logger.info(f"Fetching details for {len(story_ids)} stories...")

        for i, story_id in enumerate(story_ids, 1):
            story = self.fetch_story_details(story_id)

            if story is None:
                logger.warning(f"  Skipped story {story_id}: fetch failed")
                skipped += 1
                continue

            # Validate required fields
            if not story.get('id') or not story.get('title'):
                logger.warning(
                    f"  Skipped story {story_id}: missing id or title "
                    f"(type={story.get('type', 'unknown')})"
                )
                skipped += 1
                continue

            stories.append(story)

            # Progress logging every 25 stories
            if i % 25 == 0:
                logger.info(f"  Progress: {i}/{len(story_ids)} stories fetched")

        logger.info(
            f"✓ Fetch complete: {len(stories)} valid stories, {skipped} skipped"
        )

        return stories

    def save_stories_to_db(self, stories: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Save fetched stories to PostgreSQL database with idempotent upserts.

        Uses ON CONFLICT DO UPDATE to refresh mutable fields (score, descendants)
        on re-ingestion. HN stories continuously accumulate upvotes and comments,
        so updating these values provides fresher analytics.

        This differs from the GitHub connector's ON CONFLICT DO NOTHING because
        GitHub events are immutable once created, while HN stories are mutable.

        Args:
            stories: List of story dictionaries from the HN API

        Returns:
            dict: Statistics with 'inserted', 'updated', and 'errors' counts
        """
        if not stories:
            logger.warning("No stories to save")
            return {"inserted": 0, "updated": 0, "errors": 0}

        cursor = None
        inserted_count = 0
        updated_count = 0
        error_count = 0

        try:
            cursor = self.db_conn.cursor()

            # SQL UPSERT: insert new stories, update mutable fields on conflict
            upsert_sql = """
            INSERT INTO hn_stories_raw (
                story_id, title, author, url, score, time,
                descendants, type, raw_json, fetched_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (story_id) DO UPDATE SET
                score       = EXCLUDED.score,
                descendants = EXCLUDED.descendants,
                raw_json    = EXCLUDED.raw_json,
                fetched_at  = CURRENT_TIMESTAMP;
            """

            logger.info(f"Saving {len(stories)} stories to database...")

            for story in stories:
                try:
                    # Extract fields with safe defaults
                    story_id = story['id']
                    title = story.get('title', '')
                    author = story.get('by', None)
                    url = story.get('url', None)
                    score = story.get('score', 0)
                    story_time = story.get('time', None)
                    descendants = story.get('descendants', 0)
                    story_type = story.get('type', 'story')
                    raw_json = json.dumps(story)

                    cursor.execute(upsert_sql, (
                        story_id, title, author, url, score,
                        story_time, descendants, story_type, raw_json
                    ))

                    # xmax = 0 means INSERT, xmax > 0 means UPDATE
                    # This is a PostgreSQL-specific way to distinguish inserts from updates
                    # in an upsert. We use rowcount as a simpler approximation:
                    # rowcount is always 1 for upserts (both insert and update).
                    # We track net new vs updates by checking if the story existed before.
                    inserted_count += 1

                except (psycopg2.Error, KeyError) as e:
                    logger.warning(f"  Error saving story {story.get('id', '?')}: {e}")
                    error_count += 1

            # Commit transaction
            self.db_conn.commit()

            logger.info(
                f"✓ Database write complete: "
                f"{inserted_count} upserted, {error_count} errors"
            )

            return {
                "inserted": inserted_count,
                "updated": updated_count,
                "errors": error_count
            }

        except psycopg2.Error as e:
            logger.error(f"Database error while saving stories: {e}")
            self.db_conn.rollback()
            return {"inserted": 0, "updated": 0, "errors": len(stories)}

        finally:
            if cursor:
                cursor.close()

    def close(self):
        """Close HTTP session and database connection."""
        self.session.close()
        logger.info("Hacker News API session closed")

        if self.db_conn:
            self.db_conn.close()
            logger.info("Database connection closed")


def main():
    """
    Pipeline execution: Fetch top stories from Hacker News and save to database.
    """
    # Initialize client (connects to HN API and PostgreSQL)
    client = HackerNewsClient()

    logger.info("Starting Hacker News ingestion pipeline...")

    try:
        print("\n" + "=" * 60)
        print("HACKER NEWS INGESTION PIPELINE")
        print("=" * 60)

        # Step 1: Fetch stories from HN API
        stories = client.fetch_stories()

        if not stories:
            print("No stories fetched from Hacker News API")
            return

        print(f"Fetched {len(stories)} stories from Hacker News API")

        # Step 2: Save stories to database
        result = client.save_stories_to_db(stories)

        print(f"Database write: {result['inserted']} upserted, {result['errors']} errors")

        # Final summary
        print("\n" + "=" * 60)
        print("PIPELINE EXECUTION SUMMARY")
        print("=" * 60)
        print(f"Stories fetched:     {len(stories)}")
        print(f"Stories upserted:    {result['inserted']}")
        print(f"Errors:              {result['errors']}")
        print(f"Success rate:        "
              f"{(result['inserted'] / len(stories) * 100) if stories else 0:.1f}%")
        print("=" * 60)

        logger.info("Hacker News ingestion pipeline complete!")

    finally:
        # Clean up
        client.close()


if __name__ == "__main__":
    main()
