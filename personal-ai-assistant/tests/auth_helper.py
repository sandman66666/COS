#!/usr/bin/env python3
"""
Gmail Authentication Helper

This script helps you authenticate with Gmail before running the complete_gmail_test.py script.
It creates a browser session, authenticates with Gmail, and saves the session cookies
to a file that can be used by the test script.

Usage:
    python auth_helper.py
"""

import os
import sys
import json
import time
import requests
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# Configuration
BASE_URL = "http://localhost:8080"
AUTH_URL = f"{BASE_URL}/api/auth/gmail"
COOKIE_FILE = "gmail_test_cookies.json"

def check_server():
    """Check if the Flask server is running"""
    try:
        response = requests.get(f"{BASE_URL}/")
        return response.status_code == 200
    except:
        return False

def check_auth_status():
    """Check if we're already authenticated with Gmail"""
    session = requests.Session()
    
    # Load cookies if they exist
    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE, 'r') as f:
            cookies = requests.utils.cookiejar_from_dict(json.load(f))
            session.cookies = cookies
    
    # Check authentication status
    response = session.get(f"{BASE_URL}/api/debug-gmail")
    return response.status_code == 200

def save_session_cookies(session):
    """Save session cookies to file"""
    cookies = requests.utils.dict_from_cookiejar(session.cookies)
    with open(COOKIE_FILE, 'w') as f:
        json.dump(cookies, f)
    print(f"Session cookies saved to {COOKIE_FILE}")

def authenticate():
    """Authenticate with Gmail and save the session cookies"""
    print("Starting authentication process...")
    
    # Open browser to authentication URL
    print(f"Opening {AUTH_URL} in your default browser...")
    webbrowser.open(AUTH_URL)
    
    # Wait for user to complete authentication
    print("\nPlease complete the authentication process in your browser.")
    print("After you've authenticated, this script will detect your session.")
    
    # Poll for authentication status
    max_attempts = 30
    for attempt in range(max_attempts):
        print(f"Checking authentication status... ({attempt+1}/{max_attempts})")
        if check_auth_status():
            print("\n✅ Successfully authenticated with Gmail!")
            print(f"You can now run the test script: python complete_gmail_test.py")
            return True
        time.sleep(5)
    
    print("\n❌ Authentication timed out.")
    print("Please try running this script again.")
    return False

def main():
    """Main function"""
    print("Gmail Authentication Helper")
    print("==========================")
    
    # Check if server is running
    if not check_server():
        print("❌ Flask server is not running.")
        print(f"Please start the server and make sure it's accessible at {BASE_URL}")
        return
    
    # Check if already authenticated
    if check_auth_status():
        print("✅ Already authenticated with Gmail.")
        print("You can run the test script: python complete_gmail_test.py")
        return
    
    # Not authenticated, start authentication process
    authenticate()

if __name__ == "__main__":
    main()
