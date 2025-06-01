"""
Gmail Connector for accessing Gmail data via Google API.
"""

import base64
import json
import logging
import traceback
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from typing import Dict, List, Any, Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

class GmailConnector:
    """
    Connector for Gmail API to fetch and process emails.
    """
    def __init__(self, access_token: str):
        """
        Initialize the Gmail connector with an access token.
        
        Args:
            access_token: OAuth2 access token for Gmail API
        """
        self.access_token = access_token
        self.service = self._build_service()
    
    def _build_service(self):
        """Build and return a Gmail service object."""
        try:
            if not self.access_token:
                logger.error("No access token provided")
                raise ValueError("Access token is required for Gmail API access")
                
            # Create credentials object from just the access token
            # This is the simplest way to use an existing OAuth token
            credentials = Credentials(token=self.access_token)
            
            # Build the Gmail service with these credentials
            service = build('gmail', 'v1', credentials=credentials)
            logger.info("Successfully built Gmail service with provided access token")
            return service
        except Exception as e:
            logger.error(f"Error building Gmail service: {str(e)}")
            raise
    
    def test_connection(self) -> bool:
        """Test if the Gmail connection is working."""
        try:
            # Try to get user profile as a simple test
            self.service.users().getProfile(userId='me').execute()
            return True
        except Exception as e:
            logger.error(f"Gmail connection test failed: {str(e)}")
            return False
    
    def get_recent_emails(self, days_back: int = 7, max_results: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent emails from the last N days.
        
        Args:
            days_back: Number of days back to fetch emails from
            max_results: Maximum number of emails to return
            
        Returns:
            List of email data dictionaries
        """
        try:
            # Test connection first to fail fast if there are authentication issues
            if not self.test_connection():
                logger.error("Gmail connection test failed. Cannot fetch emails.")
                return []
                
            # Calculate date for query
            date_from = datetime.now() - timedelta(days=days_back)
            date_str = date_from.strftime('%Y/%m/%d')
            
            # Create query
            query = f'after:{date_str}'
            
            logger.info(f"Fetching emails with query: {query}, max results: {max_results}")
            
            # Get messages matching query
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            logger.info(f"Found {len(messages)} messages matching query")
            
            # Process each message
            emails = []
            for i, message in enumerate(messages):
                if i % 10 == 0 and i > 0:
                    logger.info(f"Processed {i}/{len(messages)} messages")
                email_data = self._get_email_details(message['id'])
                if email_data:
                    emails.append(email_data)
            
            logger.info(f"Successfully processed {len(emails)} emails")
            return emails
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"Error getting recent emails: {error_message}")
            logger.debug(f"Error details: {traceback.format_exc()}")
            
            # Log more specific information about the error
            if "invalid_grant" in error_message.lower():
                logger.error("OAuth token issue detected. The token may be expired or invalid.")
            elif "access_not_configured" in error_message.lower():
                logger.error("Gmail API access not properly configured. Check API enablement in Google Cloud Console.")
            elif "permission_denied" in error_message.lower():
                logger.error("Permission denied. Check that the OAuth token has the necessary Gmail scopes.")
            
            # Return empty list on error
            return []
    
    def get_urgent_emails(self, days_back: int = 3, max_results: int = 20) -> List[Dict[str, Any]]:
        """
        Get potentially urgent emails that need attention.
        
        Args:
            days_back: Number of days back to check for urgent emails
            max_results: Maximum number of emails to return
            
        Returns:
            List of urgent email data dictionaries
        """
        try:
            # Get recent emails first
            recent_emails = self.get_recent_emails(days_back=days_back, max_results=100)
            
            # Filter for potentially urgent emails
            urgent_emails = [email for email in recent_emails if self._is_potentially_urgent(email)]
            
            # Limit results
            return urgent_emails[:max_results]
            
        except Exception as e:
            logger.error(f"Error getting urgent emails: {str(e)}")
            return []
    
    def _get_email_details(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Get details of a specific email.
        
        Args:
            message_id: ID of the message to get details for
            
        Returns:
            Dictionary with email details or None if error
        """
        try:
            # Get the message
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            # Extract headers
            headers = message['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown')
            date = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')
            to = next((h['value'] for h in headers if h['name'].lower() == 'to'), '')
            
            # Extract body
            body = self._get_email_body(message)
            
            # Check if unread
            is_unread = 'UNREAD' in message.get('labelIds', [])
            
            # Create email data dictionary
            email_data = {
                'id': message_id,
                'thread_id': message.get('threadId', ''),
                'subject': subject,
                'sender': sender,
                'date': date,
                'to': to,
                'body': body,
                'is_unread': is_unread,
                'labels': message.get('labelIds', [])
            }
            
            return email_data
            
        except Exception as e:
            logger.error(f"Error getting email details for {message_id}: {str(e)}")
            return None
    
    def _get_email_body(self, message: Dict[str, Any]) -> str:
        """
        Extract the body text from an email message.
        
        Args:
            message: The message object from Gmail API
            
        Returns:
            String containing the email body text
        """
        body = ""
        
        if 'payload' not in message:
            return body
            
        if 'parts' in message['payload']:
            for part in message['payload']['parts']:
                if part.get('mimeType') == 'text/plain' and 'data' in part.get('body', {}):
                    body_bytes = base64.urlsafe_b64decode(part['body']['data'])
                    body += body_bytes.decode('utf-8', errors='replace')
        elif 'body' in message['payload'] and 'data' in message['payload']['body']:
            body_bytes = base64.urlsafe_b64decode(message['payload']['body']['data'])
            body += body_bytes.decode('utf-8', errors='replace')
            
        return body
    
    def _is_potentially_urgent(self, email_data: Dict[str, Any]) -> bool:
        """Determine if an email might be urgent"""
        # Simple heuristics for urgency
        subject = email_data.get('subject', '').lower()
        body = email_data.get('body', '').lower()
        
        urgent_keywords = [
            'urgent', 'asap', 'immediate', 'deadline', 'important',
            'meeting', 'call', 'response needed', 'please respond',
            'investor', 'funding', 'contract', 'deal'
        ]
        
        # Check if unread
        if email_data.get('is_unread', False):
            # Check for urgent keywords
            for keyword in urgent_keywords:
                if keyword in subject or keyword in body:
                    return True
        
        return False
