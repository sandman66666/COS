"""
API routes for email intelligence.
"""

import logging
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session

from backend.models.database.database import get_db
from backend.services.email_intelligence_service import EmailIntelligenceService
from backend.core.claude_integration.claude_client import ClaudeClient
from backend.api.auth import get_current_user

# Create router
router = APIRouter(
    prefix="/api/email-intelligence",
    tags=["email-intelligence"],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger(__name__)

# Helper function to get email intelligence service
def get_email_intelligence_service(
    db: Session = Depends(get_db),
    claude_client: ClaudeClient = Depends(lambda: ClaudeClient)
) -> EmailIntelligenceService:
    return EmailIntelligenceService(db, claude_client)


@router.post("/business-intelligence-sync")
async def run_business_intelligence_sync(
    request: Request,
    background_tasks: BackgroundTasks,
    days_back: int = 30,
    service: EmailIntelligenceService = Depends(get_email_intelligence_service),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Run business intelligence sync to analyze emails from the last N days.
    This is a long-running task, so it runs in the background.
    """
    user_email = current_user["email"]
    
    # Get Google OAuth token from session
    if "google_oauth_token" not in request.session:
        raise HTTPException(status_code=400, detail="Gmail not connected. Please connect Gmail first.")
    
    token_data = request.session["google_oauth_token"]
    
    # Run in background task
    background_tasks.add_task(
        service.run_business_intelligence_sync,
        user_email=user_email,
        token_data=token_data,
        days_back=days_back
    )
    
    return {
        "status": "processing",
        "message": f"Business intelligence sync started for the last {days_back} days"
    }


@router.post("/scan-urgent-emails")
async def scan_urgent_emails(
    background_tasks: BackgroundTasks,
    hours_back: int = 24,
    service: EmailIntelligenceService = Depends(get_email_intelligence_service),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Scan for urgent emails from the last N hours.
    This is a long-running task, so it runs in the background.
    """
    user_email = current_user["email"]
    
    # Run in background task
    background_tasks.add_task(
        service.scan_for_urgent_emails,
        user_email=user_email,
        hours_back=hours_back
    )
    
    return {
        "status": "processing",
        "message": f"Urgent email scan started for the last {hours_back} hours"
    }


@router.post("/update-person-profile/{contact_email}")
async def update_person_profile(
    contact_email: str,
    background_tasks: BackgroundTasks,
    service: EmailIntelligenceService = Depends(get_email_intelligence_service),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Update the profile for a specific person.
    This is a long-running task, so it runs in the background.
    """
    user_email = current_user["email"]
    
    # Run in background task
    background_tasks.add_task(
        service.update_person_profile,
        user_email=user_email,
        contact_email=contact_email
    )
    
    return {
        "status": "processing",
        "message": f"Person profile update started for {contact_email}"
    }


@router.post("/update-key-contacts")
async def update_key_contacts(
    background_tasks: BackgroundTasks,
    service: EmailIntelligenceService = Depends(get_email_intelligence_service),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Identify and update profiles for key contacts.
    This is a long-running task, so it runs in the background.
    """
    user_email = current_user["email"]
    
    # Run in background task
    background_tasks.add_task(
        service.update_key_contacts,
        user_email=user_email
    )
    
    return {
        "status": "processing",
        "message": "Key contacts update started"
    }


@router.get("/business-intelligence")
async def get_latest_business_intelligence(
    service: EmailIntelligenceService = Depends(get_email_intelligence_service),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get the latest business intelligence for the current user.
    """
    user_email = current_user["email"]
    result = service.get_latest_business_intelligence(user_email)
    
    if result["status"] == "not_found":
        raise HTTPException(status_code=404, detail="No business intelligence found")
    elif result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    
    return result


@router.get("/urgent-alerts")
async def get_pending_urgent_alerts(
    service: EmailIntelligenceService = Depends(get_email_intelligence_service),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get pending urgent email alerts for the current user.
    """
    user_email = current_user["email"]
    alerts = service.get_pending_urgent_alerts(user_email)
    return {"alerts": alerts, "count": len(alerts)}


@router.post("/mark-alert-read/{alert_id}")
async def mark_alert_as_read(
    alert_id: int,
    service: EmailIntelligenceService = Depends(get_email_intelligence_service),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Mark an urgent email alert as read.
    """
    result = service.mark_alert_as_read(alert_id)
    
    if result["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Alert not found")
    elif result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    
    return result


@router.get("/person-profile/{contact_email}")
async def get_person_profile(
    contact_email: str,
    service: EmailIntelligenceService = Depends(get_email_intelligence_service),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get the profile for a specific person.
    """
    user_email = current_user["email"]
    result = service.get_person_profile(user_email, contact_email)
    
    if result["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Person profile not found")
    elif result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    
    return result
