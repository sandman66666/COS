"""
Improved Gmail Connector with better error handling and token management.
"""

import base64
import json
import logging
import traceback
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from typing import Dict, List, Any, Optional

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

class ImprovedGmailConnector:
    """
    Improved connector for Gmail API with better error handling.
    """
    def __init__(self, token_data: Dict[str, Any]):
        """
        Initialize the Gmail connector with full token data.
        
        Args:
            token_data: OAuth2 token data including access_token, refresh_token, etc.
        """
        self.token_data = token_data
        self.service = None
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize or reinitialize the Gmail service."""
        try:
            if not self.token_data or 'access_token' not in self.token_data:
                logger.error("No access token in token data")
                raise ValueError("Access token is required for Gmail API access")
            
            # Create credentials with full token data
            credentials = Credentials(
                token=self.token_data.get('access_token'),
                refresh_token=self.token_data.get('refresh_token'),
                token_uri='https://oauth2.googleapis.com/token',
                client_id=self.token_data.get('client_id'),
                client_secret=self.token_data.get('client_secret'),
                scopes=['https://www.googleapis.com/auth/gmail.readonly']
            )
            
            # Check if token needs refresh
            if hasattr(credentials, 'expired') and credentials.expired:
                logger.info("Token expired, attempting to refresh...")
                credentials.refresh(Request())
                # Update token data with new access token
                self.token_data['access_token'] = credentials.token
                logger.info("Token refreshed successfully")
            
            # Build the Gmail service
            self.service = build('gmail', 'v1', credentials=credentials)
            logger.info("Gmail service initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing Gmail service: {str(e)}")
            logger.error(f"Token data keys: {list(self.token_data.keys()) if self.token_data else 'None'}")
            raise
    
    def test_connection(self) -> Dict[str, Any]:
        """Test if the Gmail connection is working and return detailed info."""
        try:
            # Try to get user profile
            profile = self.service.users().getProfile(userId='me').execute()
            
            # Get labels to verify read access
            labels = self.service.users().labels().list(userId='me').execute()
            
            return {
                'success': True,
                'email': profile.get('emailAddress', 'Unknown'),
                'messages_total': profile.get('messagesTotal', 0),
                'labels_count': len(labels.get('labels', [])),
                'history_id': profile.get('historyId', 'Unknown')
            }
        except HttpError as e:
            error_details = e.error_details[0] if hasattr(e, 'error_details') and e.error_details else {}
            return {
                'success': False,
                'error': str(e),
                'status_code': e.resp.status if hasattr(e, 'resp') else None,
                'reason': error_details.get('reason', 'Unknown'),
                'message': error_details.get('message', str(e))
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }
    
    def get_recent_emails(self, days_back: int = 7, max_results: int = 50) -> Dict[str, Any]:
        """
        Get recent emails with better error handling and progress tracking.
        
        Returns:
            Dict with 'success', 'emails', and 'metadata' or 'error'
        """
        try:
            # Test connection first
            connection_test = self.test_connection()
            if not connection_test['success']:
                return {
                    'success': False,
                    'error': connection_test['error'],
                    'details': connection_test
                }
            
            # Calculate date for query
            date_from = datetime.now() - timedelta(days=days_back)
            date_str = date_from.strftime('%Y/%m/%d')
            
            # Create query
            query = f'after:{date_str}'
            
            logger.info(f"Fetching emails for {connection_test['email']} with query: {query}")
            
            # Get messages with pagination support
            all_messages = []
            page_token = None
            pages_fetched = 0
            
            while len(all_messages) < max_results:
                try:
                    results = self.service.users().messages().list(
                        userId='me',
                        q=query,
                        maxResults=min(max_results - len(all_messages), 50),  # Fetch in chunks
                        pageToken=page_token
                    ).execute()
                    
                    messages = results.get('messages', [])
                    all_messages.extend(messages)
                    pages_fetched += 1
                    
                    page_token = results.get('nextPageToken')
                    if not page_token or len(all_messages) >= max_results:
                        break
                        
                except HttpError as e:
                    logger.error(f"Error fetching message list: {str(e)}")
                    if pages_fetched == 0:
                        raise
                    break
            
            logger.info(f"Found {len(all_messages)} messages across {pages_fetched} pages")
            
            # Process each message with error handling
            emails = []
            errors = []
            
            for i, message in enumerate(all_messages[:max_results]):
                try:
                    if i % 10 == 0 and i > 0:
                        logger.info(f"Processing message {i}/{len(all_messages)}")
                    
                    email_data = self._get_email_details(message['id'])
                    if email_data:
                        emails.append(email_data)
                except Exception as e:
                    error_msg = f"Error processing message {message['id']}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            return {
                'success': True,
                'emails': emails,
                'metadata': {
                    'total_found': len(all_messages),
                    'processed': len(emails),
                    'errors': len(errors),
                    'query': query,
                    'days_back': days_back,
                    'email_address': connection_test['email']
                },
                'processing_errors': errors[:5]  # Include first 5 errors for debugging
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error getting recent emails: {error_msg}")
            
            # Provide helpful error messages
            if "invalid_grant" in error_msg.lower():
                return {
                    'success': False,
                    'error': 'Authentication failed - token may be expired',
                    'suggestion': 'Please log out and log in again to refresh your authentication'
                }
            elif "insufficient permission" in error_msg.lower():
                return {
                    'success': False,
                    'error': 'Insufficient permissions to read Gmail',
                    'suggestion': 'Please ensure you granted Gmail read permissions during login'
                }
            else:
                return {
                    'success': False,
                    'error': error_msg,
                    'error_type': type(e).__name__
                }
    
    def _get_email_details(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get details of a specific email with better error handling."""
        try:
            # Get the message
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            # Extract headers
            headers = message['payload'].get('headers', [])
            header_dict = {h['name'].lower(): h['value'] for h in headers}
            
            # Get key headers with defaults
            subject = header_dict.get('subject', 'No Subject')
            sender = header_dict.get('from', 'Unknown Sender')
            date_str = header_dict.get('date', '')
            to = header_dict.get('to', '')
            cc = header_dict.get('cc', '')
            
            # Parse date
            email_date = None
            if date_str:
                try:
                    # Simple date parsing - might need improvement for all formats
                    email_date = datetime.strptime(date_str[:25], '%a, %d %b %Y %H:%M:%S')
                except:
                    email_date = None
            
            # Extract body
            body = self._get_email_body(message)
            
            # Get labels and check if unread
            labels = message.get('labelIds', [])
            is_unread = 'UNREAD' in labels
            is_important = 'IMPORTANT' in labels
            is_starred = 'STARRED' in labels
            
            # Create email data dictionary
            return {
                'id': message_id,
                'thread_id': message.get('threadId', ''),
                'subject': subject,
                'sender': sender,
                'date': date_str,
                'date_parsed': email_date.isoformat() if email_date else None,
                'to': to,
                'cc': cc,
                'body': body[:5000],  # Limit body size
                'body_truncated': len(body) > 5000,
                'is_unread': is_unread,
                'is_important': is_important,
                'is_starred': is_starred,
                'labels': labels,
                'snippet': message.get('snippet', '')
            }
            
        except Exception as e:
            logger.error(f"Error getting email details for {message_id}: {str(e)}")
            return None
    
    def _get_email_body(self, message: Dict[str, Any]) -> str:
        """Extract the body text from an email message."""
        body = ""
        
        def extract_body_from_part(part):
            if part.get('mimeType') == 'text/plain':
                data = part.get('body', {}).get('data', '')
                if data:
                    return base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
            elif part.get('mimeType') == 'text/html' and not body:  # Fallback to HTML if no plain text
                data = part.get('body', {}).get('data', '')
                if data:
                    html_body = base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
                    # Simple HTML tag removal
                    import re
                    return re.sub('<[^<]+?>', '', html_body)
            return ""
        
        payload = message.get('payload', {})
        
        # Handle multipart messages
        if 'parts' in payload:
            for part in payload['parts']:
                body += extract_body_from_part(part)
                
                # Handle nested parts
                if 'parts' in part:
                    for subpart in part['parts']:
                        body += extract_body_from_part(subpart)
        else:
            # Single part message
            body = extract_body_from_part(payload)
        
        return body.strip()
    
    def get_email_stats(self, days_back: int = 30) -> Dict[str, Any]:
        """Get email statistics for insights."""
        try:
            connection_test = self.test_connection()
            if not connection_test['success']:
                return connection_test
            
            # Get various email counts
            date_from = datetime.now() - timedelta(days=days_back)
            date_str = date_from.strftime('%Y/%m/%d')
            
            stats = {
                'total_emails': 0,
                'unread_emails': 0,
                'important_emails': 0,
                'sent_emails': 0,
                'email_address': connection_test['email']
            }
            
            # Count different types of emails
            queries = {
                'total': f'after:{date_str}',
                'unread': f'after:{date_str} is:unread',
                'important': f'after:{date_str} is:important',
                'sent': f'after:{date_str} in:sent'
            }
            
            for stat_name, query in queries.items():
                try:
                    result = self.service.users().messages().list(
                        userId='me',
                        q=query,
                        maxResults=1
                    ).execute()
                    
                    count = result.get('resultSizeEstimate', 0)
                    if stat_name == 'total':
                        stats['total_emails'] = count
                    elif stat_name == 'unread':
                        stats['unread_emails'] = count
                    elif stat_name == 'important':
                        stats['important_emails'] = count
                    elif stat_name == 'sent':
                        stats['sent_emails'] = count
                        
                except Exception as e:
                    logger.error(f"Error getting {stat_name} count: {str(e)}")
            
            return {
                'success': True,
                'stats': stats
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            } 