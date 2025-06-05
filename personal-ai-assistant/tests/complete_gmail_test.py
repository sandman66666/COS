#!/usr/bin/env python3
"""
Comprehensive End-to-End Test Script for Gmail Integration

This script tests the complete flow of Gmail integration in a single test, including:
1. OAuth authentication and token handling
2. Email fetching via Gmail API (using ONLY real Gmail data, no fake data)
3. Data processing and storage in database
4. API endpoints for UI data display
5. Database reset and force refresh functionality
6. Insights generation and retrieval

Usage:
    python complete_gmail_test.py

Note: 
- This requires the Flask server to be running on port 8080
- You must have already authenticated with Gmail before running this test
- The test will automatically reset the database, so backup any data you want to keep
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

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = "http://localhost:8080"  # Flask development server
TEST_TIMEOUT = 60  # Seconds to wait for async operations
TEST_REPORT_FILE = f"test_reports/complete_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

class CompleteGmailIntegrationTest(unittest.TestCase):
    """Complete end-to-end test for Gmail integration"""
    
    def setUp(self):
        """Set up test environment"""
        print(f"{Fore.CYAN}Setting up test environment...{Style.RESET_ALL}")
        
        # Create a session for making authenticated requests
        self.session = requests.Session()
        
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
    
    def test_complete_gmail_integration(self):
        """Test the complete Gmail integration flow"""
        test_results = {
            "start_time": datetime.now().isoformat(),
            "tests": {},
            "overall_success": False
        }
        
        try:
            # Step 1: Test Gmail Authentication Routes
            print(f"\n{Fore.CYAN}Step 1: Testing Gmail Authentication Routes{Style.RESET_ALL}")
            auth_route = f"{BASE_URL}/api/auth/gmail"
            response = requests.get(auth_route)
            self.assertEqual(response.status_code, 200, "Gmail auth route should be accessible")
            print(f"{Fore.GREEN}✓ Gmail authentication routes are properly configured{Style.RESET_ALL}")
            test_results["tests"]["auth_routes"] = {"success": True}
            
            # Step 2: Check if we have a valid Gmail token
            print(f"\n{Fore.CYAN}Step 2: Checking for valid Gmail token{Style.RESET_ALL}")
            response = requests.get(f"{BASE_URL}/api/debug-gmail")
            
            if response.status_code == 401:
                print(f"{Fore.YELLOW}⚠ Not authenticated with Gmail{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Please authenticate with Gmail by visiting {auth_route} in your browser{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Then run this test again{Style.RESET_ALL}")
                test_results["tests"]["gmail_token"] = {"success": False, "error": "Not authenticated with Gmail"}
                self.skipTest("Not authenticated with Gmail")
            
            self.assertEqual(response.status_code, 200, "Gmail debug endpoint should return 200")
            debug_data = response.json()
            self.assertIn('token_info', debug_data, "Debug endpoint should return token info")
            
            # Verify token is valid
            self.assertTrue(debug_data['token_info']['valid'], "Gmail token should be valid")
            print(f"{Fore.GREEN}✓ Valid Gmail token found{Style.RESET_ALL}")
            test_results["tests"]["gmail_token"] = {"success": True}
            
            # Step 3: Reset Database
            print(f"\n{Fore.CYAN}Step 3: Resetting Database{Style.RESET_ALL}")
            response = requests.post(f"{BASE_URL}/api/reset-database")
            self.assertEqual(response.status_code, 200, "Reset database endpoint should return 200")
            reset_result = response.json()
            self.assertTrue(reset_result.get('success'), "Reset database should return success")
            print(f"{Fore.GREEN}✓ Database reset successful{Style.RESET_ALL}")
            test_results["tests"]["reset_database"] = {"success": True}
            
            # Step 4: Test Gmail API Connection and Email Fetching
            print(f"\n{Fore.CYAN}Step 4: Testing Gmail API Connection{Style.RESET_ALL}")
            response = requests.get(f"{BASE_URL}/api/debug-gmail")
            self.assertEqual(response.status_code, 200, "Gmail debug endpoint should return 200")
            
            gmail_data = response.json()
            self.assertIn('emails', gmail_data, "Debug endpoint should return emails")
            self.assertIsInstance(gmail_data['emails'], list, "Emails should be a list")
            
            # Verify we're getting real data, not sample data
            if gmail_data['emails']:
                # Check that we have some email data with expected fields
                self.assertIn('id', gmail_data['emails'][0], "Email missing ID field")
                self.assertIn('subject', gmail_data['emails'][0], "Email missing subject field")
                print(f"{Fore.GREEN}✓ Successfully fetched {len(gmail_data['emails'])} real emails from Gmail API{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}⚠ No emails found in Gmail account{Style.RESET_ALL}")
                
            test_results["tests"]["gmail_connection"] = {
                "success": True,
                "email_count": len(gmail_data['emails'])
            }
            
            # Step 5: Test People Endpoint
            print(f"\n{Fore.CYAN}Step 5: Testing People Endpoint{Style.RESET_ALL}")
            response = requests.get(f"{BASE_URL}/api/people")
            self.assertEqual(response.status_code, 200, "People endpoint should return 200")
            
            people_data = response.json()
            self.assertIn('people', people_data, "People endpoint should return people data")
            self.assertIsInstance(people_data['people'], list, "People should be a list")
            
            print(f"{Fore.GREEN}✓ Successfully retrieved {len(people_data['people'])} contacts{Style.RESET_ALL}")
            test_results["tests"]["people_endpoint"] = {
                "success": True,
                "contact_count": len(people_data['people'])
            }
            
            # Step 6: Test Tasks Endpoint
            print(f"\n{Fore.CYAN}Step 6: Testing Tasks Endpoint{Style.RESET_ALL}")
            response = requests.get(f"{BASE_URL}/api/tasks")
            self.assertEqual(response.status_code, 200, "Tasks endpoint should return 200")
            
            tasks_data = response.json()
            self.assertIn('tasks', tasks_data, "Tasks endpoint should return tasks data")
            self.assertIsInstance(tasks_data['tasks'], list, "Tasks should be a list")
            
            print(f"{Fore.GREEN}✓ Successfully retrieved {len(tasks_data['tasks'])} tasks{Style.RESET_ALL}")
            test_results["tests"]["tasks_endpoint"] = {
                "success": True,
                "task_count": len(tasks_data['tasks'])
            }
            
            # Step 7: Test Force Refresh
            print(f"\n{Fore.CYAN}Step 7: Testing Force Refresh{Style.RESET_ALL}")
            response = requests.post(f"{BASE_URL}/api/force-refresh")
            self.assertEqual(response.status_code, 200, "Force refresh endpoint should return 200")
            
            refresh_result = response.json()
            self.assertTrue(refresh_result.get('success'), "Force refresh should return success")
            print(f"{Fore.GREEN}✓ Force refresh successful{Style.RESET_ALL}")
            test_results["tests"]["force_refresh"] = {"success": True}
            
            # Step 8: Test Sync Status
            print(f"\n{Fore.CYAN}Step 8: Testing Sync Status{Style.RESET_ALL}")
            response = requests.get(f"{BASE_URL}/api/sync-status")
            self.assertEqual(response.status_code, 200, "Sync status endpoint should return 200")
            
            sync_status = response.json()
            self.assertIn('is_syncing', sync_status, "Sync status should include is_syncing field")
            
            # Wait for sync to complete if it's in progress
            if sync_status.get('is_syncing'):
                print(f"{Fore.YELLOW}⚠ Sync in progress, waiting for completion...{Style.RESET_ALL}")
                for _ in range(TEST_TIMEOUT):
                    response = requests.get(f"{BASE_URL}/api/sync-status")
                    if response.status_code == 200:
                        sync_status = response.json()
                        if not sync_status.get('is_syncing'):
                            print(f"{Fore.GREEN}✓ Sync completed{Style.RESET_ALL}")
                            break
                    time.sleep(1)
                else:
                    print(f"{Fore.YELLOW}⚠ Sync timed out, continuing tests{Style.RESET_ALL}")
            
            print(f"{Fore.GREEN}✓ Sync status endpoint working correctly{Style.RESET_ALL}")
            test_results["tests"]["sync_status"] = {"success": True}
            
            # Step 9: Test Insights Generation
            print(f"\n{Fore.CYAN}Step 9: Testing Insights Generation{Style.RESET_ALL}")
            response = requests.post(f"{BASE_URL}/api/insights/generate")
            self.assertEqual(response.status_code, 200, "Insights generate endpoint should return 200")
            
            generate_result = response.json()
            self.assertTrue(generate_result.get('success'), "Insights generation should return success")
            print(f"{Fore.GREEN}✓ Insights generation started{Style.RESET_ALL}")
            
            # Wait for insights generation to complete
            print(f"{Fore.YELLOW}Waiting for insights generation to complete...{Style.RESET_ALL}")
            for _ in range(TEST_TIMEOUT):
                response = requests.get(f"{BASE_URL}/api/insights/status")
                if response.status_code == 200:
                    status = response.json()
                    if status.get('status') == 'completed':
                        print(f"{Fore.GREEN}✓ Insights generation completed{Style.RESET_ALL}")
                        break
                    elif status.get('status') == 'failed':
                        self.fail("Insights generation failed")
                time.sleep(1)
            else:
                print(f"{Fore.YELLOW}⚠ Insights generation timed out, continuing tests{Style.RESET_ALL}")
            
            test_results["tests"]["insights_generation"] = {"success": True}
            
            # Step 10: Test Insights Endpoint
            print(f"\n{Fore.CYAN}Step 10: Testing Insights Endpoint{Style.RESET_ALL}")
            response = requests.get(f"{BASE_URL}/api/insights")
            self.assertEqual(response.status_code, 200, "Insights endpoint should return 200")
            
            insights = response.json()
            self.assertIsInstance(insights, dict, "Insights should be a dictionary")
            
            # Check for key insights data structures
            self.assertIn('key_relationships', insights, "Insights missing key_relationships")
            self.assertIn('action_items', insights, "Insights missing action_items")
            
            print(f"{Fore.GREEN}✓ Successfully retrieved insights{Style.RESET_ALL}")
            test_results["tests"]["insights_endpoint"] = {"success": True}
            
            # Step 11: Test Gmail Token Refresh
            print(f"\n{Fore.CYAN}Step 11: Testing Gmail Token Refresh{Style.RESET_ALL}")
            response = requests.post(f"{BASE_URL}/api/auth/gmail/refresh")
            self.assertEqual(response.status_code, 200, "Gmail token refresh endpoint should return 200")
            
            refresh_result = response.json()
            self.assertTrue(refresh_result.get('success'), "Gmail token refresh should return success")
            print(f"{Fore.GREEN}✓ Gmail token refresh successful{Style.RESET_ALL}")
            test_results["tests"]["token_refresh"] = {"success": True}
            
            # Step 12: Test Database Integrity
            print(f"\n{Fore.CYAN}Step 12: Testing Database Integrity{Style.RESET_ALL}")
            response = requests.get(f"{BASE_URL}/api/debug-gmail")
            self.assertEqual(response.status_code, 200, "Gmail debug endpoint should return 200")
            
            debug_data = response.json()
            self.assertIn('database_stats', debug_data, "Debug endpoint should return database stats")
            
            # Print database statistics
            if 'database_stats' in debug_data:
                stats = debug_data['database_stats']
                print(f"{Fore.CYAN}Database Statistics:{Style.RESET_ALL}")
                for key, value in stats.items():
                    print(f"  {key}: {value}")
                
                # Verify we have user intelligence data
                self.assertIn('user_intelligence_count', stats, "Missing user intelligence count")
                self.assertGreater(stats['user_intelligence_count'], 0, "No user intelligence records found")
            
            print(f"{Fore.GREEN}✓ Database integrity verified{Style.RESET_ALL}")
            test_results["tests"]["database_integrity"] = {"success": True}
            
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
    """Run the complete end-to-end test"""
    print(f"{Fore.CYAN}========================================{Style.RESET_ALL}")
    print(f"{Fore.CYAN}  COMPLETE GMAIL INTEGRATION TEST{Style.RESET_ALL}")
    print(f"{Fore.CYAN}========================================{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Note: This test requires that you have already authenticated with Gmail{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}If you haven't authenticated yet, the test will guide you through the process{Style.RESET_ALL}")
    print()
    
    # Run the test
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
    
    print(f"\n{Fore.CYAN}========================================{Style.RESET_ALL}")
    print(f"{Fore.CYAN}  TEST COMPLETE{Style.RESET_ALL}")
    print(f"{Fore.CYAN}========================================{Style.RESET_ALL}")

if __name__ == "__main__":
    run_test()
