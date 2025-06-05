#!/usr/bin/env python3
"""
Setup Gmail OAuth Environment

This script helps set up the Gmail OAuth environment by:
1. Checking for existing .env file
2. Prompting for Google OAuth credentials if needed
3. Updating the .env file with the credentials
4. Testing the OAuth setup

Usage:
    python setup_gmail_oauth.py
"""

import os
import sys
import colorama
from colorama import Fore, Style
from dotenv import load_dotenv, find_dotenv

# Initialize colorama
colorama.init(autoreset=True)

def print_separator():
    print(f"{Fore.CYAN}----------------------------------------{Style.RESET_ALL}")

def check_env_file():
    """Check if .env file exists and contains required variables"""
    print(f"{Fore.CYAN}Checking for .env file...{Style.RESET_ALL}")
    
    # Try to find .env file
    env_file = find_dotenv()
    if not env_file:
        print(f"{Fore.YELLOW}⚠ No .env file found{Style.RESET_ALL}")
        return False, None
    
    print(f"{Fore.GREEN}✓ Found .env file at: {env_file}{Style.RESET_ALL}")
    
    # Load environment variables
    load_dotenv(env_file)
    
    # Check for required variables
    client_id = os.environ.get('GOOGLE_CLIENT_ID')
    client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
    
    if client_id and client_secret:
        print(f"{Fore.GREEN}✓ Found Google OAuth credentials in .env file{Style.RESET_ALL}")
        return True, env_file
    else:
        missing = []
        if not client_id:
            missing.append('GOOGLE_CLIENT_ID')
        if not client_secret:
            missing.append('GOOGLE_CLIENT_SECRET')
        
        print(f"{Fore.YELLOW}⚠ Missing required variables in .env file: {', '.join(missing)}{Style.RESET_ALL}")
        return False, env_file

def update_env_file(env_file):
    """Update .env file with Google OAuth credentials"""
    print_separator()
    print(f"{Fore.CYAN}Updating .env file with Google OAuth credentials...{Style.RESET_ALL}")
    
    # If no .env file exists, create one
    if not env_file:
        env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
        print(f"{Fore.YELLOW}Creating new .env file at: {env_file}{Style.RESET_ALL}")
    
    # Prompt for credentials
    print(f"{Fore.YELLOW}Please enter your Google OAuth credentials:{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}(These can be obtained from the Google Cloud Console){Style.RESET_ALL}")
    
    client_id = input(f"{Fore.CYAN}Google Client ID: {Style.RESET_ALL}")
    client_secret = input(f"{Fore.CYAN}Google Client Secret: {Style.RESET_ALL}")
    
    if not client_id or not client_secret:
        print(f"{Fore.RED}✗ Invalid credentials. Both Client ID and Client Secret are required.{Style.RESET_ALL}")
        return False
    
    # Read existing .env file content
    env_content = ""
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            env_content = f.read()
    
    # Update or add GOOGLE_CLIENT_ID
    if 'GOOGLE_CLIENT_ID=' in env_content:
        env_content = env_content.replace(
            'GOOGLE_CLIENT_ID=' + os.environ.get('GOOGLE_CLIENT_ID', ''),
            'GOOGLE_CLIENT_ID=' + client_id
        )
    else:
        env_content += f"\nGOOGLE_CLIENT_ID={client_id}"
    
    # Update or add GOOGLE_CLIENT_SECRET
    if 'GOOGLE_CLIENT_SECRET=' in env_content:
        env_content = env_content.replace(
            'GOOGLE_CLIENT_SECRET=' + os.environ.get('GOOGLE_CLIENT_SECRET', ''),
            'GOOGLE_CLIENT_SECRET=' + client_secret
        )
    else:
        env_content += f"\nGOOGLE_CLIENT_SECRET={client_secret}"
    
    # Write updated content back to .env file
    with open(env_file, 'w') as f:
        f.write(env_content.strip() + "\n")
    
    print(f"{Fore.GREEN}✓ Updated .env file with Google OAuth credentials{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}⚠ You need to restart the Flask server for these changes to take effect{Style.RESET_ALL}")
    
    return True

def setup_oauth():
    """Set up the Gmail OAuth environment"""
    print(f"{Fore.CYAN}========================================{Style.RESET_ALL}")
    print(f"{Fore.CYAN}  GMAIL OAUTH SETUP{Style.RESET_ALL}")
    print(f"{Fore.CYAN}========================================{Style.RESET_ALL}")
    
    # Check for existing .env file
    has_credentials, env_file = check_env_file()
    
    if not has_credentials:
        # Update .env file with credentials
        if not update_env_file(env_file):
            print(f"{Fore.RED}✗ Failed to update .env file{Style.RESET_ALL}")
            return
    
    print_separator()
    print(f"{Fore.CYAN}NEXT STEPS:{Style.RESET_ALL}")
    print(f"1. Make sure your Google Cloud Console project has the Gmail API enabled")
    print(f"2. Verify that the redirect URI in Google Cloud Console matches exactly:")
    print(f"   http://localhost:8080/login/google/authorized")
    print(f"3. Restart the Flask server with:")
    print(f"   python -m flask run --host=localhost --port=8080")
    print(f"4. Run the debug script to verify the setup:")
    print(f"   python debug_gmail_auth.py")
    print_separator()
    
    # Ask if user wants to restart the server
    restart = input(f"{Fore.CYAN}Do you want to restart the Flask server now? (y/n): {Style.RESET_ALL}")
    if restart.lower() == 'y':
        print(f"{Fore.YELLOW}Restarting Flask server...{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}(This will terminate the current process){Style.RESET_ALL}")
        
        # Execute the restart command
        os.system("pkill -f 'python -m flask run' && python -m flask run --host=localhost --port=8080")
    else:
        print(f"{Fore.YELLOW}Please restart the Flask server manually for the changes to take effect.{Style.RESET_ALL}")

if __name__ == "__main__":
    setup_oauth()
