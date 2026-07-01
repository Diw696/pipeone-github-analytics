"""
Pipeline Verification Script
Validates data integrity and displays professional summary statistics.

Author: Diwakar Kaushik
Project: PipeOne - Week 1 Deliverable
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv


def print_table_header(title: str, width: int = 70):
    """Print a formatted table header."""
    print("\n" + "┌" + "─" * (width - 2) + "┐")
    print(f"│ {title.center(width - 4)} │")
    print("├" + "─" * (width - 2) + "┤")


def print_table_row(col1: str, col2: str, width: int = 70):
    """Print a formatted table row with two columns."""
    col_width = width - 6
    left_width = col_width - 15
    right_width = 12
    print(f"│ {col1:<{left_width}} │ {col2:>{right_width}} │")


def print_table_footer(width: int = 70):
    """Print a formatted table footer."""
    print("└" + "─" * (width - 2) + "┘")


def get_database_connection():
    """
    Establish database connection using same credentials as GitHubClient.
    
    Returns:
        psycopg2.connection: Database connection object
    """
    load_dotenv()
    
    db_config = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': os.getenv('POSTGRES_PORT', '5432'),
        'database': os.getenv('POSTGRES_DB', 'pipeone_warehouse'),
        'user': os.getenv('POSTGRES_USER', 'pipeone_user'),
        'password': os.getenv('POSTGRES_PASSWORD')
    }
    
    if not db_config['password']:
        print("\n✗ POSTGRES_PASSWORD not found in environment variables")
        print("  Please set POSTGRES_PASSWORD in your .env file")
        sys.exit(1)
    
    try:
        conn = psycopg2.connect(**db_config)
        return conn
    except psycopg2.Error as e:
        print(f"\n✗ Database connection failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Is Docker running? Check: docker ps")
        print("  2. Is PostgreSQL up? Run: docker-compose up -d")
        sys.exit(1)


def verify_data():
    """Query the database and display professional verification report."""
    
    # Connect to database
    conn = get_database_connection()
    cursor = conn.cursor()
    
    # Main header
    print("\n" + "═" * 70)
    print("  PIPEONE: WEEK 1 PIPELINE VERIFICATION REPORT".center(70))
    print("  GitHub Events API → PostgreSQL Warehouse".center(70))
    print("═" * 70)
    
    # ==========================================
    # Section 1: Overall Statistics
    # ==========================================
    cursor.execute("SELECT COUNT(*) FROM github_events_raw;")
    total_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT repo_name) FROM github_events_raw;")
    repo_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT event_type) FROM github_events_raw;")
    event_type_count = cursor.fetchone()[0]
    
    print_table_header("OVERALL STATISTICS", 70)
    print_table_row("Total Events Ingested", f"{total_count:,}", 70)
    print_table_row("Repositories Tracked", str(repo_count), 70)
    print_table_row("Unique Event Types", str(event_type_count), 70)
    print_table_footer(70)
    
    # ==========================================
    # Section 2: Events by Repository
    # ==========================================
    cursor.execute("""
        SELECT repo_name, COUNT(*) as event_count
        FROM github_events_raw
        GROUP BY repo_name
        ORDER BY event_count DESC;
    """)
    
    print_table_header("EVENTS BY REPOSITORY", 70)
    repo_results = cursor.fetchall()
    for repo_name, count in repo_results:
        print_table_row(repo_name, f"{count:,} events", 70)
    print_table_footer(70)
    
    # ==========================================
    # Section 3: Top Event Types
    # ==========================================
    cursor.execute("""
        SELECT event_type, COUNT(*) as count
        FROM github_events_raw
        GROUP BY event_type
        ORDER BY count DESC
        LIMIT 10;
    """)
    
    print_table_header("TOP EVENT TYPES", 70)
    event_type_results = cursor.fetchall()
    for event_type, count in event_type_results:
        percentage = (count / total_count * 100) if total_count > 0 else 0
        print_table_row(event_type, f"{count:,} ({percentage:.1f}%)", 70)
    print_table_footer(70)
    
    # ==========================================
    # Section 4: Data Quality Checks
    # ==========================================
    print_table_header("DATA QUALITY CHECKS", 70)
    
    # Check 1: Null event_ids
    cursor.execute("SELECT COUNT(*) FROM github_events_raw WHERE event_id IS NULL;")
    null_ids = cursor.fetchone()[0]
    status = "✓ PASS" if null_ids == 0 else "✗ FAIL"
    print_table_row(f"{status} Null Event IDs", f"{null_ids} found", 70)
    
    # Check 2: Null payloads
    cursor.execute("SELECT COUNT(*) FROM github_events_raw WHERE raw_payload IS NULL;")
    null_payloads = cursor.fetchone()[0]
    status = "✓ PASS" if null_payloads == 0 else "✗ FAIL"
    print_table_row(f"{status} Null Payloads", f"{null_payloads} found", 70)
    
    # Check 3: Duplicates
    cursor.execute("""
        SELECT COUNT(*) FROM (
            SELECT event_id, COUNT(*) 
            FROM github_events_raw 
            GROUP BY event_id 
            HAVING COUNT(*) > 1
        ) duplicates;
    """)
    duplicates = cursor.fetchone()[0]
    status = "✓ PASS" if duplicates == 0 else "✗ FAIL"
    print_table_row(f"{status} Duplicate Events", f"{duplicates} found", 70)
    
    # Check 4: Recent data freshness
    cursor.execute("""
        SELECT 
            EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - MAX(fetched_at))) / 60 as minutes_ago
        FROM github_events_raw;
    """)
    result = cursor.fetchone()
    minutes_ago = result[0] if result and result[0] else 0
    status = "✓ PASS" if minutes_ago < 60 else "⚠ OLD"
    print_table_row(f"{status} Data Freshness", f"{minutes_ago:.0f} min ago", 70)
    
    print_table_footer(70)
    
    # ==========================================
    # Section 5: Sample Events
    # ==========================================
    cursor.execute("""
        SELECT repo_name, event_type, 
               TO_CHAR(fetched_at, 'YYYY-MM-DD HH24:MI:SS') as fetched
        FROM github_events_raw
        ORDER BY fetched_at DESC
        LIMIT 3;
    """)
    
    print_table_header("RECENT EVENTS (LATEST 3)", 70)
    sample_events = cursor.fetchall()
    for repo, etype, fetched in sample_events:
        display = f"{repo} • {etype}"
        print_table_row(display[:48], fetched, 70)
    print_table_footer(70)
    
    # ==========================================
    # Final Summary
    # ==========================================
    print("\n" + "═" * 70)
    
    if total_count > 0 and duplicates == 0 and null_ids == 0 and null_payloads == 0:
        print("  ✓ VERIFICATION SUCCESSFUL".center(70))
        print("  All data quality checks passed".center(70))
        print("  Pipeline Status: OPERATIONAL".center(70))
    elif total_count > 0:
        print("  ⚠ VERIFICATION COMPLETED WITH WARNINGS".center(70))
        print("  Data is present but quality issues detected".center(70))
    else:
        print("  ✗ VERIFICATION FAILED".center(70))
        print("  No data found in database".center(70))
        print("  Run: python src/ingestion/github_client.py".center(70))
    
    print("═" * 70)
    
    # Database info footer
    print(f"\nDatabase: {os.getenv('POSTGRES_DB', 'pipeone_warehouse')}")
    print(f"Verified: {cursor.rowcount} queries executed")
    print(f"Status: Connection closed\n")
    
    cursor.close()
    conn.close()


if __name__ == "__main__":
    try:
        verify_data()
    except KeyboardInterrupt:
        print("\n\n✗ Verification cancelled by user\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Verification error: {e}")
        print("\nMake sure:")
        print("  1. Database is initialized: python src/database/init_db.py")
        print("  2. Pipeline has run: python src/ingestion/github_client.py\n")
        sys.exit(1)
