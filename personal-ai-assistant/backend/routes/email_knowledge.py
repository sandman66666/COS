"""
API routes for email knowledge processing.
These routes handle processing emails from Gmail API to extract knowledge and tasks.
"""

from flask import Blueprint, request, jsonify, session
import logging
import os

from services.intelligence_service import IntelligenceService
from services.email_knowledge_processor import EmailKnowledgeProcessor
from integrations.gmail.gmail_connector import GmailConnector

logger = logging.getLogger(__name__)

# Create blueprint
email_knowledge_bp = Blueprint('email_knowledge', __name__)

# Get database URL from main app
database_url = None

def init_routes(app, db_url):
    """Initialize routes with database URL"""
    global database_url
    database_url = db_url
    app.register_blueprint(email_knowledge_bp, url_prefix='/api')


@email_knowledge_bp.route('/email-knowledge/process-recent', methods=['POST'])
def process_recent_emails():
    """Process recent emails to extract knowledge and tasks"""
    # Get user email from session
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'error': 'User not logged in'}), 401
    
    # Get access token from session
    access_token = session.get('access_token')
    if not access_token:
        return jsonify({'error': 'No access token available. Please authenticate with Gmail.'}), 401
    
    # Get days back from request
    data = request.json or {}
    days_back = int(data.get('days_back', 7))
    
    # Initialize services
    intelligence_service = IntelligenceService(database_url)
    email_processor = EmailKnowledgeProcessor(intelligence_service.SessionLocal)
    
    try:
        # Process emails
        result = email_processor.process_emails_for_user(
            user_email=user_email,
            access_token=access_token,
            days_back=days_back
        )
        
        if not result.get('success', False):
            return jsonify({'success': False, 'error': result.get('error', 'Unknown error')}), 500
        
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        logger.error(f"Error processing recent emails: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@email_knowledge_bp.route('/email-knowledge/process-email/<email_id>', methods=['POST'])
def process_single_email(email_id):
    """Process a single email to extract knowledge and tasks"""
    # Get user email from session
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'error': 'User not logged in'}), 401
    
    # Get access token from session
    access_token = session.get('access_token')
    if not access_token:
        return jsonify({'error': 'No access token available. Please authenticate with Gmail.'}), 401
    
    # Initialize services
    intelligence_service = IntelligenceService(database_url)
    email_processor = EmailKnowledgeProcessor(intelligence_service.SessionLocal)
    
    try:
        # Process email
        result = email_processor.process_single_email(
            user_email=user_email,
            access_token=access_token,
            email_id=email_id
        )
        
        if not result.get('success', False):
            return jsonify({'success': False, 'error': result.get('error', 'Unknown error')}), 500
        
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        logger.error(f"Error processing email: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@email_knowledge_bp.route('/email-knowledge/verify-gmail-connection', methods=['GET'])
def verify_gmail_connection():
    """Verify that the Gmail API connection is working"""
    # Get user email from session
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'error': 'User not logged in'}), 401
    
    # Get access token from session
    access_token = session.get('access_token')
    if not access_token:
        return jsonify({'error': 'No access token available. Please authenticate with Gmail.'}), 401
    
    try:
        # Initialize Gmail connector with the user's access token
        gmail_connector = GmailConnector(access_token)
        
        # Test connection by getting profile
        profile = gmail_connector.get_profile()
        
        if not profile or 'emailAddress' not in profile:
            return jsonify({
                'success': False, 
                'connected': False,
                'error': 'Could not retrieve Gmail profile'
            }), 500
        
        return jsonify({
            'success': True,
            'connected': True,
            'profile': {
                'email': profile.get('emailAddress'),
                'messagesTotal': profile.get('messagesTotal', 0)
            }
        })
    except Exception as e:
        logger.error(f"Error verifying Gmail connection: {str(e)}")
        return jsonify({
            'success': False,
            'connected': False,
            'error': str(e)
        }), 500
