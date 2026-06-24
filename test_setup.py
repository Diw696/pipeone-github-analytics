"""
Quick setup validation script for PipeOne
Tests that all dependencies are installed and configured correctly.
"""

import sys

def test_imports():
    """Test that all required packages can be imported."""
    print("Testing package imports...")
    
    try:
        import requests
        print("✓ requests installed")
    except ImportError:
        print("✗ requests not found - run: pip install -r requirements.txt")
        return False
    
    try:
        from dotenv import load_dotenv
        print("✓ python-dotenv installed")
    except ImportError:
        print("✗ python-dotenv not found - run: pip install -r requirements.txt")
        return False
    
    try:
        import psycopg2
        print("✓ psycopg2-binary installed")
    except ImportError:
        print("✗ psycopg2-binary not found - run: pip install -r requirements.txt")
        return False
    
    return True

def test_env_file():
    """Check if .env file exists."""
    import os
    print("\nChecking environment configuration...")
    
    if os.path.exists(".env"):
        print("✓ .env file found")
        
        # Check if GITHUB_TOKEN is set
        from dotenv import load_dotenv
        load_dotenv()
        
        token = os.getenv("GITHUB_TOKEN")
        if token:
            print(f"✓ GITHUB_TOKEN is set (length: {len(token)} chars)")
            return True
        else:
            print("✗ GITHUB_TOKEN not set in .env file")
            print("  Add this line to .env: GITHUB_TOKEN=your_token_here")
            return False
    else:
        print("✗ .env file not found")
        print("  Run: cp .env.example .env")
        print("  Then add your GitHub token to .env")
        return False

def test_github_client():
    """Test that GitHubClient can be imported and initialized."""
    print("\nTesting GitHubClient...")
    
    try:
        from src.ingestion.github_client import GitHubClient
        print("✓ GitHubClient imported successfully")
        
        # Try to initialize (will fail if no token)
        try:
            client = GitHubClient()
            print("✓ GitHubClient initialized")
            client.close()
            return True
        except SystemExit:
            print("✗ GitHubClient initialization failed (missing token)")
            return False
            
    except ImportError as e:
        print(f"✗ Failed to import GitHubClient: {e}")
        return False

def main():
    """Run all setup tests."""
    print("="*60)
    print("PipeOne Setup Validation")
    print("="*60)
    
    results = []
    
    # Test 1: Package imports
    results.append(("Package imports", test_imports()))
    
    # Test 2: Environment configuration
    results.append(("Environment config", test_env_file()))
    
    # Test 3: GitHubClient
    results.append(("GitHubClient module", test_github_client()))
    
    # Summary
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    
    all_passed = all(result for _, result in results)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print("="*60)
    
    if all_passed:
        print("\n🎉 All tests passed! You're ready to run:")
        print("   python src/ingestion/github_client.py")
    else:
        print("\n⚠️  Some tests failed. Fix the issues above and try again.")
        sys.exit(1)

if __name__ == "__main__":
    main()
