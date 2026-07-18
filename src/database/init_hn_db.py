"""
Hacker News Database Initialization Script
Creates the hn_stories_raw table and required indexes.

Author: PipeOne Project
Project: PipeOne — Developer Intelligence Platform
"""

import os
import sys
import logging
import psycopg2
from dotenv import load_dotenv


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_db_connection():
    """
    Establish connection to PostgreSQL database using credentials from .env

    Returns:
        psycopg2.connection: Database connection object

    Raises:
        SystemExit: If required environment variables are missing
    """
    # Load environment variables from .env file
    load_dotenv()

    # Retrieve database credentials
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

    logger.info(f"Connecting to database: {db_config['database']} at {db_config['host']}:{db_config['port']}")

    try:
        conn = psycopg2.connect(**db_config)
        logger.info("✓ Database connection established")
        return conn
    except psycopg2.Error as e:
        logger.error(f"Failed to connect to database: {e}")
        sys.exit(1)


def create_hn_stories_table(conn):
    """
    Create the hn_stories_raw table with proper schema.

    Schema mirrors the structure of github_events_raw:
      - Primary key for idempotent upserts (ON CONFLICT)
      - Frequently queried fields as typed columns
      - Complete raw payload preserved as JSONB
      - Ingestion timestamp for freshness monitoring

    Args:
        conn: PostgreSQL connection object
    """
    cursor = None

    try:
        cursor = conn.cursor()

        # SQL to create the raw stories table
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS hn_stories_raw (
            story_id       BIGINT PRIMARY KEY,
            title          TEXT,
            author         VARCHAR(100),
            url            TEXT,
            score          INTEGER DEFAULT 0,
            time           BIGINT,
            descendants    INTEGER DEFAULT 0,
            type           VARCHAR(20),
            raw_json       JSONB NOT NULL,
            fetched_at     TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """

        logger.info("Creating table: hn_stories_raw")
        cursor.execute(create_table_sql)
        logger.info("✓ Table hn_stories_raw created successfully")

        # Create index on author for contributor-style queries
        create_author_index_sql = """
        CREATE INDEX IF NOT EXISTS idx_hn_stories_author
        ON hn_stories_raw(author);
        """

        logger.info("Creating index: idx_hn_stories_author")
        cursor.execute(create_author_index_sql)
        logger.info("✓ Index idx_hn_stories_author created successfully")

        # Create index on time for temporal queries
        create_time_index_sql = """
        CREATE INDEX IF NOT EXISTS idx_hn_stories_time
        ON hn_stories_raw(time);
        """

        logger.info("Creating index: idx_hn_stories_time")
        cursor.execute(create_time_index_sql)
        logger.info("✓ Index idx_hn_stories_time created successfully")

        # Create index on score for ranking queries
        create_score_index_sql = """
        CREATE INDEX IF NOT EXISTS idx_hn_stories_score
        ON hn_stories_raw(score);
        """

        logger.info("Creating index: idx_hn_stories_score")
        cursor.execute(create_score_index_sql)
        logger.info("✓ Index idx_hn_stories_score created successfully")

        # Commit the transaction
        conn.commit()
        logger.info("✓ All changes committed to database")

    except psycopg2.Error as e:
        logger.error(f"Database error during table creation: {e}")
        conn.rollback()
        logger.warning("Transaction rolled back")
        raise

    finally:
        if cursor:
            cursor.close()
            logger.debug("Cursor closed")


def verify_schema(conn):
    """
    Verify that the table and indexes were created successfully.

    Args:
        conn: PostgreSQL connection object
    """
    cursor = None

    try:
        cursor = conn.cursor()

        # Check if table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'hn_stories_raw'
            );
        """)
        table_exists = cursor.fetchone()[0]

        if table_exists:
            logger.info("✓ Table 'hn_stories_raw' verified")

            # Get column count
            cursor.execute("""
                SELECT COUNT(*)
                FROM information_schema.columns
                WHERE table_name = 'hn_stories_raw';
            """)
            column_count = cursor.fetchone()[0]
            logger.info(f"  Columns: {column_count}")

            # Check indexes
            cursor.execute("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'hn_stories_raw';
            """)
            indexes = cursor.fetchall()
            logger.info(f"  Indexes: {len(indexes)} created")
            for idx in indexes:
                logger.info(f"    - {idx[0]}")
        else:
            logger.error("✗ Table 'hn_stories_raw' not found")

    except psycopg2.Error as e:
        logger.error(f"Error during schema verification: {e}")

    finally:
        if cursor:
            cursor.close()


def main():
    """
    Main execution: Initialize Hacker News database schema for PipeOne.
    """
    print("=" * 60)
    print("PipeOne — Hacker News Database Initialization")
    print("=" * 60)

    conn = None

    try:
        # Step 1: Connect to database
        conn = get_db_connection()

        # Step 2: Create table and indexes
        print("\n" + "-" * 60)
        print("Creating schema...")
        print("-" * 60)
        create_hn_stories_table(conn)

        # Step 3: Verify schema
        print("\n" + "-" * 60)
        print("Verifying schema...")
        print("-" * 60)
        verify_schema(conn)

        print("\n" + "=" * 60)
        print("Hacker News database initialization complete!")
        print("=" * 60)
        print("\nYou can now run the HN ingestion pipeline:")
        print("  python src/ingestion/hn_client.py")

    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        print("\n" + "=" * 60)
        print("Hacker News database initialization failed")
        print("=" * 60)
        sys.exit(1)

    finally:
        # Clean up: Always close the connection
        if conn:
            conn.close()
            logger.info("Database connection closed")


if __name__ == "__main__":
    main()
