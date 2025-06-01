#!/usr/bin/env python3
"""
Debug script to check email insights after sync
"""

import os
import sys
import json
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("=== Email Insights Debug Tool ===\n")

# Import Flask app
from backend.main import create_app, sync_status

app = create_app()

print("1. Checking sync_status global variable:")
print(f"   - is_syncing: {sync_status.get('is_syncing', 'Not set')}")
print(f"   - progress: {sync_status.get('progress', 'Not set')}")
print(f"   - user_email: {sync_status.get('user_email', 'Not set')}")
print(f"   - last_sync: {sync_status.get('last_sync', 'Not set')}")
print(f"   - Has email_insights: {'email_insights' in sync_status}")

if 'email_insights' in sync_status:
    insights = sync_status['email_insights']
    print("\n2. Email insights content:")
    print(f"   - Type: {type(insights)}")
    print(f"   - Keys: {list(insights.keys()) if isinstance(insights, dict) else 'Not a dict'}")
    
    if isinstance(insights, dict):
        print(f"   - Status: {insights.get('status', 'No status')}")
        print(f"   - Message: {insights.get('message', 'No message')}")
        print(f"   - Key relationships: {len(insights.get('key_relationships', []))}")
        print(f"   - Active projects: {len(insights.get('active_projects', []))}")
        print(f"   - Action items: {len(insights.get('action_items', []))}")
        print(f"   - Important info: {len(insights.get('important_information', []))}")
        
        # Show sample data if available
        if insights.get('key_relationships'):
            print("\n   Sample key relationship:")
            print(f"   {json.dumps(insights['key_relationships'][0], indent=4)}")

print("\n3. Checking session storage:")
print(f"   - Session directory: {app.config.get('SESSION_FILE_DIR', 'Not set')}")

session_dir = app.config.get('SESSION_FILE_DIR')
if session_dir and os.path.exists(session_dir):
    files = os.listdir(session_dir)
    print(f"   - Session files: {len(files)}")
    
    # Check the most recent session file
    if files:
        latest_file = max([os.path.join(session_dir, f) for f in files], key=os.path.getmtime)
        print(f"   - Latest session: {os.path.basename(latest_file)}")
        print(f"   - Modified: {time.ctime(os.path.getmtime(latest_file))}")

print("\n4. Testing email intelligence module:")
try:
    from backend.core.claude_integration.email_intelligence import EmailIntelligence
    from anthropic import Anthropic
    
    claude_client = Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
    email_intelligence = EmailIntelligence(claude_client)
    print("   ✓ EmailIntelligence module loaded successfully")
    
    # Check if the module has the right methods
    methods = ['analyze_recent_emails', '_create_relationships_prompt', '_create_patterns_prompt']
    for method in methods:
        if hasattr(email_intelligence, method):
            print(f"   ✓ Method '{method}' exists")
        else:
            print(f"   ✗ Method '{method}' missing")
            
except Exception as e:
    print(f"   ✗ Error loading EmailIntelligence: {str(e)}")

print("\n5. Recommendations:")
print("   - Make sure you're logged in with Gmail OAuth")
print("   - Click 'Sync Emails' in Settings")
print("   - Wait for sync to complete (check progress)")
print("   - Then visit /email-insights")
print("   - Check browser console for JavaScript errors")
print("   - Check Flask logs for server errors") 