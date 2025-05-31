import anthropic
from typing import Dict, Optional
import os

class ClaudeClient:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is required")
        
        self.client = anthropic.Anthropic(api_key=api_key)
        self.conversation_history = {}  # Store by user_email
        self.max_history = 20  # Keep last 20 messages per user
    
    def send_message(self, user_email: str, message: str) -> str:
        """Send message to Claude with user context"""
        
        # Initialize conversation history for new users
        if user_email not in self.conversation_history:
            self.conversation_history[user_email] = []
        
        # Build system prompt with user context
        system_prompt = f"""You are a personalized AI assistant for {user_email}.

You have access to their:
- Gmail (use your native Gmail integration when they ask about emails)
- Google Calendar (use your native Calendar integration for scheduling questions)
- ClickUp tasks and projects (coming soon)

When users ask about:
- Emails: Use your Gmail integration to check their actual emails
- Calendar/Schedule: Use your Calendar integration to check their actual events  
- General questions: Provide helpful, conversational responses

Be conversational, helpful, and proactive. You can access their real data when relevant.
"""
        
        # Add user message to history
        self.conversation_history[user_email].append({
            "role": "user", 
            "content": message
        })
        
        try:
            # Send to Claude
            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=4000,
                system=system_prompt,
                messages=self.conversation_history[user_email]
            )
            
            assistant_response = response.content[0].text
            
            # Add response to history
            self.conversation_history[user_email].append({
                "role": "assistant",
                "content": assistant_response
            })
            
            # Trim history if too long
            if len(self.conversation_history[user_email]) > self.max_history:
                self.conversation_history[user_email] = self.conversation_history[user_email][-self.max_history:]
            
            return assistant_response
            
        except Exception as e:
            return f"I'm having trouble connecting right now. Error: {str(e)}"
    
    def clear_history(self, user_email: str):
        """Clear conversation history for a user"""
        if user_email in self.conversation_history:
            del self.conversation_history[user_email]
EOF