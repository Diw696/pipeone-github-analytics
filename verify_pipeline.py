"""
Pipeline Verification Script
Checks that data was successfully written to the database.
"""

import os
import psycopg2
from dotenv import load_dotenv


def verify_data():
    """Query the database to verify events were inserted."""
    load_dotenv()
    
    # Connect to database
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=os.getenv('POSTGRES_PORT', '5432'),
        database=os.getenv('POSTGRES_DB', 'pipeone_warehouse'),
        user=os.getenv('POSTGRES_USER', 'pipeone_user'),
        password=os.getenv('POSTGRES_PASSWORD')
    )
    
    cursor = conn.cursor()
    
    print("="*60)
    print("DATABASE VERIFICATION")
    print("="*60)
    
    # Query 1: Total events count
    cursor.execute("SELECT COUNT(*) FROM github_events_raw;")
    total_count = cursor.fetchone()[0]
    print(f"\n✓ Total events in database: {total_count}")
    
    # Query 2: Count by repository
    cursor.execute("""
        SELECT repo_name, COUNT(*) as event_count
        FROM github_events_raw
        GROUP BY repo_name
        ORDER BY event_count DESC;
    """)
    
    print("\nEvents by repository:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} events")
    
    # Query 3: Count by event type
    cursor.execute("""
        SELECT event_type, COUNT(*) as count
        FROM github_events_raw
        GROUP BY event_type
        ORDER BY count DESC
        LIMIT 5;
    """)
    
    print("\nTop 5 event types:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} events")
    
    # Query 4: Recent events
    cursor.execute("""
        SELECT repo_name, event_type, fetched_at
        FROM github_events_raw
        ORDER BY fetched_at DESC
        LIMIT 3;
    """)
    
    print("\nMost recent events:")
    for row in cursor.fetchall():
        print(f"  {row[0]} - {row[1]} - {row[2]}")
    
    # Query 5: Check for duplicates (should be 0)
    cursor.execute("""
        SELECT event_id, COUNT(*) 
        FROM github_events_raw 
        GROUP BY event_id 
        HAVING COUNT(*) > 1;
    """)
    
    duplicates = cursor.fetchall()
    print(f"\n✓ Duplicate check: {len(duplicates)} duplicates found (should be 0)")
    
    print("\n" + "="*60)
    print("VERIFICATION COMPLETE")
    print("="*60)
    
    if total_count > 0:
        print("\n🎉 Success! Data is flowing: GitHub API → PostgreSQL")
    else:
        print("\n⚠️  No data found. Run the pipeline first:")
        print("   python src/ingestion/github_client.py")
    
    cursor.close()
    conn.close()


if __name__ == "__main__":
    try:
        verify_data()
    except Exception as e:
        print(f"\n✗ Verification failed: {e}")
        print("\nMake sure:")
        print("  1. Database is initialized: python src/database/init_db.py")
        print("  2. Pipeline has run: python src/ingestion/github_client.py")
