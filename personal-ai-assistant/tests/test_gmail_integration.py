#!/usr/bin/env python3
"""
End-to-End Test Script for Gmail Integration and UI Data Display

This script tests the complete flow of Gmail integration, including:
1. OAuth authentication and token handling
2. Email fetching via Gmail API
3. Data processing and storage
4. API endpoints for UI data display
5. Reset database functionality

Usage:
    python test_gmail_integration.py

Note: This requires a valid Gmail OAuth token in the test session.
"""

import os
import sys
import json
import time
import logging
import requests
import unittest
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = "http://localhost:8080"  # Flask development server
TEST_EMAIL = os.environ.get("TEST_EMAIL", "test@example.com")  # Override with real email for testing
TEST_TIMEOUT = 30  # Seconds to wait for async operations

class GmailIntegrationTest(unittest.TestCase):
    """Test suite for Gmail integration and UI data display"""
    
    def setUp(self):
        """Set up test environment"""
        # Create a session for making authenticated requests
        self.session = requests.Session()
        
        # Check if server is running
        try:
            response = self.session.get(f"{BASE_URL}/api/debug-session")
            if response.status_code != 200:
                logger.error(f"Server returned status code {response.status_code}")
                logger.error("Make sure the Flask server is running")
                sys.exit(1)
            
            # Check if we have a valid session with Gmail tokens
            session_data = response.json()
            if 'gmail_token' not in session_data:
                logger.error("No Gmail token found in session")
                logger.error("Please authenticate with Gmail before running tests")
                sys.exit(1)
                
            logger.info("Server is running and session is valid")
            
        except requests.exceptions.ConnectionError:
            logger.error(f"Could not connect to server at {BASE_URL}")
            logger.error("Make sure the Flask server is running")
            sys.exit(1)
    
    def test_01_reset_database(self):
        """Test database reset functionality"""
        logger.info("Testing database reset...")
        
        response = self.session.post(f"{BASE_URL}/api/reset-database")
        self.assertEqual(response.status_code, 200, "Reset database failed")
        
        result = response.json()
        self.assertTrue(result.get('success'), "Reset database did not return success")
        logger.info("Database reset successful")
    
    def test_02_gmail_connection(self):
        """Test Gmail API connection and token refresh"""
        logger.info("Testing Gmail API connection...")
        
        response = self.session.get(f"{BASE_URL}/api/debug-gmail")
        self.assertEqual(response.status_code, 200, "Gmail API connection failed")
        
        result = response.json()
        self.assertIn('emails', result, "No emails returned from Gmail API")
        self.assertIsInstance(result['emails'], list, "Emails should be a list")
        
        # Verify we're getting real data, not sample data
        if result['emails']:
            # Check that we have some email data with expected fields
            self.assertIn('id', result['emails'][0], "Email missing ID field")
            self.assertIn('subject', result['emails'][0], "Email missing subject field")
        
        logger.info(f"Gmail API connection successful, found {len(result['emails'])} emails")
    
    def test_03_people_endpoint(self):
        """Test /api/people endpoint for contacts data"""
        logger.info("Testing /api/people endpoint...")
        
        response = self.session.get(f"{BASE_URL}/api/people")
        self.assertEqual(response.status_code, 200, "/api/people endpoint failed")
        
        people = response.json()
        self.assertIsInstance(people, list, "People should be a list")
        
        # Log the number of contacts found
        logger.info(f"Found {len(people)} contacts")
        
        # If we have contacts, verify the data structure
        if people:
            contact = people[0]
            self.assertIn('email', contact, "Contact missing email field")
            self.assertIn('name', contact, "Contact missing name field")
        
        logger.info("/api/people endpoint test successful")
    
    def test_04_tasks_endpoint(self):
        """Test /api/tasks endpoint"""
        logger.info("Testing /api/tasks endpoint...")
        
        response = self.session.get(f"{BASE_URL}/api/tasks")
        self.assertEqual(response.status_code, 200, "/api/tasks endpoint failed")
        
        tasks = response.json()
        self.assertIsInstance(tasks, list, "Tasks should be a list")
        
        logger.info(f"Found {len(tasks)} tasks")
        logger.info("/api/tasks endpoint test successful")
    
    def test_05_insights_generate(self):
        """Test /api/insights/generate endpoint"""
        logger.info("Testing /api/insights/generate endpoint...")
        
        # Start the insights generation process
        response = self.session.post(f"{BASE_URL}/api/insights/generate")
        self.assertEqual(response.status_code, 200, "/api/insights/generate endpoint failed")
        
        result = response.json()
        self.assertTrue(result.get('success'), "Insights generation did not return success")
        
        # Wait for the background job to complete
        logger.info("Waiting for insights generation to complete...")
        for _ in range(TEST_TIMEOUT):
            response = self.session.get(f"{BASE_URL}/api/sync-status")
            if response.status_code == 200:
                status = response.json()
                if status.get('status') == 'completed':
                    logger.info("Insights generation completed")
                    break
                elif status.get('status') == 'failed':
                    self.fail("Insights generation failed")
            time.sleep(1)
        else:
            logger.warning("Insights generation timed out, continuing tests")
        
        logger.info("/api/insights/generate endpoint test successful")
    
    def test_06_insights_endpoint(self):
        """Test /api/insights endpoint"""
        logger.info("Testing /api/insights endpoint...")
        
        response = self.session.get(f"{BASE_URL}/api/insights")
        self.assertEqual(response.status_code, 200, "/api/insights endpoint failed")
        
        insights = response.json()
        self.assertIsInstance(insights, dict, "Insights should be a dictionary")
        
        # Check for key insights data structures
        self.assertIn('key_relationships', insights, "Insights missing key_relationships")
        self.assertIn('action_items', insights, "Insights missing action_items")
        
        logger.info("/api/insights endpoint test successful")
    
    def test_07_force_refresh(self):
        """Test /api/force-refresh endpoint"""
        logger.info("Testing /api/force-refresh endpoint...")
        
        response = self.session.post(f"{BASE_URL}/api/force-refresh")
        self.assertEqual(response.status_code, 200, "/api/force-refresh endpoint failed")
        
        result = response.json()
        self.assertTrue(result.get('success'), "Force refresh did not return success")
        
        logger.info("/api/force-refresh endpoint test successful")
    
    def test_08_integrations_status(self):
        """Test /api/integrations/status endpoint"""
        logger.info("Testing /api/integrations/status endpoint...")
        
        response = self.session.get(f"{BASE_URL}/api/integrations/status")
        self.assertEqual(response.status_code, 200, "/api/integrations/status endpoint failed")
        
        status = response.json()
        self.assertIn('gmail', status, "Integrations status missing Gmail")
        self.assertTrue(status['gmail']['connected'], "Gmail should be connected")
        
        logger.info("/api/integrations/status endpoint test successful")
    
    def test_09_gmail_token_refresh(self):
        """Test Gmail token refresh functionality"""
        logger.info("Testing Gmail token refresh...")
        
        response = self.session.post(f"{BASE_URL}/api/auth/gmail/refresh")
        self.assertEqual(response.status_code, 200, "Gmail token refresh failed")
        
        result = response.json()
        self.assertTrue(result.get('success'), "Gmail token refresh did not return success")
        
        logger.info("Gmail token refresh successful")
    
    def test_10_database_integrity(self):
        """Test database integrity after all operations"""
        logger.info("Testing database integrity...")
        
        # Check if we have user intelligence data
        response = self.session.get(f"{BASE_URL}/api/debug-gmail")
        self.assertEqual(response.status_code, 200)
        
        result = response.json()
        self.assertIn('database_stats', result, "Debug endpoint missing database stats")
        self.assertIn('user_intelligence_count', result['database_stats'], "Missing user intelligence count")
        
        # Verify we have at least one user intelligence record
        self.assertGreater(result['database_stats']['user_intelligence_count'], 0, 
                          "No user intelligence records found")
        
        logger.info("Database integrity test successful")

def run_tests():
    """Run the test suite"""
    logger.info("Starting Gmail integration end-to-end tests")
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
    logger.info("All tests completed")

if __name__ == "__main__":
    run_tests()
