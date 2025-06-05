#!/usr/bin/env python3
"""
Fix Gmail Authentication

This script helps fix Gmail authentication issues by:
1. Checking the current session status
2. Clearing any stale session data
3. Opening the auth URL in the browser
4. Verifying the authentication was successful
5. Testing the Gmail API integration

Usage:
    python fix_gmail_auth.py
"""

import os
import sys
import json
import time
import webbrowser
import requests
import colorama
from colorama import Fore, Style
from datetime import datetime

# Initialize colorama
colorama.init(autoreset=True)

# Configuration
BASE_URL = "http://localhost:8080"
AUTH_URL = f"{BASE_URL}/api/auth/gmail"
DEBUG_URL = f"{BASE_URL}/api/debug-gmail-auth"
TEST_URL = f"{BASE_URL}/api/test-gmail-direct"
SESSION_COOKIE_FILE = "gmail_session_cookies.json"

def check_server():
    """Check if the server is running"""
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code != 200:
            print(f"{Fore.RED}Server returned status code {response.status_code}{Style.RESET_ALL}")
            print(f"{Fore.RED}Make sure the Flask server is running on port 8080{Style.RESET_ALL}")
            return False
                
        print(f"{Fore.GREEN}✓ Server is running{Style.RESET_ALL}")
        return True
            
    except requests.exceptions.ConnectionError:
        print(f"{Fore.RED}Could not connect to server at {BASE_URL}{Style.RESET_ALL}")
        print(f"{Fore.RED}Make sure the Flask server is running{Style.RESET_ALL}")
        return False

def clear_session():
    """Clear the session by visiting the logout endpoint"""
    try:
        print(f"{Fore.CYAN}Clearing session data...{Style.RESET_ALL}")
        response = requests.get(f"{BASE_URL}/logout")
        if response.status_code != 200:
            print(f"{Fore.YELLOW}⚠ Logout returned status code {response.status_code}{Style.RESET_ALL}")
            return False
        
        print(f"{Fore.GREEN}✓ Session cleared{Style.RESET_ALL}")
        return True
        
    except Exception as e:
        print(f"{Fore.RED}Error clearing session: {str(e)}{Style.RESET_ALL}")
        return False

def open_auth_page():
    """Open the Gmail authentication page in the browser"""
    print(f"{Fore.CYAN}Opening Gmail authentication page in browser...{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}IMPORTANT: Complete the authentication in the browser that opens.{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}After authenticating, return to this terminal.{Style.RESET_ALL}")
    
    webbrowser.open(AUTH_URL)
    input(f"{Fore.CYAN}Press Enter after you've completed authentication in the browser...{Style.RESET_ALL}")
    
    # Check if authentication was successful
    print(f"{Fore.CYAN}Verifying authentication...{Style.RESET_ALL}")
    
    # Try multiple times as it might take a moment for the session to be updated
    for i in range(5):
        if check_auth_status(verbose=False):
            print(f"{Fore.GREEN}✓ Authentication successful!{Style.RESET_ALL}")
            return True
        time.sleep(1)
    
    print(f"{Fore.RED}✗ Authentication failed or session not updated.{Style.RESET_ALL}")
    return False

def check_auth_status(verbose=True):
    """Check Gmail authentication status"""
    try:
        response = requests.get(DEBUG_URL)
        if response.status_code != 200:
            if verbose:
                print(f"{Fore.YELLOW}⚠ Debug endpoint returned status code {response.status_code}{Style.RESET_ALL}")
            return False
        
        data = response.json()
        authenticated = data.get('authenticated', False)
        
        if authenticated:
            token_info = data.get('token_info', {})
            token_expired = token_info.get('token_expired', True)
            
            if token_expired:
                if verbose:
                    print(f"{Fore.YELLOW}⚠ Authenticated but token has expired{Style.RESET_ALL}")
                return False
            
            if verbose:
                print(f"{Fore.GREEN}✓ Successfully authenticated with Gmail{Style.RESET_ALL}")
                print(f"{Fore.GREEN}  User: {data.get('user_email')}{Style.RESET_ALL}")
            return True
        else:
            if verbose:
                print(f"{Fore.YELLOW}⚠ Not authenticated with Gmail{Style.RESET_ALL}")
            return False
        
    except Exception as e:
        if verbose:
            print(f"{Fore.RED}Error checking authentication status: {str(e)}{Style.RESET_ALL}")
        return False

def test_gmail_api():
    """Test the Gmail API integration"""
    try:
        response = requests.post(TEST_URL, json={
            "days_back": 7,
            "max_results": 3
        })
        
        if response.status_code == 401:
            print(f"{Fore.YELLOW}⚠ Not authenticated with Gmail{Style.RESET_ALL}")
            return False
        
        if response.status_code != 200:
            print(f"{Fore.RED}Test endpoint returned status code {response.status_code}{Style.RESET_ALL}")
            print(f"{Fore.RED}Response: {response.text}{Style.RESET_ALL}")
            return False
        
        result = response.json()
        if not result.get('success', False):
            print(f"{Fore.RED}Gmail API test failed: {result.get('error', 'Unknown error')}{Style.RESET_ALL}")
            return False
        
        emails = result.get('emails', [])
        if not emails:
            print(f"{Fore.YELLOW}⚠ No emails returned from Gmail API{Style.RESET_ALL}")
            return False
        
        print(f"{Fore.GREEN}✓ Successfully tested Gmail API{Style.RESET_ALL}")
        print(f"{Fore.GREEN}  Retrieved {len(emails)} emails{Style.RESET_ALL}")
        
        # Print sample email
        if emails:
            sample = emails[0]
            print(f"\n{Fore.CYAN}Sample Email:{Style.RESET_ALL}")
            print(f"  Subject: {sample.get('subject', 'No subject')}")
            print(f"  From: {sample.get('from', {}).get('email', 'Unknown')}")
            print(f"  Date: {sample.get('date', 'Unknown')}")
        
        return True
        
    except Exception as e:
        print(f"{Fore.RED}Error testing Gmail API: {str(e)}{Style.RESET_ALL}")
        return False

def fix_gmail_auth():
    """Fix Gmail authentication issues"""
    print(f"{Fore.CYAN}========================================{Style.RESET_ALL}")
    print(f"{Fore.CYAN}  FIX GMAIL AUTHENTICATION{Style.RESET_ALL}")
    print(f"{Fore.CYAN}========================================{Style.RESET_ALL}")
    
    # Check if server is running
    if not check_server():
        return
    
    # Check current authentication status
    print(f"\n{Fore.CYAN}Checking current authentication status...{Style.RESET_ALL}")
    is_authenticated = check_auth_status()
    
    if is_authenticated:
        print(f"\n{Fore.GREEN}You are already authenticated with Gmail.{Style.RESET_ALL}")
        choice = input(f"{Fore.CYAN}Do you want to re-authenticate anyway? (y/n): {Style.RESET_ALL}")
        if choice.lower() != 'y':
            # Test Gmail API
            print(f"\n{Fore.CYAN}Testing Gmail API integration...{Style.RESET_ALL}")
            test_gmail_api()
            return
    
    # Clear any existing session
    clear_session()
    
    # Authenticate with Gmail
    print(f"\n{Fore.CYAN}Starting Gmail authentication...{Style.RESET_ALL}")
    if not open_auth_page():
        print(f"\n{Fore.RED}Failed to authenticate with Gmail.{Style.RESET_ALL}")
        print(f"{Fore.RED}Please try again manually by visiting:{Style.RESET_ALL}")
        print(f"{Fore.RED}{AUTH_URL}{Style.RESET_ALL}")
        return
    
    # Test Gmail API
    print(f"\n{Fore.CYAN}Testing Gmail API integration...{Style.RESET_ALL}")
    test_gmail_api()
    
    print(f"\n{Fore.CYAN}========================================{Style.RESET_ALL}")
    print(f"{Fore.CYAN}  AUTHENTICATION COMPLETE{Style.RESET_ALL}")
    print(f"{Fore.CYAN}========================================{Style.RESET_ALL}")

if __name__ == "__main__":
    fix_gmail_auth()
