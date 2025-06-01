"""
Entity Extraction Service for extracting entities and relationships from emails.
Uses Claude API to extract entities and relationships from email content.
"""

import os
import logging
import json
import re
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from anthropic import Anthropic

logger = logging.getLogger(__name__)

class EntityExtractionService:
    """Service for extracting entities and relationships from emails"""
    
    def __init__(self, claude_client=None):
        """Initialize the Claude client"""
        self.claude_client = claude_client or Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
        logger.info("Initialized Entity Extraction Service with Claude API")
    
    def extract_entities_from_email(self, email_content: str, email_metadata: Optional[Dict] = None) -> Dict:
        """
        Extract entities from email content using Claude API
        
        Args:
            email_content: The content of the email
            email_metadata: Optional metadata about the email (sender, recipients, subject, date)
            
        Returns:
            Dictionary containing extracted entities and relationships
        """
        # Create a prompt for Claude to extract entities
        metadata_str = ""
        if email_metadata:
            metadata_str = f"""
            Email Metadata:
            - From: {email_metadata.get('from', 'Unknown')}
            - To: {email_metadata.get('to', 'Unknown')}
            - Subject: {email_metadata.get('subject', 'Unknown')}
            - Date: {email_metadata.get('date', 'Unknown')}
            """
        
        prompt = f"""
        Extract the following entities from this email:
        
        1. People (name and email if available)
        2. Companies/Organizations
        3. Projects/Initiatives mentioned
        4. Action items with deadlines (be specific about what needs to be done and when)
        5. Meetings with times and participants
        
        Also identify relationships between these entities, such as:
        - Person works at Company
        - Person is responsible for Task
        - Person is participating in Meeting
        - Project involves Person
        
        Format the response as JSON with these categories. Be precise and extract only what is explicitly mentioned in the email.
        
        {metadata_str}
        
        Email Content:
        {email_content}
        """
        
        # Call Claude API
        logger.info("Calling Claude API to extract entities from email")
        try:
            response = self.claude_client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=1500,
                temperature=0,
                system="You are an expert at extracting structured information from emails. You identify people, organizations, tasks, meetings, and their relationships. You respond only with well-formatted JSON.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Parse the response to extract the JSON
            logger.info("Received response from Claude API, parsing JSON")
            return self._parse_claude_response(response.content)
            
        except Exception as e:
            logger.error(f"Error calling Claude API: {str(e)}")
            return {
                "people": [],
                "companies": [],
                "projects": [],
                "action_items": [],
                "meetings": [],
                "relationships": []
            }
    
    def _parse_claude_response(self, response_content: str) -> Dict:
        """
        Parse the Claude API response to extract the JSON
        
        Args:
            response_content: The content of the Claude API response
            
        Returns:
            Dictionary containing extracted entities and relationships
        """
        try:
            # Try to find JSON in the response using regex
            json_match = re.search(r'```json\n(.*?)\n```', response_content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # If no JSON block is found, try to use the whole response
                json_str = response_content
            
            # Parse the JSON
            entities = json.loads(json_str)
            logger.info(f"Successfully parsed entities: {len(entities.get('people', []))} people, {len(entities.get('action_items', []))} action items")
            return entities
            
        except Exception as e:
            logger.error(f"Error parsing Claude response: {str(e)}")
            logger.debug(f"Claude response: {response_content[:500]}...")
            
            # Return empty structure if parsing fails
            return {
                "people": [],
                "companies": [],
                "projects": [],
                "action_items": [],
                "meetings": [],
                "relationships": []
            }
    
    def extract_tasks_from_email(self, email_content: str, email_metadata: Optional[Dict] = None) -> List[Dict]:
        """
        Extract tasks from email content using Claude API
        
        Args:
            email_content: The content of the email
            email_metadata: Optional metadata about the email (sender, recipients, subject, date)
            
        Returns:
            List of tasks with descriptions, deadlines, and related entities
        """
        # Extract all entities first
        entities = self.extract_entities_from_email(email_content, email_metadata)
        
        # Process action items into tasks
        tasks = []
        for action_item in entities.get('action_items', []):
            task = {
                "id": str(uuid.uuid4()),
                "description": action_item.get('description', ''),
                "deadline": action_item.get('deadline'),
                "priority": action_item.get('priority', 'medium'),
                "source_type": "email",
                "source_id": email_metadata.get('id') if email_metadata else None,
                "source_snippet": action_item.get('context', ''),
                "related_people": [],
                "related_project": None,
                "created_at": datetime.utcnow().isoformat(),
            }
            
            # Find related people for this task
            for relationship in entities.get('relationships', []):
                if relationship.get('type') == 'responsible_for' and relationship.get('target') == action_item.get('id'):
                    # Find the person in the people list
                    for person in entities.get('people', []):
                        if person.get('id') == relationship.get('source'):
                            task['related_people'].append(person.get('email', person.get('name')))
                
                if relationship.get('type') == 'part_of' and relationship.get('source') == action_item.get('id'):
                    # Find the project in the projects list
                    for project in entities.get('projects', []):
                        if project.get('id') == relationship.get('target'):
                            task['related_project'] = project.get('name')
            
            tasks.append(task)
        
        logger.info(f"Extracted {len(tasks)} tasks from email")
        return tasks
