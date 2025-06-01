#!/usr/bin/env python3
"""
Debug script for Gmail OAuth issues
"""

import os
import sys
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("=== Gmail OAuth Debug Tool ===\n")

def check_token_validity(access_token):
    """Check if an access token is valid by calling Google's tokeninfo endpoint"""
    if not access_token:
        return False, "No access token provided"
    
    try:
        response = requests.get(
            f'https://oauth2.googleapis.com/tokeninfo?access_token={access_token}'
        )
        
        if response.status_code == 200:
            token_info = response.json()
            
            # Check expiry
            expires_in = token_info.get('expires_in', 0)
            if expires_in <= 0:
                return False, "Token is expired"
            
            # Check scopes
            scope = token_info.get('scope', '')
            if 'gmail.readonly' not in scope:
                return False, f"Gmail scope not found. Current scopes: {scope}"
            
            return True, f"Token valid for {expires_in} seconds. Scopes: {scope}"
        else:
            return False, f"Token validation failed: {response.status_code} - {response.text}"
    except Exception as e:
        return False, f"Error checking token: {str(e)}"

def test_gmail_api_direct(access_token):
    """Test Gmail API directly with a simple request"""
    if not access_token:
        return False, "No access token provided"
    
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(
            'https://gmail.googleapis.com/gmail/v1/users/me/profile',
            headers=headers
        )
        
        if response.status_code == 200:
            profile = response.json()
            return True, f"Connected to Gmail for: {profile.get('emailAddress', 'Unknown')}"
        else:
            return False, f"Gmail API error: {response.status_code} - {response.text}"
    except Exception as e:
        return False, f"Error calling Gmail API: {str(e)}"

def main():
    # Check if we have an access token stored somewhere
    print("1. Checking for stored access token...")
    
    # Try to read from a test file if it exists
    test_token_file = 'test_token.txt'
    access_token = None
    
    if os.path.exists(test_token_file):
        with open(test_token_file, 'r') as f:
            access_token = f.read().strip()
        print(f"   Found token in {test_token_file}")
    else:
        print(f"   No {test_token_file} found")
        print(f"   To test with a token, save it to {test_token_file}")
    
    if access_token:
        print("\n2. Validating access token...")
        valid, message = check_token_validity(access_token)
        if valid:
            print(f"   ✓ {message}")
        else:
            print(f"   ✗ {message}")
        
        print("\n3. Testing Gmail API directly...")
        success, message = test_gmail_api_direct(access_token)
        if success:
            print(f"   ✓ {message}")
        else:
            print(f"   ✗ {message}")
    
    print("\n=== OAuth Flow Debug Info ===")
    print("\n1. Google Cloud Console Checklist:")
    print("   [ ] Gmail API is enabled")
    print("   [ ] OAuth consent screen is configured")
    print("   [ ] Authorized redirect URIs include:")
    print("       - http://127.0.0.1:8080/login/google/authorized")
    print("       - http://localhost:8080/login/google/authorized")
    print("   [ ] Test users are added (if app is in testing mode)")
    
    print("\n2. Required OAuth Scopes:")
    print("   - openid")
    print("   - email")
    print("   - profile")
    print("   - https://www.googleapis.com/auth/gmail.readonly")
    
    print("\n3. Common Token Issues:")
    print("   - Token expired: Re-authenticate by logging out and in")
    print("   - Missing scopes: User didn't consent to Gmail access")
    print("   - Invalid grant: Token was revoked or is corrupted")
    
    print("\n4. Testing the Full Flow:")
    print("   a. Clear browser cookies for localhost:8080")
    print("   b. Run: python3 backend/main.py")
    print("   c. Visit: http://127.0.0.1:8080/logout (to clear session)")
    print("   d. Visit: http://127.0.0.1:8080/login")
    print("   e. Complete OAuth flow and check for Gmail consent")
    print("   f. Check browser console for errors")
    print("   g. Try syncing emails from Settings page")
    
    print("\n5. Enable Debug Logging:")
    print("   export FLASK_ENV=development")
    print("   export FLASK_DEBUG=1")
    
    print("\n6. Manual Token Test:")
    print("   After logging in, you can extract the token from the Flask session")
    print("   and save it to test_token.txt to run this debug script")

if __name__ == "__main__":
    main() 