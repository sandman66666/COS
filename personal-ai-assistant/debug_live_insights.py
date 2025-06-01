#!/usr/bin/env python3
"""
Debug script to check live insights data
"""

import sys
sys.path.append('.')

from backend.main import sync_status
import json

print("=== Live Sync Status ===")
print(f"is_syncing: {sync_status.get('is_syncing')}")
print(f"progress: {sync_status.get('progress')}")
print(f"user_email: {sync_status.get('user_email')}")
print(f"last_sync: {sync_status.get('last_sync')}")

if 'email_insights' in sync_status:
    insights = sync_status['email_insights']
    print("\n=== Email Insights ===")
    print(f"Status: {insights.get('status')}")
    print(f"Message: {insights.get('message', 'No message')}")
    
    # Check each category
    for category in ['key_relationships', 'active_projects', 'action_items', 'important_information']:
        if category in insights:
            items = insights[category]
            print(f"\n{category}: {len(items)} items")
            if items and len(items) > 0:
                print(f"First item: {json.dumps(items[0], indent=2)}")
else:
    print("\nNo email_insights in sync_status!")

# Also check if the insights have the right structure
if 'email_insights' in sync_status:
    insights = sync_status['email_insights']
    print("\n=== Insights Structure ===")
    print("Keys:", list(insights.keys())) 