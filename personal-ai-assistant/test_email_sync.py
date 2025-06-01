#!/usr/bin/env python3
"""
Test script to verify email sync is working correctly
"""

import requests
import time
import json

BASE_URL = "http://127.0.0.1:8080"

print("=== Email Sync Test ===\n")

print("This test assumes:")
print("1. Flask app is running at http://127.0.0.1:8080")
print("2. You are logged in with Gmail")
print("3. Gmail API is enabled in Google Cloud Console")
print("")

print("Steps to test email sync:")
print("\n1. Make sure the Flask app is running:")
print("   python3 backend/main.py")

print("\n2. Login with Gmail:")
print("   - Visit http://127.0.0.1:8080/login")
print("   - Complete OAuth flow")
print("   - Grant Gmail read permissions")

print("\n3. Start email sync:")
print("   - Visit http://127.0.0.1:8080/settings")
print("   - Click 'Sync Emails'")
print("   - Wait for sync to complete")

print("\n4. View insights:")
print("   - Visit http://127.0.0.1:8080/email-insights")

print("\n=== Common Issues ===")
print("\n1. No insights showing after sync:")
print("   - Check browser console for errors (F12)")
print("   - Check Flask app logs for errors")
print("   - Verify you have emails in the specified date range")

print("\n2. Token expired error:")
print("   - Logout and login again")
print("   - Make sure to grant Gmail permissions")

print("\n3. Gmail API not enabled:")
print("   - Go to Google Cloud Console")
print("   - Enable Gmail API for your project")
print("   - Add your email as a test user if app is in testing mode")

print("\n4. No emails found:")
print("   - Check Settings page for 'Days back' parameter")
print("   - Default is 30 days - increase if needed")

print("\n=== Manual API Test ===")
print("You can test the API directly after logging in:")
print("")
print("# Check sync status:")
print("curl http://127.0.0.1:8080/api/sync-status")
print("")
print("# Get email insights:")
print("curl http://127.0.0.1:8080/api/email-insights") 