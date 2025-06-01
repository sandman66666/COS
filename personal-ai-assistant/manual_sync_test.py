#!/usr/bin/env python3
"""
Manual sync test to debug email insights
"""

import os
import sys
from dotenv import load_dotenv
load_dotenv()

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("=== Manual Email Sync Test ===\n")

# Check environment
print("1. Checking environment...")
if not os.environ.get('ANTHROPIC_API_KEY'):
    print("❌ ANTHROPIC_API_KEY not set!")
    exit(1)
else:
    print("✅ ANTHROPIC_API_KEY is set")

# Import modules
print("\n2. Importing modules...")
try:
    from anthropic import Anthropic
    from backend.core.claude_integration.email_intelligence import EmailIntelligence
    print("✅ Modules imported successfully")
except Exception as e:
    print(f"❌ Import error: {e}")
    exit(1)

# Initialize Claude
print("\n3. Initializing Claude client...")
claude_client = Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
email_intelligence = EmailIntelligence(claude_client)

# Get user input
print("\n4. Enter your Gmail access token (from browser session):")
print("   You can find this by:")
print("   - Open browser DevTools (F12)")
print("   - Go to Application > Cookies")
print("   - Look for session cookie and decode it")
print("   OR just press Enter to skip this test")
access_token = input("Access token: ").strip()

if not access_token:
    print("\nSkipping live test. Would need access token from active session.")
    print("\nTo properly test:")
    print("1. Login to the app")
    print("2. Click 'Sync Emails' in Settings")
    print("3. Watch the Flask terminal for detailed logs")
    print("4. Visit http://127.0.0.1:8080/test-insights to see raw data")
else:
    print("\n5. Testing email analysis...")
    user_email = input("Your email address: ")
    
    try:
        insights = email_intelligence.analyze_recent_emails(user_email, access_token, days_back=7)
        
        print("\n=== Results ===")
        print(f"Status: {insights.get('status')}")
        print(f"Message: {insights.get('message')}")
        print(f"\nKey Relationships: {len(insights.get('key_relationships', []))}")
        if insights.get('key_relationships'):
            print(f"  First: {insights['key_relationships'][0]}")
        
        print(f"\nActive Projects: {len(insights.get('active_projects', []))}")
        if insights.get('active_projects'):
            print(f"  First: {insights['active_projects'][0]}")
            
        print(f"\nAction Items: {len(insights.get('action_items', []))}")
        if insights.get('action_items'):
            print(f"  First: {insights['action_items'][0]}")
            
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc() 