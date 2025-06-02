"""
Email Intelligence Module using Claude for email analysis with data from ImprovedGmailConnector.

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

from backend.integrations.gmail.gmail_connector_improved import ImprovedGmailConnector
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
    
    def analyze_recent_emails(self, user_email: str, token_data: Dict[str, Any] = None, days_back: int = 30, previous_insights: Dict[str, Any] = None, structured_knowledge: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze emails from the last N days to extract business intelligence using multiple targeted prompts.
        Uses the Gmail API to fetch real emails via ImprovedGmailConnector.
        
        Args:
            user_email: The email of the user whose emails to analyze
            token_data: Full OAuth token data including access_token, refresh_token, etc.
            days_back: Number of days back to analyze (default: 30)
            previous_insights: Previously generated insights to build upon (default: None)
            structured_knowledge: Structured knowledge to consider in analysis (default: None)
            
        Returns:
            Dict containing analysis results with key insights from multiple specialized prompts
        """
        logger.info(f"Analyzing emails from last {days_back} days for {user_email}")
        analysis_type = "incremental" if previous_insights else "full"
        logger.info(f"Performing {analysis_type} analysis")
        
        try:
            # Validate we have token data
            if not token_data or 'access_token' not in token_data:
                logger.error(f"No token data provided for {user_email}")
                return {
                    "status": "error",
                    "message": "No token data provided for Gmail API",
                    "key_relationships": [],
                    "active_projects": [],
                    "communication_patterns": {},
                    "action_items": [],
                    "important_information": []
                }
                
            # Initialize Gmail connector with the full token data
            gmail = ImprovedGmailConnector(token_data)
            
            # Test the connection
            connection_test = gmail.test_connection()
            if not connection_test.get('success', False):
                logger.error(f"Failed to connect to Gmail API for {user_email}: {connection_test.get('error', 'Unknown error')}")
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
            result = gmail.get_recent_emails(days_back=days_back, max_results=50)  # Reduced from 100 to 50
            
            if not result.get('success', False):
                logger.error(f"Failed to fetch emails: {result.get('error', 'Unknown error')}")
                return {
                    "status": "error",
                    "message": f"Failed to fetch emails: {result.get('error', 'Unknown error')}",
                    "key_relationships": [],
                    "active_projects": [],
                    "communication_patterns": {},
                    "action_items": [],
                    "important_information": []
                }
                
            email_summaries = result.get('emails', [])
            
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
            
            # Log structured knowledge if available
            if structured_knowledge:
                projects_count = len(structured_knowledge.get('projects', []))
                goals_count = len(structured_knowledge.get('goals', []))
                knowledge_files_count = len(structured_knowledge.get('knowledge_files', []))
                logger.info(f"Using structured knowledge: {projects_count} projects, {goals_count} goals, {knowledge_files_count} knowledge files")
            
            # Get relationships analysis
            relationships_prompt = self._create_relationships_prompt(user_email, email_summaries, previous_insights, structured_knowledge)
            relationships_response = self._get_structured_response(user_email, relationships_prompt, "key_relationships", days_back)
            combined_results["key_relationships"] = relationships_response.get("key_relationships", [])
            
            # Get projects analysis
            projects_prompt = self._create_projects_prompt(user_email, email_summaries, previous_insights, structured_knowledge)
            projects_response = self._get_structured_response(user_email, projects_prompt, "active_projects", days_back)
            combined_results["active_projects"] = projects_response.get("active_projects", [])
            
            # Get communication patterns analysis
            patterns_prompt = self._create_patterns_prompt(user_email, email_summaries, previous_insights, structured_knowledge)
            patterns_response = self._get_structured_response(user_email, patterns_prompt, "communication_patterns", days_back)
            combined_results["communication_patterns"] = patterns_response.get("communication_patterns", {})
            
            # Get action items analysis
            actions_prompt = self._create_actions_prompt(user_email, email_summaries, previous_insights, structured_knowledge)
            actions_response = self._get_structured_response(user_email, actions_prompt, "action_items", days_back)
            combined_results["action_items"] = actions_response.get("action_items", [])
            
            # Get important information analysis
            info_prompt = self._create_info_prompt(user_email, email_summaries, previous_insights, structured_knowledge)
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
    
    def _create_relationships_prompt(self, user_email: str, email_summaries: List[Dict], previous_insights: Dict[str, Any] = None, structured_knowledge: Dict[str, Any] = None) -> str:
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
        
        # Include structured knowledge about projects and goals if available
        structured_knowledge_text = ""
        if structured_knowledge:
            projects = structured_knowledge.get('projects', [])
            goals = structured_knowledge.get('goals', [])
            
            if projects or goals:
                structured_knowledge_text = "IMPORTANT: Consider the following user-defined projects and goals when analyzing relationships:\n"
                
                if projects:
                    structured_knowledge_text += "\nProjects:\n"
                    for project in projects:
                        structured_knowledge_text += f"- {project.get('name')}: {project.get('description')}\n"
                        if project.get('stakeholders'):
                            structured_knowledge_text += f"  Stakeholders: {', '.join(project.get('stakeholders'))}\n"
                
                if goals:
                    structured_knowledge_text += "\nGoals:\n"
                    for goal in goals:
                        structured_knowledge_text += f"- {goal.get('name')}: {goal.get('description')}\n"
        
        # Construct the full prompt
        prompt = f"""
        You are an expert relationship analyst for {user_email}. Your task is to analyze their recent email communications and identify key relationships.
        
        For each key relationship, provide:
        1. Name of the person
        2. Their email address if available
        3. Their organization/company if available
        4. Their role or title if available
        5. The nature of the relationship (colleague, client, vendor, friend, etc.)
        6. The apparent importance of this relationship based on frequency and content of communications
        7. Key topics discussed with this person
        8. Any action items or follow-ups pending with this person
        
        {previous_relationships_text}
        
        {structured_knowledge_text}
        
        Here are the recent email communications to analyze:
        {json.dumps(concise_summaries, indent=2)}
        
        Provide your analysis in the following JSON format:
        {{
            "key_relationships": [
                {{
                    "name": "Person's full name",
                    "email": "email@example.com",
                    "organization": "Company name",
                    "role": "Their role or title",
                    "relationship_type": "Type of relationship",
                    "importance": "High/Medium/Low",
                    "key_topics": ["Topic 1", "Topic 2"],
                    "pending_actions": ["Action 1", "Action 2"]
                }}
            ]
        }}
        
        Only include people who appear to be actual relationships, not automated systems or mailing lists.
        Focus on quality over quantity - identify the 5-10 most important relationships.
        """
        
        return prompt
    
    def _create_projects_prompt(self, user_email: str, email_summaries: List[Dict], previous_insights: Dict[str, Any] = None, structured_knowledge: Dict[str, Any] = None) -> str:
        """Create a prompt for analyzing active projects from emails."""
        # Create a more concise summary focusing on project-related information
        concise_summaries = []
        for email in email_summaries[:30]:  # Limit to 30 most recent emails
            concise_summaries.append({
                'sender': email.get('sender', 'Unknown'),
                'subject': email.get('subject', '')[:100],  # Limit subject length
                'date': email.get('date', ''),
                'snippet': email.get('body', '')[:300] if 'body' in email else ''  # Use longer snippet for projects
            })
        
        # Include previous projects if available
        previous_projects_text = ""
        if previous_insights and 'active_projects' in previous_insights and previous_insights['active_projects']:
            previous_projects_text = f"""
            IMPORTANT: Here are the active projects identified from previous email analysis. 
            Build upon and update this information with the new email data:
            {json.dumps(previous_insights['active_projects'], indent=2)}
            """
        
        # Include structured knowledge about projects if available
        structured_knowledge_text = ""
        if structured_knowledge and structured_knowledge.get('projects'):
            projects = structured_knowledge.get('projects', [])
            structured_knowledge_text = "IMPORTANT: Consider these user-defined projects when analyzing emails:\n"
            for project in projects:
                structured_knowledge_text += f"- {project.get('name')}: {project.get('description')}\n"
                if project.get('stakeholders'):
                    structured_knowledge_text += f"  Stakeholders: {', '.join(project.get('stakeholders'))}\n"
                if project.get('status'):
                    structured_knowledge_text += f"  Status: {project.get('status')}\n"
        
        # Construct the full prompt
        prompt = f"""
        You are an expert project analyst for {user_email}. Your task is to analyze their recent email communications and identify active projects or initiatives.
        
        For each active project, provide:
        1. Project name or identifier
        2. Brief description of the project
        3. Current status (if discernible)
        4. Key stakeholders involved
        5. Recent developments or updates
        6. Upcoming deadlines or milestones (if mentioned)
        7. Any blockers or issues mentioned
        
        {previous_projects_text}
        
        {structured_knowledge_text}
        
        Here are the recent email communications to analyze:
        {json.dumps(concise_summaries, indent=2)}
        
        Provide your analysis in the following JSON format:
        {{
            "active_projects": [
                {{
                    "name": "Project name",
                    "description": "Brief description",
                    "status": "In progress/Completed/On hold/etc.",
                    "stakeholders": ["Person 1", "Person 2"],
                    "recent_updates": ["Update 1", "Update 2"],
                    "upcoming_deadlines": ["Deadline 1", "Deadline 2"],
                    "blockers": ["Blocker 1", "Blocker 2"]
                }}
            ]
        }}
        
        Only include projects that appear to be currently active or recently mentioned.
        Focus on quality over quantity - identify the 3-7 most significant projects.
        """
        
        return prompt
    
    def _create_patterns_prompt(self, user_email: str, email_summaries: List[Dict], previous_insights: Dict[str, Any] = None, structured_knowledge: Dict[str, Any] = None) -> str:
        """Create a prompt for analyzing communication patterns from emails."""
        # Extract sender and date information for pattern analysis
        sender_data = []
        for email in email_summaries:
            sender = email.get('sender', 'Unknown')
            date = email.get('date', '')
            sender_data.append({'sender': sender, 'date': date})
        
        # Include previous patterns if available
        previous_patterns_text = ""
        if previous_insights and 'communication_patterns' in previous_insights and previous_insights['communication_patterns']:
            previous_patterns_text = f"""
            IMPORTANT: Here are the communication patterns identified from previous email analysis. 
            Build upon and update this information with the new email data:
            {json.dumps(previous_insights['communication_patterns'], indent=2)}
            """
        
        # Construct the full prompt
        prompt = f"""
        You are an expert communication analyst for {user_email}. Your task is to analyze their recent email communications and identify patterns.
        
        Analyze the following aspects of communication:
        1. Most frequent contacts
        2. Time patterns (time of day, day of week)
        3. Response rates and times
        4. Communication volume trends
        5. Common topics or themes
        
        {previous_patterns_text}
        
        Here is the sender and date information from recent emails:
        {json.dumps(sender_data, indent=2)}
        
        Provide your analysis in the following JSON format:
        {{
            "communication_patterns": {{
                "frequent_contacts": [
                    {{"name": "Contact name", "frequency": "Number or description"}}
                ],
                "time_patterns": [
                    {{"pattern": "Description of pattern", "observation": "Details"}}
                ],
                "response_patterns": [
                    {{"pattern": "Description of pattern", "observation": "Details"}}
                ],
                "volume_trends": [
                    {{"trend": "Description of trend", "observation": "Details"}}
                ],
                "common_themes": [
                    {{"theme": "Theme name", "frequency": "Description"}}
                ]
            }}
        }}
        
        Focus on identifying meaningful patterns rather than listing every detail.
        """
        
        return prompt
    
    def _create_actions_prompt(self, user_email: str, email_summaries: List[Dict], previous_insights: Dict[str, Any] = None, structured_knowledge: Dict[str, Any] = None) -> str:
        """Create a prompt for extracting action items from emails."""
        # Create a more concise summary focusing on potential action items
        concise_summaries = []
        for email in email_summaries[:30]:  # Limit to 30 most recent emails
            concise_summaries.append({
                'sender': email.get('sender', 'Unknown'),
                'subject': email.get('subject', '')[:100],  # Limit subject length
                'date': email.get('date', ''),
                'snippet': email.get('body', '')[:300] if 'body' in email else ''  # Use longer snippet for actions
            })
        
        # Include previous action items if available
        previous_actions_text = ""
        if previous_insights and 'action_items' in previous_insights and previous_insights['action_items']:
            previous_actions_text = f"""
            IMPORTANT: Here are the action items identified from previous email analysis. 
            Some may have been completed. Update this list with new action items and remove completed ones:
            {json.dumps(previous_insights['action_items'], indent=2)}
            """
        
        # Construct the full prompt
        prompt = f"""
        You are an expert assistant for {user_email}. Your task is to analyze their recent email communications and identify action items, tasks, and follow-ups.
        
        For each action item, provide:
        1. Description of the task or action required
        2. Who requested it (if applicable)
        3. Due date or deadline (if mentioned)
        4. Priority level (if discernible)
        5. Related project or context
        
        {previous_actions_text}
        
        Here are the recent email communications to analyze:
        {json.dumps(concise_summaries, indent=2)}
        
        Provide your analysis in the following JSON format:
        {{
            "action_items": [
                {{
                    "description": "Description of the action item",
                    "requester": "Person who requested it",
                    "due_date": "Deadline if available",
                    "priority": "High/Medium/Low",
                    "context": "Related project or context"
                }}
            ]
        }}
        
        Only include clear action items that require follow-up.
        Focus on quality over quantity - identify the most important and urgent items.
        """
        
        return prompt
    
    def _create_info_prompt(self, user_email: str, email_summaries: List[Dict], previous_insights: Dict[str, Any] = None, structured_knowledge: Dict[str, Any] = None) -> str:
        """Create a prompt for extracting important information from emails."""
        # Create a more concise summary focusing on information content
        concise_summaries = []
        for email in email_summaries[:30]:  # Limit to 30 most recent emails
            concise_summaries.append({
                'sender': email.get('sender', 'Unknown'),
                'subject': email.get('subject', '')[:100],  # Limit subject length
                'date': email.get('date', ''),
                'snippet': email.get('body', '')[:300] if 'body' in email else ''  # Use longer snippet for info
            })
        
        # Include previous important information if available
        previous_info_text = ""
        if previous_insights and 'important_information' in previous_insights and previous_insights['important_information']:
            previous_info_text = f"""
            IMPORTANT: Here is important information identified from previous email analysis. 
            Some may no longer be relevant. Update this list with new information and remove outdated items:
            {json.dumps(previous_insights['important_information'], indent=2)}
            """
        
        # Construct the full prompt
        prompt = f"""
        You are an expert information analyst for {user_email}. Your task is to analyze their recent email communications and identify important information, announcements, decisions, and updates.
        
        For each piece of important information, provide:
        1. Brief description of the information
        2. Source of the information (who shared it)
        3. Date it was shared
        4. Category (announcement, decision, update, etc.)
        5. Relevance or impact
        
        {previous_info_text}
        
        Here are the recent email communications to analyze:
        {json.dumps(concise_summaries, indent=2)}
        
        Provide your analysis in the following JSON format:
        {{
            "important_information": [
                {{
                    "description": "Description of the information",
                    "source": "Person who shared it",
                    "date": "Date it was shared",
                    "category": "Type of information",
                    "relevance": "Why it's important"
                }}
            ]
        }}
        
        Only include truly important information that has ongoing relevance.
        Focus on quality over quantity - identify the most significant items.
        """
        
        return prompt
    
    def _get_structured_response(self, user_email: str, prompt: str, key_field: str, days_back: int) -> Dict[str, Any]:
        """
        Get a structured response from Claude for a specific analysis prompt.
        
        Args:
            user_email: The email of the user
            prompt: The analysis prompt to send to Claude
            key_field: The key field expected in the response
            days_back: Number of days back being analyzed
            
        Returns:
            Dict containing the structured response
        """
        try:
            logger.info(f"Getting {key_field} analysis for {user_email}")
            
            # Set up system prompt
            system_prompt = f"""
            You are an AI assistant specialized in analyzing email data for business intelligence.
            Your task is to analyze the provided email data and extract structured insights.
            
            IMPORTANT GUIDELINES:
            1. ALWAYS respond in valid JSON format with the structure exactly as requested
            2. Do not include any explanations or text outside the JSON structure
            3. If you're unsure about something, make a reasonable inference rather than omitting information
            4. Focus on quality over quantity in your analysis
            5. Ensure all field names match exactly what was requested
            """
            
            # Get response from Claude
            response = self.claude_client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=4000,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # Extract and parse JSON from response
            response_text = response.content[0].text
            
            # Clean up response text to ensure it's valid JSON
            # Remove any markdown code block markers
            response_text = response_text.replace("```json", "").replace("```", "").strip()
            
            # Parse JSON
            try:
                parsed_response = json.loads(response_text)
                
                # Validate that the expected key field is present
                if key_field not in parsed_response:
                    logger.warning(f"Expected key '{key_field}' not found in response for {user_email}")
                    parsed_response[key_field] = [] if key_field != "communication_patterns" else {}
                
                return parsed_response
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response for {key_field} analysis: {str(e)}")
                logger.error(f"Response text: {response_text[:500]}...")
                
                # Return empty result with the expected structure
                if key_field == "communication_patterns":
                    return {key_field: {}}
                else:
                    return {key_field: []}
                
        except Exception as e:
            logger.error(f"Error getting {key_field} analysis for {user_email}: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Return empty result with the expected structure
            if key_field == "communication_patterns":
                return {key_field: {}}
            else:
                return {key_field: []}
