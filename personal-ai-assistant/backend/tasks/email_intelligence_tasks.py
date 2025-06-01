"""
Scheduled tasks for email intelligence operations.
"""

import logging
from typing import Dict, List, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from backend.models.database.database import SessionLocal
from backend.services.email_intelligence_service import EmailIntelligenceService
from backend.core.claude_integration.claude_client import ClaudeClient
from backend.models.database.user import User

logger = logging.getLogger(__name__)

def run_daily_business_intelligence_sync():
    """
    Daily task to run business intelligence sync for all users.
    This analyzes emails from the last 30 days to build business context.
    """
    logger.info("Starting daily business intelligence sync")
    
    db = SessionLocal()
    try:
        # Get all active users
        users = db.query(User).filter(User.is_active == True).all()
        
        # Initialize Claude client
        claude_client = ClaudeClient()
        service = EmailIntelligenceService(db, claude_client)
        
        # Process each user
        for user in users:
            try:
                logger.info(f"Running business intelligence sync for {user.email}")
                result = service.run_business_intelligence_sync(user.email, days_back=30)
                
                if result["status"] == "success":
                    logger.info(f"Business intelligence sync completed for {user.email}")
                else:
                    logger.error(f"Business intelligence sync failed for {user.email}: {result.get('message', 'Unknown error')}")
                    
            except Exception as e:
                logger.error(f"Error in business intelligence sync for {user.email}: {str(e)}")
                continue
                
        logger.info("Daily business intelligence sync completed")
        
    except Exception as e:
        logger.error(f"Error in daily business intelligence sync: {str(e)}")
    finally:
        db.close()


def run_hourly_urgent_email_scan():
    """
    Hourly task to scan for urgent emails for all users.
    This checks emails from the last 6 hours for urgent items.
    """
    logger.info("Starting hourly urgent email scan")
    
    db = SessionLocal()
    try:
        # Get all active users
        users = db.query(User).filter(User.is_active == True).all()
        
        # Initialize Claude client
        claude_client = ClaudeClient()
        service = EmailIntelligenceService(db, claude_client)
        
        # Process each user
        for user in users:
            try:
                logger.info(f"Scanning urgent emails for {user.email}")
                result = service.scan_for_urgent_emails(user.email, hours_back=6)
                
                if result["status"] == "success":
                    if result.get("alert_id"):
                        logger.info(f"Urgent email scan completed for {user.email}, found urgent emails")
                    else:
                        logger.info(f"Urgent email scan completed for {user.email}, no urgent emails found")
                else:
                    logger.error(f"Urgent email scan failed for {user.email}: {result.get('message', 'Unknown error')}")
                    
            except Exception as e:
                logger.error(f"Error in urgent email scan for {user.email}: {str(e)}")
                continue
                
        logger.info("Hourly urgent email scan completed")
        
    except Exception as e:
        logger.error(f"Error in hourly urgent email scan: {str(e)}")
    finally:
        db.close()


def run_weekly_people_intelligence_update():
    """
    Weekly task to update people intelligence for all users.
    This identifies key contacts and updates their profiles.
    """
    logger.info("Starting weekly people intelligence update")
    
    db = SessionLocal()
    try:
        # Get all active users
        users = db.query(User).filter(User.is_active == True).all()
        
        # Initialize Claude client
        claude_client = ClaudeClient()
        service = EmailIntelligenceService(db, claude_client)
        
        # Process each user
        for user in users:
            try:
                logger.info(f"Updating key contacts for {user.email}")
                result = service.update_key_contacts(user.email)
                
                if result["status"] == "success":
                    logger.info(f"People intelligence update completed for {user.email}, processed {len(result.get('processed_contacts', []))} contacts")
                else:
                    logger.error(f"People intelligence update failed for {user.email}: {result.get('message', 'Unknown error')}")
                    
            except Exception as e:
                logger.error(f"Error in people intelligence update for {user.email}: {str(e)}")
                continue
                
        logger.info("Weekly people intelligence update completed")
        
    except Exception as e:
        logger.error(f"Error in weekly people intelligence update: {str(e)}")
    finally:
        db.close()
