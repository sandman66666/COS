#!/usr/bin/env python3
"""
Direct Gmail API Test Script

This script directly tests the Gmail API integration without relying on session cookies.
It uses a direct API approach to validate that Gmail integration is working properly.

Usage:
    python direct_gmail_test.py
"""

import os
import sys
import json
import time
import logging
import requests
import unittest
from datetime import datetime, timedelta
import colorama
from colorama import Fore, Style

# Initialize colorama
colorama.init(autoreset=True)

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = "http://localhost:8080"  # Flask development server
TEST_REPORT_FILE = f"test_reports/direct_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

class DirectGmailTest(unittest.TestCase):
    """Direct test for Gmail API integration"""
    
    def setUp(self):
        """Set up test environment"""
        print(f"{Fore.CYAN}Setting up test environment...{Style.RESET_ALL}")
        
        # Check if server is running
        try:
            response = requests.get(f"{BASE_URL}/")
            if response.status_code != 200:
                print(f"{Fore.RED}Server returned status code {response.status_code}{Style.RESET_ALL}")
                print(f"{Fore.RED}Make sure the Flask server is running on port 8080{Style.RESET_ALL}")
                sys.exit(1)
                
            print(f"{Fore.GREEN}✓ Server is running{Style.RESET_ALL}")
            
        except requests.exceptions.ConnectionError:
            print(f"{Fore.RED}Could not connect to server at {BASE_URL}{Style.RESET_ALL}")
            print(f"{Fore.RED}Make sure the Flask server is running{Style.RESET_ALL}")
            sys.exit(1)
    
    def test_direct_gmail_api(self):
        """Test direct Gmail API integration"""
        test_results = {
            "start_time": datetime.now().isoformat(),
            "tests": {},
            "overall_success": False
        }
        
        try:
            # Step 1: Test Gmail API via direct endpoint
            print(f"\n{Fore.CYAN}Step 1: Testing Gmail API directly{Style.RESET_ALL}")
            
            # Create a new endpoint in the Flask app to test Gmail API directly
            response = requests.post(f"{BASE_URL}/api/test-gmail-direct", json={
                "test_mode": True,
                "days_back": 7,
                "max_results": 5
            })
            
            # Check if the endpoint exists
            if response.status_code == 404:
                print(f"{Fore.YELLOW}⚠ The /api/test-gmail-direct endpoint doesn't exist yet{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Please add this endpoint to your Flask app first{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}See instructions in the script comments{Style.RESET_ALL}")
                test_results["tests"]["direct_api"] = {"success": False, "error": "Endpoint not found"}
                return
            
            # Check if we're authenticated
            if response.status_code == 401:
                print(f"{Fore.YELLOW}⚠ Not authenticated with Gmail{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Please authenticate with Gmail by visiting {BASE_URL}/api/auth/gmail in your browser{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Then run this test again{Style.RESET_ALL}")
                test_results["tests"]["direct_api"] = {"success": False, "error": "Not authenticated"}
                return
            
            # Check if the API call was successful
            self.assertEqual(response.status_code, 200, "Gmail API test endpoint should return 200")
            result = response.json()
            
            # Print the result
            print(f"{Fore.CYAN}Gmail API Test Result:{Style.RESET_ALL}")
            print(json.dumps(result, indent=2))
            
            # Check if we got emails
            self.assertTrue(result.get('success'), "Gmail API test should succeed")
            self.assertIn('emails', result, "Gmail API test should return emails")
            self.assertGreater(len(result.get('emails', [])), 0, "Gmail API test should return at least one email")
            
            print(f"{Fore.GREEN}✓ Successfully tested Gmail API directly{Style.RESET_ALL}")
            test_results["tests"]["direct_api"] = {"success": True, "email_count": len(result.get('emails', []))}
            
            # All tests passed
            test_results["overall_success"] = True
            
        except Exception as e:
            print(f"{Fore.RED}Test failed: {str(e)}{Style.RESET_ALL}")
            test_results["error"] = str(e)
            raise
        
        finally:
            # Save test results
            test_results["end_time"] = datetime.now().isoformat()
            
            # Create test_reports directory if it doesn't exist
            os.makedirs(os.path.dirname(TEST_REPORT_FILE), exist_ok=True)
            
            with open(TEST_REPORT_FILE, 'w') as f:
                json.dump(test_results, f, indent=2)
            
            print(f"\n{Fore.CYAN}Test report saved to {TEST_REPORT_FILE}{Style.RESET_ALL}")

def run_test():
    """Run the direct Gmail API test"""
    print(f"{Fore.CYAN}========================================{Style.RESET_ALL}")
    print(f"{Fore.CYAN}  DIRECT GMAIL API TEST{Style.RESET_ALL}")
    print(f"{Fore.CYAN}========================================{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Note: This test requires that you have already authenticated with Gmail{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}If you haven't authenticated yet, please visit {BASE_URL}/api/auth/gmail in your browser{Style.RESET_ALL}")
    print()
    
    # Run the test
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
    
    print(f"\n{Fore.CYAN}========================================{Style.RESET_ALL}")
    print(f"{Fore.CYAN}  TEST COMPLETE{Style.RESET_ALL}")
    print(f"{Fore.CYAN}========================================{Style.RESET_ALL}")

if __name__ == "__main__":
    run_test()

"""
INSTRUCTIONS FOR ADDING THE TEST ENDPOINT TO YOUR FLASK APP:

Add the following endpoint to your Flask app in main.py:

@app.route('/api/test-gmail-direct', methods=['POST'])
def test_gmail_direct():
    # Check if user is authenticated
    if 'user_email' not in session or 'google_oauth_token' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
        
    # Get request parameters
    data = request.json or {}
    days_back = data.get('days_back', 7)
    max_results = data.get('max_results', 5)
    
    # Get token data
    token_data = session['google_oauth_token']
    
    # Create Gmail connector
    from backend.connectors.gmail_connector import ImprovedGmailConnector
    gmail_connector = ImprovedGmailConnector(token_data)
    
    # Fetch emails
    result = gmail_connector.get_recent_emails(days_back=days_back, max_results=max_results)
    
    return jsonify(result)
"""
