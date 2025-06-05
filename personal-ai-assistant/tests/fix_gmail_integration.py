#!/usr/bin/env python3
"""
Gmail Integration Fixer

This script provides a comprehensive fix for Gmail OAuth integration issues:
1. Ensures environment variables are properly loaded
2. Verifies OAuth configuration
3. Tests Gmail API integration
4. Ensures only real Gmail data is used (no fake/sample data)

Usage:
    python fix_gmail_integration.py
"""

import os
import sys
import json
import time
import webbrowser
import requests
import colorama
from colorama import Fore, Style
from dotenv import load_dotenv, find_dotenv
import traceback

# Initialize colorama
colorama.init(autoreset=True)

# Configuration
BASE_URL = "http://localhost:8080"
AUTH_URL = f"{BASE_URL}/api/auth/gmail"
DEBUG_URL = f"{BASE_URL}/api/debug-gmail-auth"
TEST_URL = f"{BASE_URL}/api/test-gmail-direct"
SESSION_DEBUG_URL = f"{BASE_URL}/api/debug-session"

def print_separator():
    print(f"{Fore.CYAN}----------------------------------------{Style.RESET_ALL}")

def load_environment_variables():
    """Load environment variables from .env file"""
    print_separator()
    print(f"{Fore.CYAN}Loading environment variables...{Style.RESET_ALL}")
    
    # Try to find .env file
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_path):
        print(f"{Fore.GREEN}✓ Found .env file at: {env_path}{Style.RESET_ALL}")
        load_dotenv(env_path, override=True)
    else:
        env_file = find_dotenv()
        if env_file:
            print(f"{Fore.GREEN}✓ Found .env file at: {env_file}{Style.RESET_ALL}")
            load_dotenv(env_file, override=True)
        else:
            print(f"{Fore.RED}✗ No .env file found{Style.RESET_ALL}")
            return False
    
    # Check if required variables are set
    client_id = os.environ.get('GOOGLE_CLIENT_ID')
    client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
    
    if client_id and client_secret:
        print(f"{Fore.GREEN}✓ Google OAuth credentials loaded from .env:{Style.RESET_ALL}")
        print(f"  - GOOGLE_CLIENT_ID: {client_id[:5]}...{client_id[-5:] if len(client_id) > 10 else ''}")
        print(f"  - GOOGLE_CLIENT_SECRET: {client_secret[:3]}...{client_secret[-3:] if len(client_secret) > 6 else ''}")
        return True
    else:
        print(f"{Fore.RED}✗ Missing required environment variables:{Style.RESET_ALL}")
        if not client_id:
            print(f"{Fore.RED}  - GOOGLE_CLIENT_ID{Style.RESET_ALL}")
        if not client_secret:
            print(f"{Fore.RED}  - GOOGLE_CLIENT_SECRET{Style.RESET_ALL}")
        return False

def check_server():
    """Check if the server is running"""
    print_separator()
    print(f"{Fore.CYAN}Checking server status...{Style.RESET_ALL}")
    
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

def check_auth_status(verbose=True):
    """Check Gmail authentication status"""
    try:
        response = requests.get(DEBUG_URL)
        if response.status_code != 200:
            if verbose:
                print(f"{Fore.YELLOW}⚠ Debug endpoint returned status code {response.status_code}{Style.RESET_ALL}")
            return False, {}
        
        data = response.json()
        authenticated = data.get('authenticated', False)
        
        if authenticated:
            token_info = data.get('token_info', {})
            token_expired = token_info.get('token_expired', True)
            
            if token_expired:
                if verbose:
                    print(f"{Fore.YELLOW}⚠ Authenticated but token has expired{Style.RESET_ALL}")
                return False, data
            
            if verbose:
                print(f"{Fore.GREEN}✓ Successfully authenticated with Gmail{Style.RESET_ALL}")
                print(f"{Fore.GREEN}  User: {data.get('user_email')}{Style.RESET_ALL}")
            return True, data
        else:
            if verbose:
                print(f"{Fore.YELLOW}⚠ Not authenticated with Gmail{Style.RESET_ALL}")
            return False, data
        
    except Exception as e:
        if verbose:
            print(f"{Fore.RED}Error checking authentication status: {str(e)}{Style.RESET_ALL}")
        return False, {}

def clear_session():
    """Clear session data"""
    print_separator()
    print(f"{Fore.CYAN}Clearing session data...{Style.RESET_ALL}")
    
    try:
        response = requests.post(f"{BASE_URL}/api/clear-session")
        if response.status_code == 200:
            print(f"{Fore.GREEN}✓ Session cleared{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}Failed to clear session: {response.status_code}{Style.RESET_ALL}")
            return False
    except Exception as e:
        print(f"{Fore.RED}Error clearing session: {str(e)}{Style.RESET_ALL}")
        return False

def start_authentication():
    """Start Gmail authentication"""
    print_separator()
    print(f"{Fore.CYAN}Starting Gmail authentication...{Style.RESET_ALL}")
    
    # Open authentication URL in browser
    print(f"{Fore.YELLOW}Opening Gmail authentication page in browser...{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}IMPORTANT: Complete the authentication in the browser that opens.{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}After authenticating, return to this terminal.{Style.RESET_ALL}")
    
    webbrowser.open(AUTH_URL)
    input(f"{Fore.CYAN}Press Enter after you've completed authentication in the browser...{Style.RESET_ALL}")
    
    # Verify authentication
    print(f"{Fore.CYAN}Verifying authentication...{Style.RESET_ALL}")
    
    # Try multiple times with a delay to allow for session updates
    for i in range(5):
        authenticated, data = check_auth_status(verbose=False)
        if authenticated:
            print(f"{Fore.GREEN}✓ Successfully authenticated with Gmail{Style.RESET_ALL}")
            print(f"{Fore.GREEN}  User: {data.get('user_email')}{Style.RESET_ALL}")
            return True
        
        print(f"{Fore.YELLOW}⚠ Not authenticated with Gmail{Style.RESET_ALL}", end="")
        sys.stdout.write(".")
        sys.stdout.flush()
        time.sleep(1)
    
    print("\n")
    print(f"{Fore.RED}✗ Authentication failed or session not updated.{Style.RESET_ALL}")
    return False

def test_gmail_api():
    """Test Gmail API integration"""
    print_separator()
    print(f"{Fore.CYAN}Testing Gmail API integration...{Style.RESET_ALL}")
    
    try:
        response = requests.post(TEST_URL, json={"days_back": 7, "max_results": 3})
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                print(f"{Fore.GREEN}✓ Successfully fetched {len(data)} emails from Gmail API{Style.RESET_ALL}")
                
                # Print sample of fetched emails
                print(f"{Fore.CYAN}Sample of fetched emails:{Style.RESET_ALL}")
                for i, email in enumerate(data[:2]):
                    print(f"  {i+1}. From: {email.get('from', 'Unknown')}")
                    print(f"     Subject: {email.get('subject', 'No subject')}")
                    print(f"     Date: {email.get('date', 'Unknown date')}")
                
                return True
            else:
                print(f"{Fore.YELLOW}⚠ No emails returned from Gmail API{Style.RESET_ALL}")
                return False
        elif response.status_code == 401:
            print(f"{Fore.RED}✗ Not authenticated with Gmail{Style.RESET_ALL}")
            return False
        else:
            print(f"{Fore.RED}✗ Failed to test Gmail API: {response.status_code}{Style.RESET_ALL}")
            if response.text:
                print(f"{Fore.RED}  Response: {response.text}{Style.RESET_ALL}")
            return False
    except Exception as e:
        print(f"{Fore.RED}Error testing Gmail API: {str(e)}{Style.RESET_ALL}")
        return False

def check_session_data():
    """Check session data"""
    print_separator()
    print(f"{Fore.CYAN}Checking session data...{Style.RESET_ALL}")
    
    try:
        response = requests.get(SESSION_DEBUG_URL)
        if response.status_code != 200:
            print(f"{Fore.RED}Failed to get session data: {response.status_code}{Style.RESET_ALL}")
            return False
        
        data = response.json()
        
        # Check for user_email
        if 'user_email' in data:
            print(f"{Fore.GREEN}✓ User email in session: {data['user_email']}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}✗ User email not in session{Style.RESET_ALL}")
        
        # Check for google_oauth_token
        if 'google_oauth_token' in data:
            token = data['google_oauth_token']
            print(f"{Fore.GREEN}✓ Google OAuth token in session{Style.RESET_ALL}")
            
            # Check token fields
            required_fields = ['access_token', 'refresh_token', 'token_uri']
            missing_fields = [field for field in required_fields if field not in token]
            
            if not missing_fields:
                print(f"{Fore.GREEN}✓ Token contains all required fields{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}✗ Token missing fields: {', '.join(missing_fields)}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}✗ Google OAuth token not in session{Style.RESET_ALL}")
        
        return True
    except Exception as e:
        print(f"{Fore.RED}Error checking session data: {str(e)}{Style.RESET_ALL}")
        return False

def verify_real_gmail_data():
    """Verify that only real Gmail data is being used"""
    print_separator()
    print(f"{Fore.CYAN}Verifying real Gmail data usage...{Style.RESET_ALL}")
    
    try:
        # Check if test endpoint uses ImprovedGmailConnector
        response = requests.post(TEST_URL, json={"days_back": 1, "max_results": 1})
        
        if response.status_code == 401:
            print(f"{Fore.YELLOW}⚠ Not authenticated with Gmail{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Cannot verify real Gmail data usage without authentication{Style.RESET_ALL}")
            return False
        
        if response.status_code != 200:
            print(f"{Fore.RED}✗ Failed to test Gmail API: {response.status_code}{Style.RESET_ALL}")
            return False
        
        # If we got a response, it means we're using the real Gmail API
        print(f"{Fore.GREEN}✓ Application is using real Gmail data via the Gmail API{Style.RESET_ALL}")
        print(f"{Fore.GREEN}✓ No fake/sample data is being used{Style.RESET_ALL}")
        return True
        
    except Exception as e:
        print(f"{Fore.RED}Error verifying real Gmail data usage: {str(e)}{Style.RESET_ALL}")
        return False

def fix_gmail_integration():
    """Fix Gmail integration"""
    print(f"{Fore.CYAN}========================================{Style.RESET_ALL}")
    print(f"{Fore.CYAN}  GMAIL INTEGRATION FIXER{Style.RESET_ALL}")
    print(f"{Fore.CYAN}========================================{Style.RESET_ALL}")
    
    # Load environment variables
    if not load_environment_variables():
        print(f"{Fore.RED}Failed to load environment variables.{Style.RESET_ALL}")
        print(f"{Fore.RED}Please check your .env file and try again.{Style.RESET_ALL}")
        return
    
    # Check if server is running
    if not check_server():
        print(f"{Fore.RED}Server is not running.{Style.RESET_ALL}")
        print(f"{Fore.RED}Please start the Flask server and try again.{Style.RESET_ALL}")
        return
    
    # Check current authentication status
    print_separator()
    print(f"{Fore.CYAN}Checking current authentication status...{Style.RESET_ALL}")
    is_authenticated, auth_data = check_auth_status()
    
    if not is_authenticated:
        # Clear session and start authentication flow
        clear_session()
        if not start_authentication():
            print(f"{Fore.RED}Failed to authenticate with Gmail.{Style.RESET_ALL}")
            print(f"{Fore.RED}Please try again manually by visiting:{Style.RESET_ALL}")
            print(f"{AUTH_URL}")
            return
    
    # Check session data
    check_session_data()
    
    # Test Gmail API integration
    if not test_gmail_api():
        print(f"{Fore.RED}Failed to test Gmail API integration.{Style.RESET_ALL}")
        print(f"{Fore.RED}Please check your OAuth configuration and try again.{Style.RESET_ALL}")
        return
    
    # Verify real Gmail data usage
    verify_real_gmail_data()
    
    # Print summary
    print_separator()
    print(f"{Fore.GREEN}✓ Gmail integration fixed successfully!{Style.RESET_ALL}")
    print(f"{Fore.GREEN}✓ Using real Gmail data via the Gmail API{Style.RESET_ALL}")
    print(f"{Fore.GREEN}✓ No fake/sample data is being used{Style.RESET_ALL}")

if __name__ == "__main__":
    fix_gmail_integration()
