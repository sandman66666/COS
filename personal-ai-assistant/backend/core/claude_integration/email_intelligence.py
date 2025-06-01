"""
Email Intelligence Module using Claude for email analysis with data from GmailConnector.

This module provides functionality for:
1. Business Intelligence Sync - Analyzing emails from the last 30 days
2. Real-time Alert System - Scanning recent emails for urgent items
3. People Intelligence - Building profiles based on email interactions
"""

import json
import logging
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

from backend.integrations.gmail.gmail_connector import GmailConnector
import anthropic
from anthropic.types import ContentBlockDeltaEvent
import os

logger = logging.getLogger(__name__)

class EmailIntelligence:
    def __init__(self, claude_client):
        """
        Initialize the Email Intelligence module with a Claude client.
        
        Args:
            claude_client: An instance of the Claude client with API access
        """
        self.claude_client = claude_client
    
    def analyze_recent_emails(self, user_email: str, access_token: str = None, days_back: int = 30, previous_insights: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze emails from the last N days to extract business intelligence using multiple targeted prompts.
        Uses the Gmail API to fetch real emails via GmailConnector.
        
        Args:
            user_email: The email of the user whose emails to analyze
            access_token: OAuth access token for Gmail API
            days_back: Number of days back to analyze (default: 30)
            previous_insights: Previously generated insights to build upon (default: None)
            
        Returns:
            Dict containing analysis results with key insights from multiple specialized prompts
        """
        logger.info(f"Analyzing emails from last {days_back} days for {user_email}")
        analysis_type = "incremental" if previous_insights else "full"
        logger.info(f"Performing {analysis_type} analysis")
        
        try:
            # Validate we have an access token
            if not access_token:
                logger.error(f"No access token provided for {user_email}")
                return {
                    "status": "error",
                    "message": "No access token provided for Gmail API",
                    "key_relationships": [],
                    "active_projects": [],
                    "communication_patterns": {},
                    "action_items": [],
                    "important_information": []
                }
                
            # Initialize Gmail connector with the access token
            gmail = GmailConnector(access_token)
            
            # Test the connection
            if not gmail.test_connection():
                logger.error(f"Failed to connect to Gmail API for {user_email}")
                return {
                    "status": "error",
                    "message": "Failed to connect to Gmail API",
                    "key_relationships": [],
                    "active_projects": [],
                    "communication_patterns": {},
                    "action_items": [],
                    "important_information": []
                }
            
            # Fetch real emails using the Gmail API
            logger.info(f"Fetching emails from Gmail API for {user_email}")
            email_summaries = gmail.get_recent_emails(days_back=days_back, max_results=50)  # Reduced from 100 to 50
            
            if not email_summaries:
                logger.warning(f"No emails found for {user_email} in the last {days_back} days")
            else:
                logger.info(f"Successfully fetched {len(email_summaries)} emails for {user_email}")
                
                # Truncate email bodies to avoid token limit
                for email in email_summaries:
                    if 'body' in email and len(email['body']) > 1000:
                        email['body'] = email['body'][:1000] + "... [truncated]"
                    
                    # Also limit subject and sender info
                    if 'subject' in email and len(email['subject']) > 200:
                        email['subject'] = email['subject'][:200] + "..."
            
            # Create combined results dictionary
            combined_results = {
                "status": "success",
                "message": "Analysis completed successfully"
            }
            
            # Get relationships analysis
            relationships_prompt = self._create_relationships_prompt(user_email, email_summaries, previous_insights)
            relationships_response = self._get_structured_response(user_email, relationships_prompt, "key_relationships", days_back)
            combined_results["key_relationships"] = relationships_response.get("key_relationships", [])
            
            # Get projects analysis
            projects_prompt = self._create_projects_prompt(user_email, email_summaries, previous_insights)
            projects_response = self._get_structured_response(user_email, projects_prompt, "active_projects", days_back)
            combined_results["active_projects"] = projects_response.get("active_projects", [])
            
            # Get communication patterns analysis
            patterns_prompt = self._create_patterns_prompt(user_email, email_summaries, previous_insights)
            patterns_response = self._get_structured_response(user_email, patterns_prompt, "communication_patterns", days_back)
            combined_results["communication_patterns"] = patterns_response.get("communication_patterns", {})
            
            # Get action items analysis
            actions_prompt = self._create_actions_prompt(user_email, email_summaries, previous_insights)
            actions_response = self._get_structured_response(user_email, actions_prompt, "action_items", days_back)
            combined_results["action_items"] = actions_response.get("action_items", [])
            
            # Get important information analysis
            info_prompt = self._create_info_prompt(user_email, email_summaries, previous_insights)
            info_response = self._get_structured_response(user_email, info_prompt, "important_information", days_back)
            combined_results["important_information"] = info_response.get("important_information", [])
            
            logger.info(f"Successfully analyzed emails for {user_email} using multiple targeted prompts")
            return combined_results
            
        except Exception as e:
            logger.error(f"Error analyzing emails for {user_email}: {str(e)}")
            return {
                "status": "error",
                "message": f"Error analyzing emails: {str(e)}",
                "key_relationships": [],
                "active_projects": [],
                "communication_patterns": {},
                "action_items": [],
                "important_information": []
            }
    
    def _create_relationships_prompt(self, user_email: str, email_summaries: List[Dict], previous_insights: Dict[str, Any] = None) -> str:
        """Create a prompt for analyzing key relationships from emails."""
        # Create a more concise summary focusing on sender information
        concise_summaries = []
        for email in email_summaries[:30]:  # Limit to 30 most recent emails
            concise_summaries.append({
                'sender': email.get('sender', 'Unknown'),
                'subject': email.get('subject', '')[:100],  # Limit subject length
                'date': email.get('date', ''),
                'snippet': email.get('body', '')[:200] if 'body' in email else ''  # Use snippet instead of full body
            })
        
        # Include previous relationships if available
        previous_relationships_text = ""
        if previous_insights and 'key_relationships' in previous_insights and previous_insights['key_relationships']:
            previous_relationships_text = f"""
            IMPORTANT: Here are the key relationships identified from previous email analysis. 
            Build upon and update this information with the new email data:
            {json.dumps(previous_insights['key_relationships'], indent=2)}
            """
        
        return f"""
        Analyze the following email summaries from {user_email} to identify key relationships.
        
        {previous_relationships_text}
        
        Email data (showing sender, subject, date, and brief snippet):
        {json.dumps(concise_summaries, indent=2)}
        
        Provide a comprehensive analysis of key relationships in JSON format with the following structure:
        {{
            "key_relationships": [
                {{
                    "name": "Person's Name",
                    "email": "person@example.com",
                    "role": "Their professional role or relationship",
                    "importance": "High/Medium/Low",
                    "recent_interactions": "Brief summary of recent interactions",
                    "action_needed": "Any follow-up needed (or null if none)"
                }}
            ]
        }}
        
        Include at least 5-10 key relationships if they exist in the data, ordered by importance.
        If a person appears in both the previous relationships and the new emails, merge the information to create a more complete profile that builds upon the existing knowledge.
        """
    
    def _create_projects_prompt(self, user_email: str, email_summaries: List[Dict], previous_insights: Dict[str, Any] = None) -> str:
        """Create a prompt for analyzing active projects from emails."""
        # Create a more concise summary focusing on project-related information
        concise_summaries = []
        for email in email_summaries[:30]:  # Limit to 30 most recent emails
            concise_summaries.append({
                'sender': email.get('sender', 'Unknown'),
                'subject': email.get('subject', '')[:100],  # Limit subject length
                'date': email.get('date', ''),
                'snippet': email.get('body', '')[:200] if 'body' in email else ''  # Use snippet instead of full body
            })
        
        # Include previous projects if available
        previous_projects_text = ""
        if previous_insights and 'active_projects' in previous_insights and previous_insights['active_projects']:
            previous_projects_text = f"""
            IMPORTANT: Here are the active projects identified from previous email analysis. 
            Build upon and update this information with the new email data, tracking progress and changes in status:
            {json.dumps(previous_insights['active_projects'], indent=2)}
            """
        
        return f"""
        Analyze the following email summaries from {user_email} to identify active projects and initiatives.
        
        {previous_projects_text}
        
        Email data (showing sender, subject, date, and brief snippet):
        {json.dumps(concise_summaries, indent=2)}
        
        Provide a comprehensive analysis of active projects in JSON format with the following structure:
        {{
            "active_projects": [
                {{
                    "name": "Project Name",
                    "description": "Brief description of the project",
                    "status": "Current status (e.g., In Progress, Planning, Completed)",
                    "key_stakeholders": ["Person1", "Person2"],
                    "priority": "High/Medium/Low",
                    "next_steps": "Upcoming actions or milestones"
                }}
            ]
        }}
        
        Include at least 3-7 active projects if they exist in the data, ordered by priority.
        If a project appears in both the previous projects and the new emails, merge the information to create a more complete profile, updating status and progress based on the new information.
        Track how projects evolve over time, noting any changes in status, priority, or stakeholders.
        """
    
    def _create_patterns_prompt(self, user_email: str, email_summaries: List[Dict], previous_insights: Dict[str, Any] = None) -> str:
        """Create a prompt for analyzing communication patterns from emails."""
        # Create concise summaries for pattern analysis
        concise_summaries = []
        for email in email_summaries[:30]:  # Limit to 30 most recent emails
            concise_summaries.append({
                'sender': email.get('sender', 'Unknown'),
                'date': email.get('date', ''),
                'subject': email.get('subject', '')[:100],
                'is_unread': email.get('is_unread', False)
            })
        
        # Include previous patterns if available
        previous_patterns_text = ""
        if previous_insights and 'communication_patterns' in previous_insights and previous_insights['communication_patterns']:
            previous_patterns_text = f"""
            IMPORTANT: Here are the communication patterns identified from previous email analysis. 
            Build upon and update this information with the new email data:
            {json.dumps(previous_insights['communication_patterns'], indent=2)}
            """
        
        return f"""
        Analyze the following email summaries from {user_email} to identify communication patterns.
        
        {previous_patterns_text}
        
        Email data (showing sender, date, subject, and read status):
        {json.dumps(concise_summaries, indent=2)}
        
        Provide a comprehensive analysis of communication patterns in JSON format with the following structure:
        {{
            "communication_patterns": {{
                "most_frequent_contacts": [
                    {{
                        "name": "Contact Name",
                        "email": "contact@example.com",
                        "frequency": "Number of interactions"
                    }}
                ],
                "busiest_times": {{
                    "days_of_week": ["Monday", "Thursday"],
                    "times_of_day": ["Morning", "Evening"]
                }},
                "response_patterns": {{
                    "average_response_time": "X hours/days",
                    "most_responsive_to": ["Person1", "Person2"],
                    "least_responsive_to": ["Person3", "Person4"]
                }},
                "communication_style": {{
                    "email_length": "Short/Medium/Long",
                    "formality_level": "Formal/Casual/Mixed",
                    "common_phrases": ["Phrase1", "Phrase2"]
                }}
            }}
        }}
        
        If there are patterns in both the previous analysis and the new emails, merge the information to create a more comprehensive understanding of communication habits over time.
        """
    
    def _create_actions_prompt(self, user_email: str, email_summaries: List[Dict], previous_insights: Dict[str, Any] = None) -> str:
        """Create a prompt for identifying action items from emails."""
        # Create concise summaries focusing on actionable content
        concise_summaries = []
        for email in email_summaries[:30]:  # Limit to 30 most recent emails
            concise_summaries.append({
                'subject': email.get('subject', '')[:100],
                'sender': email.get('sender', 'Unknown'),
                'date': email.get('date', ''),
                'snippet': email.get('body', '')[:300] if 'body' in email else ''  # Slightly longer for action items
            })
        
        # Include previous action items if available
        previous_actions_text = ""
        if previous_insights and 'action_items' in previous_insights and previous_insights['action_items']:
            previous_actions_text = f"""
            IMPORTANT: Here are the action items identified from previous email analysis. 
            Build upon and update this information with the new email data, noting which items may have been completed:
            {json.dumps(previous_insights['action_items'], indent=2)}
            """
        
        return f"""
        Analyze the following email summaries from {user_email} to identify action items and tasks.
        
        {previous_actions_text}
        
        Email data (showing sender, subject, date, and brief snippet):
        {json.dumps(concise_summaries, indent=2)}
        
        Provide a comprehensive list of action items in JSON format with the following structure:
        {{
            "action_items": [
                {{
                    "description": "Brief description of the action item",
                    "due_date": "Due date if specified (or null)",
                    "priority": "High/Medium/Low",
                    "related_to": "Person or project related to this action",
                    "status": "Pending/In Progress/Completed"
                }}
            ]
        }}
        
        Include only clear action items where I need to take action. Prioritize recent and urgent items.
        For action items that appear in both the previous list and the new emails, update their status and details based on the latest information.
        """
    
    def _create_info_prompt(self, user_email: str, email_summaries: List[Dict], previous_insights: Dict[str, Any] = None) -> str:
        """Create a prompt for extracting important information from emails."""
        # Create concise summaries for important information
        concise_summaries = []
        for email in email_summaries[:30]:  # Limit to 30 most recent emails
            concise_summaries.append({
                'subject': email.get('subject', '')[:100],
                'sender': email.get('sender', 'Unknown'),
                'date': email.get('date', ''),
                'snippet': email.get('body', '')[:300] if 'body' in email else ''
            })
        
        # Include previous important information if available
        previous_info_text = ""
        if previous_insights and 'important_information' in previous_insights and previous_insights['important_information']:
            previous_info_text = f"""
            IMPORTANT: Here is the important information identified from previous email analysis. 
            Build upon and update this information with the new email data:
            {json.dumps(previous_insights['important_information'], indent=2)}
            """
        
        return f"""
        Analyze the following email summaries from {user_email} to extract important information.
        
        {previous_info_text}
        
        Email data (showing sender, subject, date, and brief snippet):
        {json.dumps(concise_summaries, indent=2)}
        
        Provide a comprehensive list of important information in JSON format with the following structure:
        {{
            "important_information": [
                {{
                    "topic": "Brief topic or category",
                    "details": "Detailed information",
                    "source": "Person or organization this came from",
                    "date_received": "When this information was received",
                    "relevance": "Why this information is important"
                }}
            ]
        }}
        
        Focus on extracting key facts, announcements, decisions, or other noteworthy information.
        If a topic appears in both the previous information and the new emails, merge the details to create a more complete understanding of that topic.
        """
    
    def _get_structured_response(self, user_email: str, prompt: str, expected_key: str = None, days_back: int = 30) -> Dict[str, Any]:
        """Get a structured response from Claude based on the provided prompt.
        
        Args:
            user_email: The email of the user for context
            prompt: The prompt to send to Claude
            expected_key: The expected key in the response JSON
            days_back: Number of days back to analyze
            
        Returns:
            Dict containing the structured response from Claude
        """
        try:
            # Add system instruction to format response as JSON
            system_prompt = f"""You are an expert email analyst for {user_email}.
            
            Analyze the email data provided in the prompt to extract insights.
            Focus on emails from the past {days_back} days when available.
            
            Always respond with well-structured JSON data as requested in the prompt.
            Do not include any explanatory text outside the JSON structure.
            """
            
            # Send to Claude
            try:
                # Try the new Anthropic SDK interface
                response = self.claude_client.messages.create(
                    model="claude-3-opus-20240229",
                    max_tokens=4000,
                    temperature=0.2,
                    system=system_prompt,
                    messages=[{"role": "user", "content": prompt}]
                )
                assistant_response = response.content[0].text
            except AttributeError:
                # Fallback for older SDK versions
                logger.info("Using fallback Claude client interface")
                response = self.claude_client.completions.create(
                    model="claude-3-opus-20240229",
                    max_tokens=4000,
                    temperature=0.2,
                    system=system_prompt,
                    prompt=prompt
                )
                assistant_response = response.completion
            
            # Try to parse the response as JSON
            try:
                # Clean the response - remove markdown code blocks if present
                if assistant_response.startswith("```json"):
                    assistant_response = assistant_response.strip("```json").strip("```").strip()
                elif assistant_response.startswith("```"):
                    assistant_response = assistant_response.strip("```").strip()
                
                # Try to extract JSON from the response
                # First, try to parse the entire response as JSON
                try:
                    structured_response = json.loads(assistant_response)
                except json.JSONDecodeError:
                    # If that fails, try to find JSON in the response
                    import re
                    json_match = re.search(r'({.*})', assistant_response, re.DOTALL)
                    if json_match:
                        structured_response = json.loads(json_match.group(1))
                    else:
                        # For other JSON parsing errors
                        logger.error(f"Failed to parse Claude response as JSON: {assistant_response[:100]}...")
                        return {expected_key: [] if expected_key and expected_key != "communication_patterns" else {}} if expected_key else {"error": "Failed to parse response as JSON"}
                
                # Validate that the expected key is present
                if expected_key and expected_key not in structured_response:
                    logger.warning(f"Expected key '{expected_key}' not found in Claude's response")
                    structured_response[expected_key] = [] if expected_key != "communication_patterns" else {}
                
                return structured_response
            except Exception as e:
                logger.error(f"Error processing Claude response: {str(e)}")
                return {expected_key: [] if expected_key and expected_key != "communication_patterns" else {}} if expected_key else {"error": f"Error processing response: {str(e)}"}
                
        except Exception as e:
            logger.error(f"Error getting structured response: {str(e)}")
            return {expected_key: [] if expected_key and expected_key != "communication_patterns" else {}} if expected_key else {"error": str(e)}
    
    def scan_urgent_emails(self, user_email: str, access_token: str, hours_back: int = 24) -> Dict[str, Any]:
        """
        Scan recent emails for urgent items requiring attention.
        
        Args:
            user_email: The email of the user whose emails to scan
            access_token: OAuth access token for Gmail API
            hours_back: Number of hours back to scan (default: 24)
            
        Returns:
            Dict containing urgent emails and action items
        """
        logger.info(f"Scanning urgent emails from last {hours_back} hours for {user_email}")
        
        try:
            # Validate we have an access token
            if not access_token:
                logger.error(f"No access token provided for {user_email}")
                return {
                    "status": "error",
                    "message": "No access token provided for Gmail API",
                    "urgent_emails": []
                }
                
            # Initialize Gmail connector with the access token
            gmail = GmailConnector(access_token)
            
            # Test the connection
            if not gmail.test_connection():
                logger.error(f"Failed to connect to Gmail API for {user_email}")
                return {
                    "status": "error",
                    "message": "Failed to connect to Gmail API",
                    "urgent_emails": []
                }
            
            # Calculate days back from hours (needed for Gmail API call)
            days_back = max(1, int(hours_back / 24) + 1)  # At least 1 day, rounded up
            
            # Fetch real emails using the Gmail API
            logger.info(f"Fetching emails from Gmail API for {user_email} from last {hours_back} hours")
            email_summaries = gmail.get_recent_emails(days_back=days_back, max_results=50)
            
            if not email_summaries:
                logger.warning(f"No emails found for {user_email} in the last {days_back} days")
                return {
                    "status": "success",
                    "message": "No emails found in the specified time period",
                    "urgent_emails": []
                }
            
            # Filter emails to only include those from the last X hours
            recent_time = datetime.now() - timedelta(hours=hours_back)
            recent_emails = []
            
            for email in email_summaries:
                try:
                    # Parse the email date
                    email_date_str = email.get('date', '')
                    if email_date_str:
                        # Parse the date string (this is a simplification, might need adjustment)
                        email_date = datetime.strptime(email_date_str[:25], '%a, %d %b %Y %H:%M:%S')
                        if email_date > recent_time:
                            recent_emails.append(email)
                except Exception as e:
                    # If date parsing fails, include the email to be safe
                    logger.warning(f"Error parsing email date: {str(e)}")
                    recent_emails.append(email)
            
            logger.info(f"Found {len(recent_emails)} emails in the last {hours_back} hours")
            
            # Create a prompt for Claude to identify urgent emails
            prompt = f"""
            Please scan the following emails from the last {hours_back} hours and identify any urgent items that require my attention.
            
            Consider the following as potentially urgent:
            1. Emails marked as high priority
            2. Emails with urgent language in the subject or body
            3. Emails from key stakeholders (managers, executives, important clients)
            4. Emails mentioning deadlines within the next 48 hours
            5. Emails that are part of a rapid back-and-forth thread
            
            For each urgent email, provide:
            1. The sender and subject
            2. A brief summary of the content
            3. Why it's considered urgent
            4. Recommended action (if any)
            
            Email data:
            {json.dumps(recent_emails, indent=2)}
            
            Format the response as structured JSON with an array of "urgent_emails" objects, each containing
            "sender", "subject", "summary", "urgency_reason", and "recommended_action".
            """
            
            # Send the prompt to Claude using our structured response method
            response = self._get_structured_response(user_email, prompt, "urgent_emails", hours_back)
            
            logger.info(f"Successfully scanned urgent emails for {user_email}")
            return {
                "status": "success",
                "message": "Urgent email scan completed",
                "urgent_emails": response.get("urgent_emails", [])
            }
        except Exception as e:
            logger.error(f"Error scanning urgent emails for {user_email}: {str(e)}")
            return {
                "error": str(e),
                "status": "failed",
                "message": "Failed to scan urgent emails",
                "urgent_emails": []
            }
    
    def analyze_person(self, user_email: str, contact_email: str, access_token: str = None, days_back: int = 30) -> Dict[str, Any]:
        """
        Analyze email interactions with a specific person to build a profile.
        
        Args:
            user_email: The email of the user
            contact_email: The email of the contact to analyze
            access_token: OAuth access token for Gmail API
            days_back: Number of days back to analyze (default: 30)
            
        Returns:
            Dict containing analysis of the relationship with this person
        """
        logger.info(f"Analyzing person {contact_email} for {user_email}")
        
        try:
            # Validate we have an access token
            if not access_token:
                logger.error(f"No access token provided for {user_email}")
                return {
                    "status": "error",
                    "message": "No access token provided for Gmail API",
                    "contact_name": "",
                    "interaction_frequency": "",
                    "response_patterns": "",
                    "common_topics": [],
                    "sentiment_analysis": "",
                    "action_items": [],
                    "relationship_context": "",
                    "last_contact_date": ""
                }
                
            # Initialize Gmail connector with the access token
            gmail = GmailConnector(access_token)
            
            # Test the connection
            if not gmail.test_connection():
                logger.error(f"Failed to connect to Gmail API for {user_email}")
                return {
                    "status": "error",
                    "message": "Failed to connect to Gmail API",
                    "contact_name": "",
                    "interaction_frequency": "",
                    "response_patterns": "",
                    "common_topics": [],
                    "sentiment_analysis": "",
                    "action_items": [],
                    "relationship_context": "",
                    "last_contact_date": ""
                }
            
            # Fetch real emails using the Gmail API
            logger.info(f"Fetching emails from Gmail API for {user_email} related to {contact_email}")
            # Get emails from the last N days
            email_summaries = gmail.get_recent_emails(days_back=days_back, max_results=100)
            
            # Filter emails to only include those involving the contact
            contact_emails = []
            for email in email_summaries:
                if contact_email.lower() in email.get('sender', '').lower() or contact_email.lower() in email.get('to', '').lower():
                    contact_emails.append(email)
            
            if not contact_emails:
                logger.warning(f"No emails found between {user_email} and {contact_email} in the last {days_back} days")
                return {
                    "status": "warning",
                    "message": f"No emails found with {contact_email} in the last {days_back} days",
                    "contact_name": "",
                    "interaction_frequency": "None in the analyzed period",
                    "response_patterns": "N/A",
                    "common_topics": [],
                    "sentiment_analysis": "N/A",
                    "action_items": [],
                    "relationship_context": "No recent interactions",
                    "last_contact_date": "None in the analyzed period"
                }
            
            logger.info(f"Found {len(contact_emails)} emails between {user_email} and {contact_email}")
            
            # Create a prompt for Claude to analyze interactions with this person
            prompt = f"""
            Please analyze my email interactions with {contact_email} and provide a comprehensive profile.
            
            Include:
            1. Interaction frequency: How often we communicate and patterns over time
            2. Response times: How quickly they respond to me and vice versa
            3. Topics: Common subjects and projects we discuss
            4. Sentiment: The general tone and sentiment of our communications
            5. Action items: Any pending items or follow-ups with this person
            6. Relationship context: Their role, organization, and our relationship history
            
            Analyze the following email data:
            {json.dumps(contact_emails, indent=2)}
            
            Format the response as structured JSON with the following keys:
            "contact_name", "interaction_frequency", "response_patterns", "common_topics", 
            "sentiment_analysis", "action_items", "relationship_context", "last_contact_date"
            """
            
            # Send the prompt to Claude
            response = self._get_structured_response(user_email, prompt)
            logger.info(f"Successfully analyzed person {contact_email} for {user_email}")
            return response
        except Exception as e:
            logger.error(f"Error analyzing person {contact_email} for {user_email}: {str(e)}")
            return {
                "error": str(e),
                "status": "failed",
                "message": f"Failed to analyze person {contact_email}"
            }
    
    def identify_key_contacts(self, user_email: str, access_token: str = None, days_back: int = 30) -> Dict[str, Any]:
        """
        Identify and analyze key contacts from email communications.
        
        Args:
            user_email: The email of the user
            access_token: OAuth access token for Gmail API
            days_back: Number of days back to analyze (default: 30)
            
        Returns:
            Dict containing key contacts and relationship insights
        """
        logger.info(f"Identifying key contacts for {user_email}")
        
        try:
            # Validate we have an access token
            if not access_token:
                logger.error(f"No access token provided for {user_email}")
                return {
                    "status": "error",
                    "message": "No access token provided for Gmail API",
                    "key_contacts": []
                }
                
            # Initialize Gmail connector with the access token
            gmail = GmailConnector(access_token)
            
            # Test the connection
            if not gmail.test_connection():
                logger.error(f"Failed to connect to Gmail API for {user_email}")
                return {
                    "status": "error",
                    "message": "Failed to connect to Gmail API",
                    "key_contacts": []
                }
            
            # Fetch real emails using the Gmail API
            logger.info(f"Fetching emails from Gmail API for {user_email}")
            email_summaries = gmail.get_recent_emails(days_back=days_back, max_results=100)
            
            if not email_summaries:
                logger.warning(f"No emails found for {user_email} in the last {days_back} days")
                return {
                    "status": "warning",
                    "message": "No emails found in the analyzed period",
                    "key_contacts": []
                }
            
            logger.info(f"Successfully fetched {len(email_summaries)} emails for contact analysis")
            
            # Create a prompt for Claude to identify key contacts
            prompt = f"""
            Please analyze the following email communications from the last {days_back} days and identify my key contacts.
            
            For each key contact, provide:
            1. Their name and email address
            2. Their role or organization (if apparent)
            3. The frequency of our communication
            4. The nature of our relationship (professional, personal, etc.)
            5. Common topics or projects we discuss
            
            Email data:
            {json.dumps(email_summaries, indent=2)}
            
            Format the response as structured JSON with an array of "key_contacts" objects, 
            each containing "name", "email", "role", "communication_frequency", "relationship_type", and "common_topics"
            """
            
            # Send the prompt to Claude
            response = self._get_structured_response(user_email, prompt, "key_contacts", days_back)
            logger.info(f"Successfully identified key contacts for {user_email}")
            return {
                "status": "success",
                "message": "Key contacts identified successfully",
                "key_contacts": response.get("key_contacts", [])
            }
        except Exception as e:
            logger.error(f"Error identifying key contacts for {user_email}: {str(e)}")
            return {
                "error": str(e),
                "status": "failed",
                "message": "Failed to identify key contacts",
                "key_contacts": []
            }
