#!/usr/bin/env python3
"""
Debug Gmail Authentication

This script provides detailed debugging for the Gmail OAuth flow by:
1. Directly testing the OAuth endpoints
2. Checking session storage
3. Verifying token handling

Usage:
    python debug_gmail_auth.py
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
import traceback

# Initialize colorama
colorama.init(autoreset=True)

# Configuration
BASE_URL = "http://localhost:8080"
AUTH_URL = f"{BASE_URL}/api/auth/gmail"
DEBUG_URL = f"{BASE_URL}/api/debug-gmail-auth"
TEST_URL = f"{BASE_URL}/api/test-gmail-direct"

def print_separator():
    print(f"{Fore.CYAN}----------------------------------------{Style.RESET_ALL}")

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

def debug_session_cookies():
    """Debug session cookies"""
    print_separator()
    print(f"{Fore.CYAN}Debugging session cookies...{Style.RESET_ALL}")
    
    # Make a request to the main page to get cookies
    try:
        session = requests.Session()
        response = session.get(BASE_URL)
        
        if response.status_code != 200:
            print(f"{Fore.RED}Failed to get session cookies: {response.status_code}{Style.RESET_ALL}")
            return
        
        # Print cookies
        if session.cookies:
            print(f"{Fore.GREEN}Session cookies found:{Style.RESET_ALL}")
            for cookie in session.cookies:
                print(f"  {cookie.name}: {cookie.value[:10]}... (expires: {cookie.expires})")
        else:
            print(f"{Fore.YELLOW}No session cookies found{Style.RESET_ALL}")
        
        # Try to access a protected endpoint
        auth_response = session.get(f"{BASE_URL}/api/debug-session")
        if auth_response.status_code == 200:
            print(f"{Fore.GREEN}✓ Successfully accessed protected endpoint{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}⚠ Failed to access protected endpoint: {auth_response.status_code}{Style.RESET_ALL}")
        
    except Exception as e:
        print(f"{Fore.RED}Error debugging session cookies: {str(e)}{Style.RESET_ALL}")

def debug_oauth_flow():
    """Debug the OAuth flow"""
    print_separator()
    print(f"{Fore.CYAN}Debugging OAuth flow...{Style.RESET_ALL}")
    
    # Make a request to the auth endpoint
    try:
        session = requests.Session()
        response = session.get(AUTH_URL, allow_redirects=False)
        
        if response.status_code == 302:
            redirect_url = response.headers.get('Location')
            print(f"{Fore.GREEN}✓ Auth endpoint redirects to Google OAuth:{Style.RESET_ALL}")
            print(f"  {redirect_url[:100]}...{Style.RESET_ALL}")
            
            # Check if state parameter is present
            if 'state=' in redirect_url:
                print(f"{Fore.GREEN}✓ State parameter is present{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}✗ State parameter is missing{Style.RESET_ALL}")
                
            # Check if redirect_uri is correct
            if 'redirect_uri=' in redirect_url:
                redirect_uri = redirect_url.split('redirect_uri=')[1].split('&')[0]
                print(f"{Fore.CYAN}Redirect URI: {redirect_uri}{Style.RESET_ALL}")
                
                # Check if it matches what's expected
                if 'localhost' in redirect_uri:
                    print(f"{Fore.GREEN}✓ Redirect URI uses localhost{Style.RESET_ALL}")
                elif '127.0.0.1' in redirect_uri:
                    print(f"{Fore.GREEN}✓ Redirect URI uses 127.0.0.1{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}✗ Redirect URI does not use localhost or 127.0.0.1{Style.RESET_ALL}")
                    
            # Check if scope is correct
            if 'scope=' in redirect_url:
                scope = redirect_url.split('scope=')[1].split('&')[0]
                print(f"{Fore.CYAN}Scope: {scope}{Style.RESET_ALL}")
                
                # Check if it includes Gmail readonly
                if 'gmail.readonly' in scope:
                    print(f"{Fore.GREEN}✓ Scope includes gmail.readonly{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}✗ Scope does not include gmail.readonly{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}✗ Auth endpoint did not redirect: {response.status_code}{Style.RESET_ALL}")
            print(f"{Fore.RED}Response: {response.text}{Style.RESET_ALL}")
        
    except Exception as e:
        print(f"{Fore.RED}Error debugging OAuth flow: {str(e)}{Style.RESET_ALL}")
        print(f"{Fore.RED}{traceback.format_exc()}{Style.RESET_ALL}")

def debug_callback_endpoint():
    """Debug the callback endpoint"""
    print_separator()
    print(f"{Fore.CYAN}Debugging callback endpoint...{Style.RESET_ALL}")
    
    # Make a request to the callback endpoint with fake parameters
    try:
        session = requests.Session()
        response = session.get(f"{BASE_URL}/login/google/authorized?code=fake_code&state=fake_state")
        
        print(f"{Fore.CYAN}Callback endpoint response code: {response.status_code}{Style.RESET_ALL}")
        
        # Check if it redirects
        if response.history:
            print(f"{Fore.GREEN}✓ Callback endpoint redirects{Style.RESET_ALL}")
            print(f"  Redirect chain: {' -> '.join([str(r.status_code) for r in response.history])}")
        else:
            print(f"{Fore.YELLOW}⚠ Callback endpoint does not redirect{Style.RESET_ALL}")
        
    except Exception as e:
        print(f"{Fore.RED}Error debugging callback endpoint: {str(e)}{Style.RESET_ALL}")

def check_environment_variables():
    """Check if required environment variables are set"""
    print_separator()
    print(f"{Fore.CYAN}Checking environment variables...{Style.RESET_ALL}")
    
    # Check if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are set
    client_id = os.environ.get('GOOGLE_CLIENT_ID')
    client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
    
    if client_id:
        print(f"{Fore.GREEN}✓ GOOGLE_CLIENT_ID is set{Style.RESET_ALL}")
        print(f"  Value: {client_id[:5]}...{client_id[-5:] if len(client_id) > 10 else ''}")
    else:
        print(f"{Fore.RED}✗ GOOGLE_CLIENT_ID is not set{Style.RESET_ALL}")
    
    if client_secret:
        print(f"{Fore.GREEN}✓ GOOGLE_CLIENT_SECRET is set{Style.RESET_ALL}")
        print(f"  Value: {client_secret[:3]}...{client_secret[-3:] if len(client_secret) > 6 else ''}")
    else:
        print(f"{Fore.RED}✗ GOOGLE_CLIENT_SECRET is not set{Style.RESET_ALL}")

def debug_gmail_auth():
    """Debug Gmail authentication issues"""
    print(f"{Fore.CYAN}========================================{Style.RESET_ALL}")
    print(f"{Fore.CYAN}  GMAIL AUTHENTICATION DEBUGGER{Style.RESET_ALL}")
    print(f"{Fore.CYAN}========================================{Style.RESET_ALL}")
    
    # Check if server is running
    if not check_server():
        return
    
    # Check current authentication status
    print_separator()
    print(f"{Fore.CYAN}Checking current authentication status...{Style.RESET_ALL}")
    is_authenticated, auth_data = check_auth_status()
    
    # Debug session cookies
    debug_session_cookies()
    
    # Debug OAuth flow
    debug_oauth_flow()
    
    # Debug callback endpoint
    debug_callback_endpoint()
    
    # Check environment variables
    check_environment_variables()
    
    # Print summary
    print_separator()
    print(f"{Fore.CYAN}AUTHENTICATION DEBUG SUMMARY{Style.RESET_ALL}")
    print(f"  Authentication Status: {Fore.GREEN + '✓ Authenticated' if is_authenticated else Fore.RED + '✗ Not Authenticated'}{Style.RESET_ALL}")
    
    if auth_data:
        print(f"{Fore.CYAN}Authentication Data:{Style.RESET_ALL}")
        print(json.dumps(auth_data, indent=2))
    
    print_separator()
    print(f"{Fore.CYAN}NEXT STEPS:{Style.RESET_ALL}")
    print(f"1. Check that GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are correctly set in .env")
    print(f"2. Verify that the redirect URI in Google Cloud Console matches exactly:")
    print(f"   http://localhost:8080/login/google/authorized")
    print(f"3. Make sure the Gmail API is enabled in Google Cloud Console")
    print(f"4. Try clearing your browser cookies and cache")
    print(f"5. Restart the Flask server and try again")
    print_separator()

if __name__ == "__main__":
    debug_gmail_auth()
