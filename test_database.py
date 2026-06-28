"""
Database Connection Test Script
Quick validation that PostgreSQL is accessible and credentials work.
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv


def test_connection():
    """Test database connection with credentials from .env"""
    print("="*60)
    print("Database Connection Test")
    print("="*60)
    
    # Load environment variables
    load_dotenv()
    
    # Get credentials
    db_config = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': os.getenv('POSTGRES_PORT', '5432'),
        'database': os.getenv('POSTGRES_DB', 'pipeone_warehouse'),
        'user': os.getenv('POSTGRES_USER', 'pipeone_user'),
        'password': os.getenv('POSTGRES_PASSWORD')
    }
    
    print(f"\nAttempting connection to:")
    print(f"  Host: {db_config['host']}:{db_config['port']}")
    print(f"  Database: {db_config['database']}")
    print(f"  User: {db_config['user']}")
    
    if not db_config['password']:
        print("\n✗ POSTGRES_PASSWORD not set in .env file")
        return False
    
    try:
        # Attempt connection
        conn = psycopg2.connect(**db_config)
        print("\n✓ Connection successful!")
        
        # Get PostgreSQL version
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"\n  PostgreSQL version:")
        print(f"  {version.split(',')[0]}")
        
        cursor.close()
        conn.close()
        
        print("\n" + "="*60)
        print("✓ Database is ready for initialization")
        print("="*60)
        print("\nNext step:")
        print("  python src/database/init_db.py")
        
        return True
        
    except psycopg2.OperationalError as e:
        print(f"\n✗ Connection failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Is Docker running? Check: docker ps")
        print("  2. Is PostgreSQL container up? Run: docker-compose up -d")
        print("  3. Check credentials in .env file")
        return False
    
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
