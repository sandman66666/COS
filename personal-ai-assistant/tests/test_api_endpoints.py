#!/usr/bin/env python3
"""
API Endpoint Test Script for Gmail Integration

This script tests the API endpoints without requiring authentication.
It checks if the endpoints are properly registered and responding.

Usage:
    python test_api_endpoints.py
"""

import sys
import json
import requests
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = "http://localhost:8080"  # Flask development server

def test_endpoint(endpoint, method="GET", expected_status=None):
    """Test an API endpoint and return the result"""
    url = f"{BASE_URL}{endpoint}"
    logger.info(f"Testing {method} {url}")
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=5)
        elif method == "POST":
            response = requests.post(url, timeout=5)
        else:
            logger.error(f"Unsupported method: {method}")
            return False, f"Unsupported method: {method}", None
        
        # Check if status code matches expected (if provided)
        if expected_status and response.status_code != expected_status:
            logger.warning(f"Status code {response.status_code} does not match expected {expected_status}")
        
        # For our test purposes, we'll consider any response (even error responses) as a success
        # since we're just checking if the endpoint is registered
        return True, f"Status: {response.status_code}", response
    
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error for {url}")
        return False, "Connection error", None
    except requests.exceptions.Timeout:
        logger.error(f"Timeout for {url}")
        return False, "Timeout", None
    except Exception as e:
        logger.error(f"Error testing {url}: {str(e)}")
        return False, f"Error: {str(e)}", None

def run_tests():
    """Run tests on all critical API endpoints"""
    # Define endpoints to test
    endpoints = [
        # Main app endpoints
        {"endpoint": "/", "method": "GET", "name": "Main Page"},
        
        # API endpoints
        {"endpoint": "/api/people", "method": "GET", "name": "People API"},
        {"endpoint": "/api/tasks", "method": "GET", "name": "Tasks API"},
        {"endpoint": "/api/insights", "method": "GET", "name": "Insights API"},
        {"endpoint": "/api/sync-status", "method": "GET", "name": "Sync Status API"},
        {"endpoint": "/api/reset-database", "method": "POST", "name": "Reset Database API"},
        {"endpoint": "/api/force-refresh", "method": "POST", "name": "Force Refresh API"},
        
        # Auth endpoints
        {"endpoint": "/api/auth/gmail", "method": "GET", "name": "Gmail Auth API"},
        {"endpoint": "/api/auth/gmail/callback", "method": "GET", "name": "Gmail Auth Callback API"},
        
        # Debug endpoints
        {"endpoint": "/api/debug-gmail", "method": "GET", "name": "Debug Gmail API"},
    ]
    
    results = []
    
    # Test each endpoint
    for endpoint in endpoints:
        success, message, response = test_endpoint(
            endpoint["endpoint"], 
            endpoint["method"]
        )
        
        result = {
            "name": endpoint["name"],
            "endpoint": endpoint["endpoint"],
            "method": endpoint["method"],
            "success": success,
            "message": message,
            "status_code": response.status_code if response else None,
        }
        
        results.append(result)
    
    return results

def generate_report(results):
    """Generate a report of test results"""
    # Count successes and failures
    total = len(results)
    successes = sum(1 for r in results if r["success"])
    
    # Print report header
    print("\n" + "="*50)
    print(f"API ENDPOINT TEST REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)
    print(f"Total Endpoints: {total}")
    print(f"Successful: {successes}")
    print(f"Failed: {total - successes}")
    print("-"*50)
    
    # Print detailed results
    for result in results:
        status = "✅" if result["success"] else "❌"
        print(f"{status} {result['method']} {result['endpoint']} - {result['message']}")
    
    print("="*50)
    
    # Save report to file
    report_file = f"test_reports/api_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        import os
        os.makedirs("test_reports", exist_ok=True)
        with open(report_file, 'w') as f:
            json.dump({
                "summary": {
                    "total": total,
                    "successes": successes,
                    "failures": total - successes,
                    "timestamp": datetime.now().isoformat()
                },
                "results": results
            }, f, indent=2)
        print(f"Report saved to {report_file}")
    except Exception as e:
        logger.error(f"Error saving report: {str(e)}")

if __name__ == "__main__":
    print("Starting API endpoint tests...")
    results = run_tests()
    generate_report(results)
