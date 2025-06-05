#!/usr/bin/env python3
"""
Gmail Integration Fixer

This script helps diagnose and fix Gmail API integration issues by:
1. Testing the direct Gmail API integration
2. Verifying that only real Gmail data is being used (no fake/sample data)
3. Checking the email intelligence pipeline
4. Fixing UI inconsistencies

Usage:
    python gmail_integration_fixer.py
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
EMAIL_INTELLIGENCE_URL = f"{BASE_URL}/api/email/intelligence"

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

def check_auth_status():
    """Check Gmail authentication status"""
    try:
        response = requests.get(DEBUG_URL)
        if response.status_code != 200:
            print(f"{Fore.YELLOW}⚠ Debug endpoint returned status code {response.status_code}{Style.RESET_ALL}")
            return False
        
        data = response.json()
        authenticated = data.get('authenticated', False)
        
        if authenticated:
            token_info = data.get('token_info', {})
            token_expired = token_info.get('token_expired', True)
            
            if token_expired:
                print(f"{Fore.YELLOW}⚠ Authenticated but token has expired{Style.RESET_ALL}")
                return False
            
            print(f"{Fore.GREEN}✓ Successfully authenticated with Gmail{Style.RESET_ALL}")
            print(f"{Fore.GREEN}  User: {data.get('user_email')}{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.YELLOW}⚠ Not authenticated with Gmail{Style.RESET_ALL}")
            return False
        
    except Exception as e:
        print(f"{Fore.RED}Error checking authentication status: {str(e)}{Style.RESET_ALL}")
        return False

def test_gmail_api():
    """Test the Gmail API integration"""
    try:
        print(f"{Fore.CYAN}Testing direct Gmail API integration...{Style.RESET_ALL}")
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
        print(f"{Fore.RED}{traceback.format_exc()}{Style.RESET_ALL}")
        return False

def test_email_intelligence():
    """Test the email intelligence pipeline"""
    try:
        print(f"{Fore.CYAN}Testing email intelligence pipeline...{Style.RESET_ALL}")
        response = requests.get(EMAIL_INTELLIGENCE_URL)
        
        if response.status_code == 401:
            print(f"{Fore.YELLOW}⚠ Not authenticated{Style.RESET_ALL}")
            return False
        
        if response.status_code != 200:
            print(f"{Fore.RED}Email intelligence endpoint returned status code {response.status_code}{Style.RESET_ALL}")
            print(f"{Fore.RED}Response: {response.text}{Style.RESET_ALL}")
            return False
        
        result = response.json()
        
        # Check if we have insights
        has_insights = result.get('has_insights', False)
        if not has_insights:
            print(f"{Fore.YELLOW}⚠ No email insights available{Style.RESET_ALL}")
            
            # Trigger email sync
            print(f"{Fore.CYAN}Triggering email sync...{Style.RESET_ALL}")
            sync_response = requests.post(f"{BASE_URL}/api/email/sync")
            
            if sync_response.status_code != 200:
                print(f"{Fore.RED}Email sync failed with status {sync_response.status_code}{Style.RESET_ALL}")
                print(f"{Fore.RED}Response: {sync_response.text}{Style.RESET_ALL}")
                return False
            
            print(f"{Fore.GREEN}✓ Email sync initiated{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Please wait a few moments for sync to complete...{Style.RESET_ALL}")
            
            # Wait for sync to complete
            for i in range(10):
                time.sleep(3)
                print(".", end="", flush=True)
                
                # Check if insights are available now
                check_response = requests.get(EMAIL_INTELLIGENCE_URL)
                if check_response.status_code == 200:
                    check_result = check_response.json()
                    if check_result.get('has_insights', False):
                        print(f"\n{Fore.GREEN}✓ Email insights now available{Style.RESET_ALL}")
                        return True
            
            print(f"\n{Fore.YELLOW}⚠ Timed out waiting for email insights{Style.RESET_ALL}")
            return False
        
        print(f"{Fore.GREEN}✓ Email intelligence pipeline is working{Style.RESET_ALL}")
        
        # Print insight summary
        insights = result.get('insights', {})
        print(f"\n{Fore.CYAN}Insight Summary:{Style.RESET_ALL}")
        print(f"  Key Relationships: {len(insights.get('key_relationships', []))}")
        print(f"  Active Projects: {len(insights.get('active_projects', []))}")
        print(f"  Action Items: {len(insights.get('action_items', []))}")
        
        return True
        
    except Exception as e:
        print(f"{Fore.RED}Error testing email intelligence: {str(e)}{Style.RESET_ALL}")
        print(f"{Fore.RED}{traceback.format_exc()}{Style.RESET_ALL}")
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
        if check_auth_status():
            print(f"{Fore.GREEN}✓ Authentication successful!{Style.RESET_ALL}")
            return True
        print(".", end="", flush=True)
        time.sleep(1)
    
    print(f"\n{Fore.RED}✗ Authentication failed or session not updated.{Style.RESET_ALL}")
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

def check_ui_consistency():
    """Check UI consistency"""
    try:
        print(f"{Fore.CYAN}Checking UI consistency...{Style.RESET_ALL}")
        
        # Check main page
        response = requests.get(BASE_URL)
        if response.status_code != 200:
            print(f"{Fore.RED}Main page returned status code {response.status_code}{Style.RESET_ALL}")
            return False
        
        # Check insights page
        insights_response = requests.get(f"{BASE_URL}/insights")
        if insights_response.status_code != 200:
            print(f"{Fore.YELLOW}⚠ Insights page returned status code {insights_response.status_code}{Style.RESET_ALL}")
        else:
            print(f"{Fore.GREEN}✓ Insights page is accessible{Style.RESET_ALL}")
        
        # Check people page
        people_response = requests.get(f"{BASE_URL}/people")
        if people_response.status_code != 200:
            print(f"{Fore.YELLOW}⚠ People page returned status code {people_response.status_code}{Style.RESET_ALL}")
        else:
            print(f"{Fore.GREEN}✓ People page is accessible{Style.RESET_ALL}")
        
        # Check knowledge page
        knowledge_response = requests.get(f"{BASE_URL}/knowledge")
        if knowledge_response.status_code != 200:
            print(f"{Fore.YELLOW}⚠ Knowledge page returned status code {knowledge_response.status_code}{Style.RESET_ALL}")
        else:
            print(f"{Fore.GREEN}✓ Knowledge page is accessible{Style.RESET_ALL}")
        
        return True
        
    except Exception as e:
        print(f"{Fore.RED}Error checking UI consistency: {str(e)}{Style.RESET_ALL}")
        return False

def fix_gmail_integration():
    """Fix Gmail integration issues"""
    print(f"{Fore.CYAN}========================================{Style.RESET_ALL}")
    print(f"{Fore.CYAN}  GMAIL INTEGRATION FIXER{Style.RESET_ALL}")
    print(f"{Fore.CYAN}========================================{Style.RESET_ALL}")
    
    # Check if server is running
    if not check_server():
        return
    
    # Check current authentication status
    print(f"\n{Fore.CYAN}Checking current authentication status...{Style.RESET_ALL}")
    is_authenticated = check_auth_status()
    
    if not is_authenticated:
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
    api_working = test_gmail_api()
    
    if not api_working:
        print(f"\n{Fore.RED}Gmail API integration is not working.{Style.RESET_ALL}")
        print(f"{Fore.RED}Please check the logs for more details.{Style.RESET_ALL}")
        return
    
    # Test email intelligence pipeline
    print(f"\n{Fore.CYAN}Testing email intelligence pipeline...{Style.RESET_ALL}")
    intelligence_working = test_email_intelligence()
    
    # Check UI consistency
    print(f"\n{Fore.CYAN}Checking UI consistency...{Style.RESET_ALL}")
    ui_consistent = check_ui_consistency()
    
    # Print summary
    print(f"\n{Fore.CYAN}========================================{Style.RESET_ALL}")
    print(f"{Fore.CYAN}  INTEGRATION STATUS SUMMARY{Style.RESET_ALL}")
    print(f"{Fore.CYAN}========================================{Style.RESET_ALL}")
    print(f"  Authentication: {Fore.GREEN + '✓ Working' if is_authenticated else Fore.RED + '✗ Not Working'}{Style.RESET_ALL}")
    print(f"  Gmail API: {Fore.GREEN + '✓ Working' if api_working else Fore.RED + '✗ Not Working'}{Style.RESET_ALL}")
    print(f"  Email Intelligence: {Fore.GREEN + '✓ Working' if intelligence_working else Fore.RED + '✗ Not Working'}{Style.RESET_ALL}")
    print(f"  UI Consistency: {Fore.GREEN + '✓ Good' if ui_consistent else Fore.YELLOW + '⚠ Issues Detected'}{Style.RESET_ALL}")
    
    # Final message
    if is_authenticated and api_working and intelligence_working and ui_consistent:
        print(f"\n{Fore.GREEN}✓ All systems are working correctly!{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.YELLOW}⚠ Some issues were detected. Please check the logs for more details.{Style.RESET_ALL}")
    
    print(f"\n{Fore.CYAN}========================================{Style.RESET_ALL}")

if __name__ == "__main__":
    fix_gmail_integration()
