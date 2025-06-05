#!/usr/bin/env python3
"""
Comprehensive Test Runner for Gmail Integration

This script runs a series of tests to verify the Gmail integration functionality:
1. Verifies all required API endpoints are working
2. Tests the Gmail connector with real Gmail data (no fake data)
3. Validates database operations and data persistence
4. Checks OAuth token handling and refresh mechanisms
5. Generates a detailed report of test results

Usage:
    python run_test_suite.py [--verbose] [--report-file FILENAME]

Options:
    --verbose       Show detailed test output
    --report-file   Specify a custom report file name
"""

import os
import sys
import json
import time
import logging
import argparse
import requests
import unittest
import traceback
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = "http://localhost:8080"  # Flask development server

class TestResult:
    """Class to store test results"""
    def __init__(self, name, passed, message=None, response=None, duration=None):
        self.name = name
        self.passed = passed
        self.message = message
        self.response = response
        self.duration = duration
        self.timestamp = datetime.now()

class GmailIntegrationTester:
    """Test runner for Gmail integration"""
    
    def __init__(self, base_url=BASE_URL, verbose=False):
        self.base_url = base_url
        self.verbose = verbose
        self.session = requests.Session()
        self.results = []
        
    def run_test(self, name, func, *args, **kwargs):
        """Run a test function and record results"""
        logger.info(f"Running test: {name}")
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            
            if result.get('success', False):
                test_result = TestResult(
                    name=name,
                    passed=True,
                    message=result.get('message', 'Test passed'),
                    response=result.get('data'),
                    duration=duration
                )
                logger.info(f"✅ {name}: {test_result.message}")
            else:
                test_result = TestResult(
                    name=name,
                    passed=False,
                    message=result.get('message', 'Test failed'),
                    response=result.get('data'),
                    duration=duration
                )
                logger.error(f"❌ {name}: {test_result.message}")
                
            self.results.append(test_result)
            return test_result
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Error: {str(e)}"
            logger.error(f"❌ {name}: {error_msg}")
            if self.verbose:
                logger.error(traceback.format_exc())
                
            test_result = TestResult(
                name=name,
                passed=False,
                message=error_msg,
                duration=duration
            )
            self.results.append(test_result)
            return test_result
    
    def test_server_running(self):
        """Test if the server is running"""
        try:
            response = self.session.get(f"{self.base_url}/")
            if response.status_code == 200:
                return {
                    'success': True,
                    'message': 'Server is running',
                    'data': {'status_code': response.status_code}
                }
            else:
                return {
                    'success': False,
                    'message': f'Server returned status code {response.status_code}',
                    'data': {'status_code': response.status_code}
                }
        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'message': f'Could not connect to server at {self.base_url}',
                'data': None
            }
    
    def test_gmail_auth(self):
        """Test if Gmail authentication is working"""
        try:
            response = self.session.get(f"{self.base_url}/api/debug-session")
            if response.status_code != 200:
                return {
                    'success': False,
                    'message': f'Debug session endpoint returned status code {response.status_code}',
                    'data': {'status_code': response.status_code}
                }
            
            session_data = response.json()
            if 'gmail_token' not in session_data:
                return {
                    'success': False,
                    'message': 'No Gmail token found in session',
                    'data': session_data
                }
            
            # Check token expiration
            if 'expires_at' in session_data['gmail_token']:
                expires_at = datetime.fromtimestamp(session_data['gmail_token']['expires_at'])
                if expires_at < datetime.now():
                    return {
                        'success': False,
                        'message': f'Gmail token expired at {expires_at}',
                        'data': session_data['gmail_token']
                    }
            
            return {
                'success': True,
                'message': 'Gmail authentication is valid',
                'data': {
                    'token_type': session_data['gmail_token'].get('token_type'),
                    'scope': session_data['gmail_token'].get('scope', '').split(' ')
                }
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error checking Gmail auth: {str(e)}',
                'data': None
            }
    
    def test_gmail_api(self):
        """Test Gmail API connection using real data"""
        try:
            response = self.session.get(f"{self.base_url}/api/debug-gmail")
            if response.status_code != 200:
                return {
                    'success': False,
                    'message': f'Gmail API debug endpoint returned status code {response.status_code}',
                    'data': {'status_code': response.status_code}
                }
            
            result = response.json()
            if 'emails' not in result:
                return {
                    'success': False,
                    'message': 'No emails returned from Gmail API',
                    'data': result
                }
            
            if not isinstance(result['emails'], list):
                return {
                    'success': False,
                    'message': 'Emails should be a list',
                    'data': result
                }
            
            # Check for real email data (not fake/sample data)
            if result['emails']:
                email = result['emails'][0]
                if 'id' not in email or 'subject' not in email:
                    return {
                        'success': False,
                        'message': 'Email data missing required fields (id, subject)',
                        'data': {'email_sample': email}
                    }
            
            return {
                'success': True,
                'message': f'Gmail API connection successful, found {len(result["emails"])} emails',
                'data': {
                    'email_count': len(result['emails']),
                    'sample_fields': list(result['emails'][0].keys()) if result['emails'] else []
                }
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error testing Gmail API: {str(e)}',
                'data': None
            }
    
    def test_reset_database(self):
        """Test database reset functionality"""
        try:
            response = self.session.post(f"{self.base_url}/api/reset-database")
            if response.status_code != 200:
                return {
                    'success': False,
                    'message': f'Reset database endpoint returned status code {response.status_code}',
                    'data': {'status_code': response.status_code}
                }
            
            result = response.json()
            if not result.get('success', False):
                return {
                    'success': False,
                    'message': 'Reset database did not return success',
                    'data': result
                }
            
            return {
                'success': True,
                'message': 'Database reset successful',
                'data': result
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error resetting database: {str(e)}',
                'data': None
            }
    
    def test_api_endpoints(self):
        """Test all critical API endpoints"""
        endpoints = [
            {'url': '/api/people', 'method': 'GET', 'name': 'People API'},
            {'url': '/api/tasks', 'method': 'GET', 'name': 'Tasks API'},
            {'url': '/api/insights', 'method': 'GET', 'name': 'Insights API'},
            {'url': '/api/integrations/status', 'method': 'GET', 'name': 'Integrations Status API'},
            {'url': '/api/sync-status', 'method': 'GET', 'name': 'Sync Status API'},
            {'url': '/api/force-refresh', 'method': 'POST', 'name': 'Force Refresh API'},
            {'url': '/api/auth/gmail/refresh', 'method': 'POST', 'name': 'Gmail Token Refresh API'}
        ]
        
        results = {}
        for endpoint in endpoints:
            try:
                if endpoint['method'] == 'GET':
                    response = self.session.get(f"{self.base_url}{endpoint['url']}")
                else:
                    response = self.session.post(f"{self.base_url}{endpoint['url']}")
                
                if response.status_code == 200:
                    results[endpoint['name']] = {
                        'success': True,
                        'status_code': response.status_code,
                        'data': response.json() if response.text else None
                    }
                else:
                    results[endpoint['name']] = {
                        'success': False,
                        'status_code': response.status_code,
                        'error': response.text
                    }
            except Exception as e:
                results[endpoint['name']] = {
                    'success': False,
                    'error': str(e)
                }
        
        # Count successes and failures
        success_count = sum(1 for result in results.values() if result['success'])
        
        return {
            'success': success_count == len(endpoints),
            'message': f'{success_count}/{len(endpoints)} API endpoints working',
            'data': results
        }
    
    def test_insights_generation(self):
        """Test insights generation from Gmail data"""
        try:
            # Start insights generation
            response = self.session.post(f"{self.base_url}/api/insights/generate")
            if response.status_code != 200:
                return {
                    'success': False,
                    'message': f'Insights generation endpoint returned status code {response.status_code}',
                    'data': {'status_code': response.status_code}
                }
            
            start_result = response.json()
            if not start_result.get('success', False):
                return {
                    'success': False,
                    'message': 'Insights generation did not start successfully',
                    'data': start_result
                }
            
            # Wait for insights generation to complete (max 30 seconds)
            max_wait = 30
            for i in range(max_wait):
                time.sleep(1)
                response = self.session.get(f"{self.base_url}/api/sync-status")
                if response.status_code == 200:
                    status = response.json()
                    if status.get('status') == 'completed':
                        break
                    elif status.get('status') == 'failed':
                        return {
                            'success': False,
                            'message': f'Insights generation failed: {status.get("error", "Unknown error")}',
                            'data': status
                        }
            else:
                return {
                    'success': False,
                    'message': f'Insights generation timed out after {max_wait} seconds',
                    'data': {'last_status': status if 'status' in locals() else None}
                }
            
            # Check if insights were generated
            response = self.session.get(f"{self.base_url}/api/insights")
            if response.status_code != 200:
                return {
                    'success': False,
                    'message': f'Insights endpoint returned status code {response.status_code}',
                    'data': {'status_code': response.status_code}
                }
            
            insights = response.json()
            if not insights or not isinstance(insights, dict):
                return {
                    'success': False,
                    'message': 'No insights data returned',
                    'data': insights
                }
            
            # Check for key insights data structures
            missing_keys = []
            for key in ['key_relationships', 'action_items']:
                if key not in insights:
                    missing_keys.append(key)
            
            if missing_keys:
                return {
                    'success': False,
                    'message': f'Insights missing required keys: {", ".join(missing_keys)}',
                    'data': {'available_keys': list(insights.keys())}
                }
            
            return {
                'success': True,
                'message': 'Insights generation successful',
                'data': {
                    'relationships_count': len(insights.get('key_relationships', [])),
                    'action_items_count': len(insights.get('action_items', []))
                }
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error testing insights generation: {str(e)}',
                'data': None
            }
    
    def test_database_integrity(self):
        """Test database integrity after operations"""
        try:
            response = self.session.get(f"{self.base_url}/api/debug-gmail")
            if response.status_code != 200:
                return {
                    'success': False,
                    'message': f'Debug endpoint returned status code {response.status_code}',
                    'data': {'status_code': response.status_code}
                }
            
            result = response.json()
            if 'database_stats' not in result:
                return {
                    'success': False,
                    'message': 'Debug endpoint missing database stats',
                    'data': result
                }
            
            stats = result['database_stats']
            required_stats = ['user_intelligence_count', 'contact_intelligence_count', 'email_sync_status_count']
            missing_stats = [stat for stat in required_stats if stat not in stats]
            
            if missing_stats:
                return {
                    'success': False,
                    'message': f'Database stats missing required fields: {", ".join(missing_stats)}',
                    'data': {'available_stats': list(stats.keys())}
                }
            
            # Check if we have user intelligence data
            if stats['user_intelligence_count'] == 0:
                return {
                    'success': False,
                    'message': 'No user intelligence records found',
                    'data': stats
                }
            
            return {
                'success': True,
                'message': 'Database integrity verified',
                'data': stats
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error testing database integrity: {str(e)}',
                'data': None
            }
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        logger.info("Starting Gmail integration tests")
        
        # First check if server is running
        server_test = self.run_test("Server Running", self.test_server_running)
        if not server_test.passed:
            logger.error("Server is not running, cannot continue tests")
            return self.results
        
        # Run Gmail auth test
        auth_test = self.run_test("Gmail Authentication", self.test_gmail_auth)
        if not auth_test.passed:
            logger.error("Gmail authentication failed, cannot continue Gmail API tests")
        else:
            # Reset database before tests
            self.run_test("Database Reset", self.test_reset_database)
            
            # Run remaining tests
            self.run_test("Gmail API Connection", self.test_gmail_api)
            self.run_test("API Endpoints", self.test_api_endpoints)
            self.run_test("Insights Generation", self.test_insights_generation)
            self.run_test("Database Integrity", self.test_database_integrity)
        
        return self.results
    
    def generate_report(self, file_path=None):
        """Generate a report of test results"""
        if not self.results:
            logger.warning("No test results to report")
            return
        
        passed = sum(1 for result in self.results if result.passed)
        failed = len(self.results) - passed
        
        report = {
            "summary": {
                "total_tests": len(self.results),
                "passed": passed,
                "failed": failed,
                "success_rate": f"{passed/len(self.results)*100:.1f}%" if self.results else "0%",
                "timestamp": datetime.now().isoformat()
            },
            "tests": []
        }
        
        for result in self.results:
            test_report = {
                "name": result.name,
                "passed": result.passed,
                "message": result.message,
                "duration": f"{result.duration:.3f}s" if result.duration else None,
                "timestamp": result.timestamp.isoformat()
            }
            
            # Include response data if verbose
            if self.verbose and result.response:
                test_report["response"] = result.response
                
            report["tests"].append(test_report)
        
        # Print report to console
        print("\n" + "="*50)
        print(f"GMAIL INTEGRATION TEST REPORT")
        print("="*50)
        print(f"Total Tests: {report['summary']['total_tests']}")
        print(f"Passed: {report['summary']['passed']}")
        print(f"Failed: {report['summary']['failed']}")
        print(f"Success Rate: {report['summary']['success_rate']}")
        print("-"*50)
        
        for test in report["tests"]:
            status = "✅ PASS" if test["passed"] else "❌ FAIL"
            print(f"{status} | {test['name']} - {test['message']}")
        
        print("="*50)
        
        # Save report to file if requested
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    json.dump(report, f, indent=2)
                print(f"Report saved to {file_path}")
            except Exception as e:
                logger.error(f"Error saving report: {str(e)}")
        
        return report

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Gmail Integration Test Runner")
    parser.add_argument("--verbose", action="store_true", help="Show detailed test output")
    parser.add_argument("--report-file", type=str, help="Save report to file")
    args = parser.parse_args()
    
    # Set up report file path
    report_file = args.report_file
    if not report_file:
        os.makedirs("test_reports", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"test_reports/gmail_integration_test_{timestamp}.json"
    
    # Run tests
    tester = GmailIntegrationTester(verbose=args.verbose)
    tester.run_all_tests()
    tester.generate_report(report_file)

if __name__ == "__main__":
    main()
