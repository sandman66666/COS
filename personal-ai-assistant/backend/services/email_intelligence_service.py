"""
Service layer for email intelligence operations.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from backend.core.claude_integration.email_intelligence import EmailIntelligence
from backend.models.database.email_insights import EmailInsight, UrgentEmailAlert, PersonProfile

logger = logging.getLogger(__name__)

class EmailIntelligenceService:
    def __init__(self, db: Session, claude_client):
        """
        Initialize the Email Intelligence Service.
        
        Args:
            db: Database session
            claude_client: Claude client instance
        """
        self.db = db
        self.email_intelligence = EmailIntelligence(claude_client)
    
    def run_business_intelligence_sync(self, user_email: str, token_data: Dict[str, Any], days_back: int = 30) -> Dict[str, Any]:
        """
        Run the business intelligence sync to analyze emails from the last N days.
        
        Args:
            user_email: The email of the user
            token_data: Full OAuth token data including access_token, refresh_token, etc.
            days_back: Number of days back to analyze
            
        Returns:
            Dict containing analysis results
        """
        logger.info(f"Running business intelligence sync for {user_email}")
        
        try:
            # Get analysis from Claude
            analysis = self.email_intelligence.analyze_recent_emails(user_email, token_data, days_back)
            
            # Save to database
            email_insight = EmailInsight(
                user_email=user_email,
                days_analyzed=days_back,
                key_relationships=analysis.get("key_relationships", {}),
                active_projects=analysis.get("active_projects", {}),
                communication_patterns=analysis.get("communication_patterns", {}),
                action_items=analysis.get("action_items", {}),
                important_information=analysis.get("important_information", {}),
                raw_response=str(analysis)
            )
            
            self.db.add(email_insight)
            self.db.commit()
            self.db.refresh(email_insight)
            
            logger.info(f"Business intelligence sync completed for {user_email}")
            return {"status": "success", "insight_id": email_insight.id, "data": analysis}
            
        except Exception as e:
            logger.error(f"Error in business intelligence sync for {user_email}: {str(e)}")
            self.db.rollback()
            return {"status": "error", "message": str(e)}
    
    def scan_for_urgent_emails(self, user_email: str, hours_back: int = 24) -> Dict[str, Any]:
        """
        Scan for urgent emails that need attention.
        
        Args:
            user_email: The email of the user
            hours_back: Number of hours back to scan
            
        Returns:
            Dict containing urgent email alerts
        """
        logger.info(f"Scanning for urgent emails for {user_email}")
        
        try:
            # Get urgent emails from Claude
            urgent_data = self.email_intelligence.scan_urgent_emails(user_email, hours_back)
            
            # Only create alert if there are urgent emails
            if urgent_data.get("urgent_emails") and len(urgent_data["urgent_emails"]) > 0:
                # Save to database
                alert = UrgentEmailAlert(
                    user_email=user_email,
                    hours_scanned=hours_back,
                    urgent_emails=urgent_data.get("urgent_emails", []),
                    priority_level=urgent_data.get("priority_level", "low"),
                    summary=urgent_data.get("summary", "")
                )
                
                self.db.add(alert)
                self.db.commit()
                self.db.refresh(alert)
                
                logger.info(f"Urgent email scan completed for {user_email}, found {len(urgent_data.get('urgent_emails', []))} urgent emails")
                return {"status": "success", "alert_id": alert.id, "data": urgent_data}
            else:
                logger.info(f"No urgent emails found for {user_email}")
                return {"status": "success", "message": "No urgent emails found", "data": urgent_data}
            
        except Exception as e:
            logger.error(f"Error in urgent email scan for {user_email}: {str(e)}")
            self.db.rollback()
            return {"status": "error", "message": str(e)}
    
    def update_person_profile(self, user_email: str, contact_email: str) -> Dict[str, Any]:
        """
        Create or update a profile for a person based on email interactions.
        
        Args:
            user_email: The email of the user
            contact_email: The email of the contact to analyze
            
        Returns:
            Dict containing the person profile
        """
        logger.info(f"Updating person profile for {contact_email}")
        
        try:
            # Get person analysis from Claude
            profile_data = self.email_intelligence.analyze_person(user_email, contact_email)
            
            # Check if profile already exists
            existing_profile = self.db.query(PersonProfile).filter(
                PersonProfile.user_email == user_email,
                PersonProfile.contact_email == contact_email
            ).first()
            
            if existing_profile:
                # Update existing profile
                existing_profile.contact_name = profile_data.get("contact_name", existing_profile.contact_name)
                existing_profile.interaction_frequency = profile_data.get("interaction_frequency", existing_profile.interaction_frequency)
                existing_profile.response_patterns = profile_data.get("response_patterns", existing_profile.response_patterns)
                existing_profile.common_topics = profile_data.get("common_topics", existing_profile.common_topics)
                existing_profile.sentiment_analysis = profile_data.get("sentiment_analysis", existing_profile.sentiment_analysis)
                existing_profile.action_items = profile_data.get("action_items", existing_profile.action_items)
                existing_profile.relationship_context = profile_data.get("relationship_context", existing_profile.relationship_context)
                
                if profile_data.get("last_contact_date"):
                    try:
                        existing_profile.last_contact_date = datetime.fromisoformat(profile_data["last_contact_date"])
                    except (ValueError, TypeError):
                        pass
                
                self.db.commit()
                self.db.refresh(existing_profile)
                profile_id = existing_profile.id
                
            else:
                # Create new profile
                last_contact_date = None
                if profile_data.get("last_contact_date"):
                    try:
                        last_contact_date = datetime.fromisoformat(profile_data["last_contact_date"])
                    except (ValueError, TypeError):
                        pass
                
                new_profile = PersonProfile(
                    user_email=user_email,
                    contact_email=contact_email,
                    contact_name=profile_data.get("contact_name", ""),
                    interaction_frequency=profile_data.get("interaction_frequency", {}),
                    response_patterns=profile_data.get("response_patterns", {}),
                    common_topics=profile_data.get("common_topics", {}),
                    sentiment_analysis=profile_data.get("sentiment_analysis", {}),
                    action_items=profile_data.get("action_items", {}),
                    relationship_context=profile_data.get("relationship_context", {}),
                    last_contact_date=last_contact_date
                )
                
                self.db.add(new_profile)
                self.db.commit()
                self.db.refresh(new_profile)
                profile_id = new_profile.id
            
            logger.info(f"Person profile updated for {contact_email}")
            return {"status": "success", "profile_id": profile_id, "data": profile_data}
            
        except Exception as e:
            logger.error(f"Error updating person profile for {contact_email}: {str(e)}")
            self.db.rollback()
            return {"status": "error", "message": str(e)}
    
    def update_key_contacts(self, user_email: str) -> Dict[str, Any]:
        """
        Identify and update profiles for key contacts.
        
        Args:
            user_email: The email of the user
            
        Returns:
            Dict containing key contacts data
        """
        logger.info(f"Updating key contacts for {user_email}")
        
        try:
            # Get key contacts from Claude
            contacts_data = self.email_intelligence.identify_key_contacts(user_email)
            
            # Process each key contact
            processed_contacts = []
            for contact in contacts_data.get("key_contacts", []):
                if contact.get("email"):
                    # Update or create profile for this contact
                    result = self.update_person_profile(user_email, contact["email"])
                    processed_contacts.append({
                        "email": contact["email"],
                        "name": contact.get("name", ""),
                        "profile_id": result.get("profile_id"),
                        "status": result.get("status")
                    })
            
            logger.info(f"Updated {len(processed_contacts)} key contacts for {user_email}")
            return {
                "status": "success", 
                "processed_contacts": processed_contacts,
                "key_contacts": contacts_data.get("key_contacts", [])
            }
            
        except Exception as e:
            logger.error(f"Error updating key contacts for {user_email}: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def get_latest_business_intelligence(self, user_email: str) -> Dict[str, Any]:
        """
        Get the latest business intelligence for a user.
        
        Args:
            user_email: The email of the user
            
        Returns:
            Dict containing the latest business intelligence
        """
        try:
            latest_insight = self.db.query(EmailInsight).filter(
                EmailInsight.user_email == user_email
            ).order_by(EmailInsight.created_at.desc()).first()
            
            if latest_insight:
                return {
                    "status": "success",
                    "insight_id": latest_insight.id,
                    "analysis_date": latest_insight.analysis_date,
                    "days_analyzed": latest_insight.days_analyzed,
                    "key_relationships": latest_insight.key_relationships,
                    "active_projects": latest_insight.active_projects,
                    "communication_patterns": latest_insight.communication_patterns,
                    "action_items": latest_insight.action_items,
                    "important_information": latest_insight.important_information
                }
            else:
                return {"status": "not_found", "message": "No business intelligence found for this user"}
                
        except Exception as e:
            logger.error(f"Error getting latest business intelligence for {user_email}: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def get_pending_urgent_alerts(self, user_email: str) -> List[Dict[str, Any]]:
        """
        Get pending urgent email alerts for a user.
        
        Args:
            user_email: The email of the user
            
        Returns:
            List of pending urgent alerts
        """
        try:
            alerts = self.db.query(UrgentEmailAlert).filter(
                UrgentEmailAlert.user_email == user_email,
                UrgentEmailAlert.is_read == False
            ).order_by(UrgentEmailAlert.created_at.desc()).all()
            
            return [
                {
                    "alert_id": alert.id,
                    "scan_date": alert.scan_date,
                    "priority_level": alert.priority_level,
                    "summary": alert.summary,
                    "urgent_emails": alert.urgent_emails
                }
                for alert in alerts
            ]
                
        except Exception as e:
            logger.error(f"Error getting pending urgent alerts for {user_email}: {str(e)}")
            return []
    
    def mark_alert_as_read(self, alert_id: int) -> Dict[str, Any]:
        """
        Mark an urgent email alert as read.
        
        Args:
            alert_id: The ID of the alert to mark as read
            
        Returns:
            Dict containing the result of the operation
        """
        try:
            alert = self.db.query(UrgentEmailAlert).filter(UrgentEmailAlert.id == alert_id).first()
            
            if alert:
                alert.is_read = True
                self.db.commit()
                return {"status": "success", "message": "Alert marked as read"}
            else:
                return {"status": "not_found", "message": "Alert not found"}
                
        except Exception as e:
            logger.error(f"Error marking alert as read: {str(e)}")
            self.db.rollback()
            return {"status": "error", "message": str(e)}
    
    def get_person_profile(self, user_email: str, contact_email: str) -> Dict[str, Any]:
        """
        Get the profile for a specific person.
        
        Args:
            user_email: The email of the user
            contact_email: The email of the contact
            
        Returns:
            Dict containing the person profile
        """
        try:
            profile = self.db.query(PersonProfile).filter(
                PersonProfile.user_email == user_email,
                PersonProfile.contact_email == contact_email
            ).first()
            
            if profile:
                return {
                    "status": "success",
                    "profile_id": profile.id,
                    "contact_name": profile.contact_name,
                    "contact_email": profile.contact_email,
                    "interaction_frequency": profile.interaction_frequency,
                    "response_patterns": profile.response_patterns,
                    "common_topics": profile.common_topics,
                    "sentiment_analysis": profile.sentiment_analysis,
                    "action_items": profile.action_items,
                    "relationship_context": profile.relationship_context,
                    "last_contact_date": profile.last_contact_date.isoformat() if profile.last_contact_date else None,
                    "last_updated": profile.updated_at.isoformat()
                }
            else:
                return {"status": "not_found", "message": "Person profile not found"}
                
        except Exception as e:
            logger.error(f"Error getting person profile: {str(e)}")
            return {"status": "error", "message": str(e)}
