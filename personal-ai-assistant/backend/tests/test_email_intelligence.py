"""
Tests for the email intelligence module.
"""

import unittest
from unittest.mock import MagicMock, patch
import json

from backend.core.claude_integration.email_intelligence import EmailIntelligence


class TestEmailIntelligence(unittest.TestCase):
    """Test cases for the EmailIntelligence class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_claude_client = MagicMock()
        self.mock_claude_client.client = MagicMock()
        self.email_intelligence = EmailIntelligence(self.mock_claude_client)
        
        # Sample response data
        self.sample_response = {
            "key_relationships": [
                {"name": "John Doe", "email": "john@example.com", "interaction_frequency": "high"}
            ],
            "active_projects": ["Project Alpha", "Project Beta"],
            "communication_patterns": {"peak_time": "morning", "response_time": "fast"},
            "action_items": ["Follow up with John", "Review proposal"],
            "important_information": ["Deadline on Friday", "Meeting scheduled for Thursday"]
        }
        
        # Mock Claude response
        mock_content = MagicMock()
        mock_content.text = json.dumps(self.sample_response)
        self.mock_claude_client.client.messages.create.return_value = MagicMock(
            content=[mock_content]
        )
    
    def test_analyze_recent_emails(self):
        """Test analyzing recent emails."""
        result = self.email_intelligence.analyze_recent_emails("user@example.com", 30)
        
        # Verify Claude client was called with correct parameters
        self.mock_claude_client.client.messages.create.assert_called_once()
        call_args = self.mock_claude_client.client.messages.create.call_args[1]
        
        self.assertEqual(call_args["model"], "claude-4-sonnet-20250514")
        self.assertEqual(call_args["max_tokens"], 4000)
        
        # Check that messages parameter contains our prompt
        messages = call_args["messages"]
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["role"], "user")
        self.assertIn("analyze my emails from the last 30 days", messages[0]["content"])
        
        # Check that system prompt mentions native Gmail integration
        system_prompt = call_args["system"]
        self.assertIn("NATIVE ACCESS to their Gmail", system_prompt)
        
        # Verify result matches our sample response
        self.assertEqual(result, self.sample_response)
    
    def test_scan_urgent_emails(self):
        """Test scanning for urgent emails."""
        result = self.email_intelligence.scan_urgent_emails("user@example.com", 24)
        
        # Verify Claude client was called
        self.mock_claude_client.client.messages.create.assert_called_once()
        call_args = self.mock_claude_client.client.messages.create.call_args[1]
        
        # Check that messages parameter contains our prompt
        messages = call_args["messages"]
        self.assertIn("scan my emails from the last 24 hours", messages[0]["content"])
        
        # Verify result matches our sample response
        self.assertEqual(result, self.sample_response)
    
    @patch('backend.core.claude_integration.email_intelligence.json.loads')
    def test_error_handling(self, mock_json_loads):
        """Test error handling when Claude response is not valid JSON."""
        # Make json.loads raise an exception
        mock_json_loads.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        
        # Set up a non-JSON response from Claude
        mock_content = MagicMock()
        mock_content.text = "This is not valid JSON"
        self.mock_claude_client.client.messages.create.return_value = MagicMock(
            content=[mock_content]
        )
        
        # Call the method and check the result
        result = self.email_intelligence.analyze_recent_emails("user@example.com")
        
        # Verify error handling
        self.assertEqual(result["error"], "Failed to parse response as JSON")
        self.assertIn("raw_response", result)


if __name__ == '__main__':
    unittest.main()
