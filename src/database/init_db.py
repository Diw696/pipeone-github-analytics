"""
Database Initialization Script
Creates the github_events_raw table and required indexes.

Author: Diwakar Kaushik
Project: PipeOne - H1: APIs to Warehouse
"""

import os
import sys
import logging
import psycopg2
from psycopg2 import sql
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


def create_raw_events_table(conn):
    """
    Create the github_events_raw table with proper schema.
    
    Args:
        conn: PostgreSQL connection object
    """
    cursor = None
    
    try:
        cursor = conn.cursor()
        
        # SQL to create the raw events table
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS github_events_raw (
            event_id        VARCHAR(50) PRIMARY KEY,
            repo_name       VARCHAR(100) NOT NULL,
            event_type      VARCHAR(50),
            fetched_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            raw_payload     JSONB NOT NULL
        );
        """
        
        logger.info("Creating table: github_events_raw")
        cursor.execute(create_table_sql)
        logger.info("✓ Table github_events_raw created successfully")
        
        # Create composite index on (repo_name, event_type)
        create_index_sql = """
        CREATE INDEX IF NOT EXISTS idx_repo_event_type 
        ON github_events_raw(repo_name, event_type);
        """
        
        logger.info("Creating composite index: idx_repo_event_type")
        cursor.execute(create_index_sql)
        logger.info("✓ Index idx_repo_event_type created successfully")
        
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
                AND table_name = 'github_events_raw'
            );
        """)
        table_exists = cursor.fetchone()[0]
        
        if table_exists:
            logger.info("✓ Table 'github_events_raw' verified")
            
            # Get column count
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.columns 
                WHERE table_name = 'github_events_raw';
            """)
            column_count = cursor.fetchone()[0]
            logger.info(f"  Columns: {column_count}")
            
            # Check indexes
            cursor.execute("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = 'github_events_raw';
            """)
            indexes = cursor.fetchall()
            logger.info(f"  Indexes: {len(indexes)} created")
            for idx in indexes:
                logger.info(f"    - {idx[0]}")
        else:
            logger.error("✗ Table 'github_events_raw' not found")
    
    except psycopg2.Error as e:
        logger.error(f"Error during schema verification: {e}")
    
    finally:
        if cursor:
            cursor.close()


def main():
    """
    Main execution: Initialize database schema for PipeOne.
    """
    print("="*60)
    print("PipeOne Database Initialization")
    print("="*60)
    
    conn = None
    
    try:
        # Step 1: Connect to database
        conn = get_db_connection()
        
        # Step 2: Create table and indexes
        print("\n" + "-"*60)
        print("Creating schema...")
        print("-"*60)
        create_raw_events_table(conn)
        
        # Step 3: Verify schema
        print("\n" + "-"*60)
        print("Verifying schema...")
        print("-"*60)
        verify_schema(conn)
        
        print("\n" + "="*60)
        print("✓ Database initialization complete!")
        print("="*60)
        print("\nYou can now run the ingestion pipeline:")
        print("  python src/ingestion/github_client.py")
        
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        print("\n" + "="*60)
        print("✗ Database initialization failed")
        print("="*60)
        sys.exit(1)
    
    finally:
        # Clean up: Always close the connection
        if conn:
            conn.close()
            logger.info("Database connection closed")


if __name__ == "__main__":
    main()
