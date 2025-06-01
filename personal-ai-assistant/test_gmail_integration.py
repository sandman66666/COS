#!/usr/bin/env python3
"""
Test script for diagnosing Gmail integration issues
"""

import os
import sys
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("=== Gmail Integration Test ===\n")

# Test 1: Check environment variables
print("1. Checking environment variables...")
required_vars = ['ANTHROPIC_API_KEY', 'GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET']
for var in required_vars:
    value = os.environ.get(var)
    if value:
        print(f"   ✓ {var} is set (length: {len(value)})")
    else:
        print(f"   ✗ {var} is NOT set")

# Test 2: Test Claude client
print("\n2. Testing Claude client initialization...")
try:
    from anthropic import Anthropic
    claude_client = Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
    print("   ✓ Claude client initialized successfully")
    
    # Try a simple test message
    try:
        response = claude_client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=100,
            messages=[{"role": "user", "content": "Say 'test successful' if you can read this."}]
        )
        print(f"   ✓ Claude test response: {response.content[0].text}")
    except Exception as e:
        print(f"   ✗ Claude test failed: {str(e)}")
except Exception as e:
    print(f"   ✗ Failed to initialize Claude client: {str(e)}")

# Test 3: Test Gmail connector
print("\n3. Testing Gmail connector...")
try:
    from backend.integrations.gmail.gmail_connector import GmailConnector
    print("   ✓ GmailConnector imported successfully")
except Exception as e:
    print(f"   ✗ Failed to import GmailConnector: {str(e)}")

# Test 4: Test Email Intelligence module
print("\n4. Testing Email Intelligence module...")
try:
    from backend.core.claude_integration.email_intelligence import EmailIntelligence
    print("   ✓ EmailIntelligence imported successfully")
    
    # Initialize with Claude client
    if 'claude_client' in locals():
        email_intelligence = EmailIntelligence(claude_client)
        print("   ✓ EmailIntelligence initialized successfully")
except Exception as e:
    print(f"   ✗ Failed to import/initialize EmailIntelligence: {str(e)}")

# Test 5: Manual Gmail API test
print("\n5. Testing manual Gmail API connection...")
print("   To test Gmail API:")
print("   1. Run the Flask app: python3 backend/main.py")
print("   2. Go to http://127.0.0.1:8080/login")
print("   3. Complete OAuth flow")
print("   4. Check Settings page for connection status")
print("   5. Try syncing emails")

# Test 6: Common issues and solutions
print("\n=== Common Issues and Solutions ===")
print("\n1. 'OAuth token issue detected' error:")
print("   - Token may be expired. Try logging out and logging in again.")
print("   - Check that the OAuth scope includes: https://www.googleapis.com/auth/gmail.readonly")

print("\n2. 'Gmail API access not properly configured' error:")
print("   - Enable Gmail API in Google Cloud Console")
print("   - Ensure OAuth consent screen is configured")
print("   - Add test users if app is in testing mode")

print("\n3. 'Permission denied' error:")
print("   - Check OAuth scopes include Gmail access")
print("   - User must consent to Gmail access during login")

print("\n4. No emails found:")
print("   - Check the days_back parameter (default is 30 days)")
print("   - Ensure the Gmail account has emails in that timeframe")

print("\n5. Claude integration issues:")
print("   - Check ANTHROPIC_API_KEY is valid")
print("   - Ensure Claude model name is correct (claude-3-opus-20240229)")
print("   - Check API rate limits")

print("\n=== Next Steps ===")
print("1. Run the Flask app and check browser console for errors")
print("2. Enable debug logging: export FLASK_ENV=development")
print("3. Check logs for specific error messages")
print("4. Test with a fresh OAuth token") 