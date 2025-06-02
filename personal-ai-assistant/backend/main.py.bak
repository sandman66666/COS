import os
import sys
import time
import pathlib
import secrets
import requests
import traceback
import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
# Import SQLAlchemy components
from sqlalchemy.orm import sessionmaker

# Import Google OAuth libraries
import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery
import google.auth.transport.requests

# Add the project root directory to Python's import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))  

# Import Gmail connector for real email data
from backend.integrations.gmail.gmail_connector_improved import ImprovedGmailConnector

load_dotenv()  # Load environment variables from .env file

# Configure logging
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from flask import Flask, session, render_template, redirect, url_for, request, jsonify, send_file
from flask_session import Session as FlaskSession
from werkzeug.middleware.proxy_fix import ProxyFix
import tempfile
import threading

# Global variables for tracking sync status
sync_status = {
    'is_syncing': False,
    'progress': 0,
    'user_email': '',
    'sync_type': '',
    'last_sync': None
}

# Initialize Claude client with Claude 4 Sonnet model
from anthropic import Anthropic
claude_client = Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# Initialize database URL
# Define a global database URL with an absolute path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'chief_of_staff.db')
database_url = os.environ.get('DATABASE_URL', f'sqlite:///{DATABASE_PATH}')

# Create engine and session factory
engine = create_engine(database_url)
Session = sessionmaker(bind=engine)

def get_db():
    """Get a database session"""
    return Session()

def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    
    # Configure Flask session
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-for-testing')
    app.config['SESSION_TYPE'] = 'filesystem'
    
    # Create a dedicated directory for session files
    session_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'flask_session')
    os.makedirs(session_dir, exist_ok=True)
    app.config['SESSION_FILE_DIR'] = session_dir
    
    app.config['SESSION_PERMANENT'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
    FlaskSession(app)
    
    # Google OAuth configuration
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    GOOGLE_AUTH_URI = 'https://accounts.google.com/o/oauth2/auth'
    GOOGLE_TOKEN_URI = 'https://oauth2.googleapis.com/token'
    GOOGLE_REDIRECT_URI = 'http://127.0.0.1:8080/login/google/authorized'
    
    @app.route('/')
    def index():
        return render_template('index.html', name=session.get('user_name', 'User'))
        
    @app.route('/chat')
    def chat_page():
        if 'user_email' not in session:
            return redirect(url_for('login'))
        return render_template('chat.html')
        
    @app.route('/tasks')
    def tasks_page():
        if 'user_email' not in session:
            return redirect(url_for('login'))
        return render_template('tasks.html')
        
    @app.route('/knowledge')
    def knowledge_page():
        if 'user_email' not in session:
            return redirect(url_for('login'))
        return render_template('knowledge.html')
        
    @app.route('/email-knowledge')
    def email_knowledge_page():
        """Render the email knowledge page"""
        if 'user_email' not in session:
            return redirect(url_for('login'))
            
        return render_template('email_knowledge.html')
        
    @app.route('/insights')
    def insights_page():
        if 'user_email' not in session:
            return redirect(url_for('login'))
        return render_template('insights.html')
        
    @app.route('/people')
    def people_page():
        if 'user_email' not in session:
            return redirect(url_for('login'))
        return render_template('people.html')
        
    @app.route('/integrations')
    def integrations_page():
        if 'user_email' not in session:
            return redirect(url_for('login'))
        return render_template('integrations.html')
    
    @app.route('/login')
    def login():
        # Only clear session if user is not already logged in
        if 'user_email' not in session or 'google_oauth_token' not in session:
            logger.info("User not logged in, clearing any partial session data")
            for key in list(session.keys()):
                if key.startswith('google_') or key in ['user_name', 'user_email']:
                    del session[key]
        else:
            logger.info(f"User already logged in as {session.get('user_email')}")
            return redirect(url_for('settings'))
        
        # Generate a secure state token
        state = secrets.token_urlsafe(16)
        session['oauth_state'] = state
        
        # Build the authorization URL
        auth_params = {
            'client_id': GOOGLE_CLIENT_ID,
            'redirect_uri': GOOGLE_REDIRECT_URI,
            'scope': 'openid email profile https://www.googleapis.com/auth/gmail.readonly',
            'access_type': 'offline',
            'response_type': 'code',
            'state': state,
            'prompt': 'consent'
        }
        
        auth_url = f"{GOOGLE_AUTH_URI}?" + '&'.join([f"{k}={v}" for k, v in auth_params.items()])
        logger.info("Starting OAuth flow with state: " + state)
        return redirect(auth_url)
    
    @app.route('/login/google/authorized')
    def authorized():
        # Verify state parameter to prevent CSRF
        state = request.args.get('state')
        stored_state = session.get('oauth_state')
        
        if not state or state != stored_state:
            logger.error(f"State mismatch: received {state}, expected {stored_state}")
            return redirect(url_for('index'))
        
        # Clear the state from session
        if 'oauth_state' in session:
            del session['oauth_state']
        
        # Exchange authorization code for tokens
        code = request.args.get('code')
        if not code:
            logger.error("No authorization code received")
            return redirect(url_for('index'))
        
        token_params = {
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'code': code,
            'redirect_uri': GOOGLE_REDIRECT_URI,
            'grant_type': 'authorization_code'
        }
        
        try:
            # Exchange code for token
            token_response = requests.post(GOOGLE_TOKEN_URI, data=token_params)
            token_data = token_response.json()
            
            if 'error' in token_data:
                logger.error(f"Token exchange error: {token_data['error']}")
                return redirect(url_for('index'))
            
            # Store token in session with all required fields for ImprovedGmailConnector
            session['google_oauth_token'] = {
                'access_token': token_data['access_token'],
                'refresh_token': token_data.get('refresh_token'),
                'token_type': token_data['token_type'],
                'expires_at': int(time.time()) + token_data['expires_in'],
                'client_id': GOOGLE_CLIENT_ID,
                'client_secret': GOOGLE_CLIENT_SECRET,
                'token_uri': GOOGLE_TOKEN_URI
            }
            
            # Get user info
            headers = {'Authorization': f"Bearer {token_data['access_token']}"}
            user_info_response = requests.get('https://www.googleapis.com/oauth2/v1/userinfo', headers=headers)
            user_info = user_info_response.json()
            
            session['user_name'] = user_info.get('name', 'User')
            session['user_email'] = user_info.get('email')
            
            logger.info(f"Successfully authenticated user: {session['user_email']}")
            return redirect(url_for('index'))
        except Exception as e:
            logger.error(f"OAuth callback error: {str(e)}")
            return redirect(url_for('index'))
    
    @app.route('/chat')
    def chat():
        if 'user_email' not in session:
            return redirect(url_for('login'))
        
        return render_template('chat.html', name=session.get('user_name', 'User'))
    
    @app.route('/settings')
    def settings():
        if 'user_email' not in session:
            return redirect(url_for('login'))
        
        user_email = session.get('user_email')
        
        # Get sync status
        global sync_status
        current_sync_status = None
        if sync_status['is_syncing'] and sync_status['user_email'] == user_email:
            current_sync_status = sync_status
        
        # Initialize services for this request
        from services.intelligence_service import IntelligenceService
        from services.structured_knowledge_service import StructuredKnowledgeService
        from services.knowledge_integration_service import KnowledgeIntegrationService
        from services.entity_extraction_service import EntityExtractionService
        from models.database.insights_storage import UserIntelligence, EmailSyncStatus
        from models.database.structured_knowledge import Project, Goal, KnowledgeFile
        from models.database.tasks import Task
        
        intelligence_service = IntelligenceService(database_url, claude_client)
        structured_knowledge_service = StructuredKnowledgeService(database_url)
        knowledge_integration_service = KnowledgeIntegrationService(intelligence_service.SessionLocal, claude_client)
        
        # Get user preferences
        session_db = intelligence_service.SessionLocal()
        try:
            user_intel = session_db.query(UserIntelligence).filter_by(user_email=user_email).first()
            preferences = user_intel.personal_knowledge.get('preferences', {}) if user_intel else {}
        finally:
            session_db.close()
        
        # Initialize structured knowledge service
        from services.structured_knowledge_service import StructuredKnowledgeService
        structured_knowledge_service = StructuredKnowledgeService(intelligence_service.SessionLocal)
        
        # Get structured knowledge
        projects = structured_knowledge_service.get_projects(user_email)
        goals = structured_knowledge_service.get_goals(user_email)
        knowledge_files = structured_knowledge_service.get_knowledge_files(user_email)
        
        return render_template('settings.html', 
                               user_email=user_email,
                               sync_status=current_sync_status,
                               preferences=preferences,
                               projects=projects,
                               goals=goals,
                               knowledge_files=knowledge_files,
                               email_sync_frequency=session.get('email_sync_frequency', 24),
                               email_days_back=session.get('email_days_back', 30),
                               urgent_alerts_enabled=session.get('urgent_alerts_enabled', True))
    
    @app.route('/email-insights')
    def email_insights():
        # Redirect to the new insights route
        return redirect(url_for('insights'))
        
    @app.route('/insights')
    def insights():
        if 'user_email' not in session:
            return redirect(url_for('login'))
        
        user_email = session['user_email']
        
        # Get sync status
        global sync_status
        current_sync_status = None
        if sync_status.get('is_syncing') and sync_status.get('user_email') == user_email:
            current_sync_status = sync_status
            # Redirect to sync progress page if sync is in progress
            return render_template('sync_in_progress.html',
                                  active_tab='insights',
                                  name=session.get('user_name', 'User'),
                                  user_email=user_email,
                                  sync_status=current_sync_status)
        
        # If no sync is in progress, show the insights page
        return render_template('insights.html', 
                              active_tab='insights', 
                              name=session.get('user_name', 'User'),
                              user_email=user_email,
                              has_insights='email_insights' in session,
                              insights=session.get('email_insights', {}),
                              last_sync=session.get('last_email_sync', 'Never'))

        

        

        
        # Pass the raw insights data to the template
        return render_template('email_insights.html', 
                            name=session.get('user_name', 'User'),
                            insights=insights)
    
    @app.route('/logout')
    def logout():
        session.clear()
        logger.info("User logged out")
        return redirect(url_for('index'))
    
    @app.route('/sync-emails', methods=['GET', 'POST'])
    def sync_emails():
        logger.info(f"Sync emails route called with method: {request.method}")
        
        if 'user_email' not in session or 'google_oauth_token' not in session:
            logger.warning("User not authenticated, redirecting to login")
            return redirect(url_for('login'))
            
        user_email = session['user_email']
        access_token = session['google_oauth_token']['access_token']
        days_back = session.get('email_days_back', 30)
        
        # Check if force_full_sync was requested
        force_full_sync = request.args.get('force_full_sync', 'false').lower() == 'true'
        
        logger.info(f"Starting email sync for {user_email} with {days_back} days back, force_full_sync={force_full_sync}")
        
        # Initialize intelligence service using the global database_url
        # Initialize intelligence service for this request
        from services.intelligence_service import IntelligenceService
        from models.database.insights_storage import UserIntelligence
        intelligence_service = IntelligenceService(database_url, claude_client)
        
        # Update global sync status
        global sync_status
        sync_status = {
            'user_email': user_email,
            'is_syncing': True,
            'progress': 0,
            'sync_type': 'Email Intelligence',
            'start_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Start sync in background thread
        def run_sync():
            global sync_status
            try:
                logger.info("Starting email sync in background thread")
                
                # Process and store insights
                result = intelligence_service.process_and_store_email_insights(
                    user_email, 
                    access_token, 
                    days_back,
                    force_full_sync
                )
                
                logger.info(f"Email sync completed with result: {result}")
                
                # Update sync status with results
                sync_status['is_syncing'] = False
                sync_status['progress'] = 100
                sync_status['completed_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                sync_status['email_insights'] = result
                
            except Exception as e:
                logger.error(f"Error in background sync thread: {str(e)}")
                # Update sync status with error
                sync_status['is_syncing'] = False
                sync_status['progress'] = 0
                sync_status['error'] = str(e)
        
        # Start sync thread
        sync_thread = threading.Thread(target=run_sync)
        sync_thread.daemon = True
        sync_thread.start()
        logger.info("Sync thread started successfully")
        
        # Show sync progress page
        return render_template('sync_in_progress.html',
                            name=session.get('user_name', 'User'),
                            sync_type='Email Intelligence',
                            progress=0)
            
    @app.route('/disconnect-gmail')
    def disconnect_gmail():
        if 'google_oauth_token' in session:
            del session['google_oauth_token']
        if 'last_email_sync' in session:
            del session['last_email_sync']
            
        # Redirect to settings page
        return redirect(url_for('settings'))
    
    @app.route('/api/sync-status', methods=['GET'])
    def api_sync_status():
        """Get the status of the current sync operation"""
        global sync_status
        
        if 'user_email' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
            
        # Only return sync status for the current user
        if sync_status.get('user_email') == session.get('user_email'):
            # If sync is complete, update session with insights
            if not sync_status.get('is_syncing') and sync_status.get('progress') == 100:
                if 'email_insights' in sync_status:
                    session['email_insights'] = sync_status['email_insights']
                    session['last_email_sync'] = sync_status.get('last_sync', datetime.now().strftime("%Y-%m-%d %H:%M"))
                
            return jsonify({
                'success': True,
                'is_syncing': sync_status.get('is_syncing', False),
                'progress': sync_status.get('progress', 0),
                'sync_type': sync_status.get('sync_type', ''),
                'last_sync': sync_status.get('last_sync', ''),
                'redirect': '/email-insights' if not sync_status.get('is_syncing') and sync_status.get('progress') == 100 else None
            })
        else:
            # No sync status for this user
            # Instead of redirecting to settings, redirect to email-insights
            # This prevents the redirect loop when returning from settings page
            return jsonify({
                'success': True,
                'is_syncing': False,
                'progress': 0,
                'sync_type': '',
                'last_sync': '',
                'redirect': '/email-insights'
            })
    
    @app.route('/api/save-preferences', methods=['POST'])
    def save_preferences():
        if 'user_email' not in session:
            return jsonify({'success': False, 'error': 'Not logged in'}), 401
            
        try:
            data = request.json
            
            # Save preferences to session
            session['email_sync_frequency'] = int(data.get('email_sync_frequency', 24))
            session['email_days_back'] = int(data.get('email_days_back', 30))
            session['urgent_alerts_enabled'] = bool(data.get('urgent_alerts_enabled', True))
            
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"Error saving preferences: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/reset-database', methods=['POST'])
    def reset_database():
        if 'user_email' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        try:
            # Import models here to avoid circular imports
            from models.database.insights_storage import UserIntelligence, EmailSyncStatus, ContactIntelligence
            from models.database.structured_knowledge import Task, Project, Goal, KnowledgeFile
            
            db = get_db()
            user_email = session['user_email']
            
            logger.info(f"Starting database reset for user {user_email}")
            
            # Get user intelligence record to find related records
            user_intel = db.query(UserIntelligence).filter_by(user_email=user_email).first()
            
            if user_intel:
                # Delete related records first (foreign key constraints)
                logger.info("Deleting tasks...")
                db.query(Task).filter_by(user_email=user_email).delete()
                
                logger.info("Deleting projects, goals, and knowledge files...")
                if user_intel.id:
                    db.query(Project).filter_by(user_intelligence_id=user_intel.id).delete()
                    db.query(Goal).filter_by(user_intelligence_id=user_intel.id).delete()
                    db.query(KnowledgeFile).filter_by(user_intelligence_id=user_intel.id).delete()
                
                logger.info("Deleting contact intelligence...")
                db.query(ContactIntelligence).filter_by(user_email=user_email).delete()
                
                logger.info("Deleting email sync status...")
                db.query(EmailSyncStatus).filter_by(user_email=user_email).delete()
                
                logger.info("Deleting user intelligence...")
                db.delete(user_intel)
            else:
                logger.info(f"No user intelligence record found for {user_email}")
            
            # Reset the global sync status if it belongs to this user
            global sync_status
            if sync_status.get('user_email') == user_email:
                sync_status = {
                    'is_syncing': False,
                    'progress': 0,
                    'user_email': None,
                    'sync_type': None,
                    'last_sync': None
                }
            
            db.commit()
            logger.info(f"Database reset completed for user {user_email}")
            
            return jsonify({'success': True, 'message': 'Database reset successful. Please refresh your Gmail data.'})
        except Exception as e:
            logger.error(f"Error resetting database: {str(e)}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            db.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/auth/gmail')
    def auth_gmail():
        """Start the Gmail OAuth flow"""
        # Generate a random state token to prevent CSRF
        state = secrets.token_hex(16)
        session['oauth_state'] = state
        
        # Configure OAuth 2.0 parameters
        auth_params = {
            'client_id': GOOGLE_CLIENT_ID,
            'redirect_uri': GOOGLE_REDIRECT_URI,
            'scope': 'openid email profile https://www.googleapis.com/auth/gmail.readonly',
            'access_type': 'offline',
            'response_type': 'code',
            'state': state,
            'prompt': 'consent'
        }
        
                
            try:
                data = request.json
                
                # Save preferences to session
                session['email_sync_frequency'] = int(data.get('email_sync_frequency', 24))
                session['email_days_back'] = int(data.get('email_days_back', 30))
                session['urgent_alerts_enabled'] = bool(data.get('urgent_alerts_enabled', True))
                
                return jsonify({'success': True})
            except Exception as e:
                logger.error(f"Error saving preferences: {str(e)}")
                return jsonify({'success': False, 'error': str(e)}), 500
    def api_reset_database():
        """Reset the entire database and clear all user data using SQLAlchemy ORM models"""
        if 'user_email' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        user_email = session['user_email']
        logger.info(f"Starting database reset for user {user_email}")
        
        # Get the database session
        db = get_db()
        
        try:
            # Delete all user data in the correct order to respect foreign key constraints
            # First, delete tasks associated with the user
            from models.database.tasks import Task
            db.query(Task).filter_by(user_email=user_email).delete()
            logger.info(f"Deleted tasks for user {user_email}")
            
            # Delete projects associated with the user
            from models.database.projects import Project
            db.query(Project).filter_by(user_email=user_email).delete()
            logger.info(f"Deleted projects for user {user_email}")
            
            # Delete goals associated with the user
            from models.database.goals import Goal
            db.query(Goal).filter_by(user_email=user_email).delete()
            logger.info(f"Deleted goals for user {user_email}")
            
            # Delete knowledge files associated with the user
            from models.database.knowledge_files import KnowledgeFile
            db.query(KnowledgeFile).filter_by(user_email=user_email).delete()
            logger.info(f"Deleted knowledge files for user {user_email}")
            
            # Delete contacts associated with the user
            from models.database.contacts import Contact
            db.query(Contact).filter_by(user_email=user_email).delete()
            logger.info(f"Deleted contacts for user {user_email}")
            
            # Delete sync status associated with the user
            from models.database.sync_status import SyncStatus
            db.query(SyncStatus).filter_by(user_email=user_email).delete()
            logger.info(f"Deleted sync status for user {user_email}")
            
            # Reset global sync status if it belongs to the user
            global sync_status
            if sync_status and sync_status.get('user_email') == user_email:
                sync_status = None
                logger.info(f"Reset global sync status for user {user_email}")
            
            # Delete user intelligence data
            from models.database.user_intelligence import UserIntelligence
            db.query(UserIntelligence).filter_by(user_email=user_email).delete()
            logger.info(f"Deleted user intelligence for user {user_email}")
            
            # Commit all changes
            db.commit()
            logger.info(f"Database reset completed successfully for user {user_email}")
            
            # Clear session data except for authentication
            google_oauth_token = session.get('google_oauth_token')
            session.clear()
            session['user_email'] = user_email
            if google_oauth_token:
                session['google_oauth_token'] = google_oauth_token
            
            return jsonify({'success': True, 'message': 'Database has been reset successfully'})
        
        except Exception as e:
            # Rollback in case of error
            db.rollback()
            error_details = traceback.format_exc()
            logger.error(f"Error resetting database: {str(e)}")
            logger.error(error_details)
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            db.close()

    @app.route('/api/people/relationships', methods=['GET'])
    def api_people_relationships():
        """Get relationship data based on email activity"""
        if 'user_email' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        try:
            # Check if we have a valid Gmail token
            if 'google_oauth_token' not in session:
                return jsonify({'success': False, 'error': 'Gmail not connected'}), 400
                
            # Use the Gmail API to get real relationship data
            token_data = session['google_oauth_token']
            gmail_connector = ImprovedGmailConnector(token_data)
            
            # Get email stats to find top relationships
            emails_result = gmail_connector.get_recent_emails(days_back=30, max_results=100)
            
            if not emails_result.get('success'):
                return jsonify({'success': False, 'error': emails_result.get('error')}), 500
                
            # Count email interactions by contact
            contact_interactions = {}
            for email in emails_result.get('emails', []):
                # From contacts
                if 'from' in email:
                    from_email = email['from'].get('email')
                    from_name = email['from'].get('name')
                    if from_email and from_email != session['user_email']:
                        if from_email not in contact_interactions:
                            contact_interactions[from_email] = {
                                'name': from_name or from_email.split('@')[0],
                                'email': from_email,
                                'organization': from_email.split('@')[1] if '@' in from_email else '',
                                'emailCount': 1,
                                'lastContact': email.get('date')
                            }
                        else:
                            contact_interactions[from_email]['emailCount'] += 1
                            # Update last contact if this email is more recent
                            if email.get('date') > contact_interactions[from_email]['lastContact']:
                                contact_interactions[from_email]['lastContact'] = email.get('date')
                
                # To contacts
                for to in email.get('to', []):
                    to_email = to.get('email')
                    to_name = to.get('name')
                    if to_email and to_email != session['user_email']:
                        if to_email not in contact_interactions:
                            contact_interactions[to_email] = {
                                'name': to_name or to_email.split('@')[0],
                                'email': to_email,
                                'organization': to_email.split('@')[1] if '@' in to_email else '',
                                'emailCount': 1,
                                'lastContact': email.get('date')
                            }
                        else:
                            contact_interactions[to_email]['emailCount'] += 1
                            # Update last contact if this email is more recent
                            if email.get('date') > contact_interactions[to_email]['lastContact']:
                                contact_interactions[to_email]['lastContact'] = email.get('date')
            
            # Convert to list and sort by email count
            relationships = list(contact_interactions.values())
            relationships.sort(key=lambda x: x['emailCount'], reverse=True)
            
            # Limit to top 5 relationships
            top_relationships = relationships[:5] if len(relationships) > 5 else relationships
            
            return jsonify({'success': True, 'relationships': top_relationships})
        except Exception as e:
            logger.error(f"Error fetching relationship data: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/knowledge-graph/stats', methods=['GET'])
    def api_knowledge_graph_stats():
        """Get knowledge graph statistics"""
        if 'user_email' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        try:
            # In a real implementation, this would fetch from a database
            # For now, return sample data
            sample_stats = {
                'nodes': 156,
                'edges': 243,
                'concepts': 42,
                'entities': 78,
                'lastUpdated': '2025-05-30T18:30:00Z'
            }
            
            return jsonify({'success': True, 'stats': sample_stats})
        except Exception as e:
            logger.error(f"Error fetching knowledge graph stats: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/integrations/status', methods=['GET'])
    def api_integrations_status():
        """Get status of all integrations"""
        if 'user_email' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
            
        try:
            # Check Gmail connection status
            gmail_status = {
                'connected': 'google_oauth_token' in session,
                'lastSynced': session.get('last_email_sync', 'Never'),
                'emailCount': 0
            }
            
            # If Gmail is connected, get real stats
            if gmail_status['connected']:
                try:
                    token_data = session['google_oauth_token']
                    gmail_connector = ImprovedGmailConnector(token_data)
                    connection_test = gmail_connector.test_connection()
                    
                    if connection_test['success']:
                        gmail_status['emailCount'] = connection_test.get('messages_total', 0)
                    else:
                        gmail_status['error'] = connection_test.get('error', 'Connection failed')
                        # If connection failed, token might be invalid
                        gmail_status['connected'] = False
                except Exception as gmail_error:
                    logger.error(f"Error getting Gmail status: {str(gmail_error)}")
                    gmail_status['error'] = str(gmail_error)
                    # If there was an error, consider the connection as failed
                    gmail_status['connected'] = False
            
            # Check Neo4j connection status
            neo4j_status = {
                'connected': False,
                'error': 'Not configured'
            }
            
            # For now, calendar is not implemented
            calendar_status = {
                'connected': False,
                'error': 'Not implemented'
            }
            
            status = {
                'gmail': gmail_status,
                'calendar': calendar_status,
                'neo4j': neo4j_status
            }
            
            return jsonify({'success': True, 'status': status})
        except Exception as e:
            logger.error(f"Error fetching integration status: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
            
    @app.route('/api/auth/gmail/revoke', methods=['POST'])
    def api_auth_gmail_revoke():
        """Revoke Gmail OAuth token and remove from session"""
        if 'user_email' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
            
        try:
            # Check if token exists in session
            if 'google_oauth_token' not in session:
                return jsonify({'success': True, 'message': 'No token to revoke'})
                
            # Get token data
            token_data = session['google_oauth_token']
            
            # Try to revoke the token with Google
            try:
                # Create credentials object
                credentials = google.oauth2.credentials.Credentials(**token_data)
                
                # Revoke token
                requests.post('https://oauth2.googleapis.com/revoke',
                    params={'token': credentials.token},
                    headers={'content-type': 'application/x-www-form-urlencoded'})
                    
            except Exception as revoke_error:
                # Log error but continue to remove from session
                logger.error(f"Error revoking token with Google: {str(revoke_error)}")
                
            # Remove token from session
            session.pop('google_oauth_token', None)
            
            return jsonify({'success': True, 'message': 'Gmail disconnected successfully'})
        except Exception as e:
            logger.error(f"Error revoking Gmail token: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
            
    @app.route('/api/auth/gmail/refresh', methods=['POST'])
    def api_auth_gmail_refresh():
        """Refresh Gmail OAuth token"""
        if 'user_email' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
            
        try:
            # Check if token exists in session
            if 'google_oauth_token' not in session:
                return jsonify({'success': False, 'error': 'No token to refresh'}), 400
                
            # Get token data
            token_data = session['google_oauth_token']
            
            # Create credentials object
            credentials = google.oauth2.credentials.Credentials(**token_data)
            
            # Check if refresh token exists
            if not credentials.refresh_token:
                return jsonify({'success': False, 'error': 'No refresh token available. Please reconnect Gmail.'}), 400
                
            # Refresh the token
            request = google.auth.transport.requests.Request()
            credentials.refresh(request)
            
            # Update token in session
            session['google_oauth_token'] = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }
            
            return jsonify({'success': True, 'message': 'Gmail token refreshed successfully'})
        except Exception as e:
            logger.error(f"Error refreshing Gmail token: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/insights', methods=['GET'])
    def api_insights():
        """Get insights data from the database"""
        if 'user_email' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_email = session['user_email']
        
        # Check if force refresh is requested
        force_refresh = request.args.get('refresh', 'false').lower() == 'true'
        
        try:
            # Initialize services
            from services.intelligence_service import IntelligenceService
            from services.structured_knowledge_service import StructuredKnowledgeService
            from models.database.insights_storage import UserIntelligence, EmailSyncStatus
            from models.database.structured_knowledge import Project
            from models.database.tasks import Task
            from datetime import datetime, timedelta
            from sqlalchemy import desc, func
            
            intelligence_service = IntelligenceService(database_url, claude_client)
            structured_knowledge_service = StructuredKnowledgeService(database_url)
            
            # Create a database session
            db = intelligence_service.SessionLocal()
            
            try:
                # Get projects data
                projects_data = []
                projects = db.query(Project).filter(Project.user_email == user_email).all()
                
                for project in projects:
                    # Get email count related to this project (simplified)
                    # Since UserIntelligence doesn't have project_id, we'll just use a default count
                    email_count = 0
                    # You can implement a proper count if you have a way to link emails to projects
                    
                    # Get people involved in this project
                    people = []
                    if project.stakeholders:
                        for stakeholder in project.stakeholders:
                            if '@' in stakeholder:  # Simple validation
                                name = stakeholder.split('@')[0].replace('.', ' ').title()
                                people.append({
                                    'name': name,
                                    'email': stakeholder
                                })
                    
                    projects_data.append({
                        'name': project.name,
                        'description': project.description,
                        'lastActivity': project.updated_at.isoformat() if project.updated_at else datetime.now().isoformat(),
                        'emailCount': email_count,
                        'people': people
                    })
                
                # Get email activity for the last 7 days
                email_activity = []
                end_date = datetime.now()
                start_date = end_date - timedelta(days=7)
                
                for i in range(7):
                    current_date = start_date + timedelta(days=i)
                    date_str = current_date.strftime('%Y-%m-%d')
                    
                    # Count insights for this day
                    count = db.query(UserIntelligence).filter(
                        UserIntelligence.user_email == user_email,
                        func.date(UserIntelligence.created_at) == current_date.date()
                    ).count()
                    
                    email_activity.append({
                        'date': date_str,
                        'count': count
                    })
                
                # Get generated insights
                insights_data = []
                insights = db.query(UserIntelligence).filter(
                    UserIntelligence.user_email == user_email
                ).order_by(desc(UserIntelligence.created_at)).limit(10).all()
                
                for idx, insight in enumerate(insights):
                    # Determine insight type based on content or other attributes
                    # since insight_type doesn't exist in the model
                    insight_type = 'action'  # Default type
                    
                    # Extract insight text from the appropriate field
                    # Assuming the insight text is stored in one of these JSON fields
                    insight_text = ''
                    if insight.tactical_notifications and len(insight.tactical_notifications) > 0:
                        insight_text = insight.tactical_notifications[0].get('text', '')
                    elif insight.last_email_analysis:
                        insight_text = insight.last_email_analysis.get('summary', '')
                    
                    # Determine source
                    source = 'email'
                    
                    insights_data.append({
                        'id': str(insight.id),
                        'type': insight_type,
                        'content': insight_text,
                        'source': source,
                        'date': insight.created_at.isoformat(),
                        'priority': 'medium'
                    })
                
                # Get tasks
                tasks = db.query(Task).filter(Task.user_email == user_email).all()
                tasks_data = [{
                    'id': str(task.id),
                    'title': task.title,
                    'description': task.description,
                    'status': task.status,
                    'priority': task.priority,
                    'due_date': task.due_date.isoformat() if task.due_date else None,
                    'created_at': task.created_at.isoformat() if task.created_at else None
                } for task in tasks]
                
                result = {
                    'success': True,
                    'projects': projects_data,
                    'emailActivity': email_activity,
                    'generatedInsights': insights_data,
                    'tasks': tasks_data
                }
                
                return jsonify(result)
            
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error fetching insights data: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/force-refresh', methods=['POST'])
    def api_force_refresh():
        """Force refresh all data from Gmail"""
        if 'user_email' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
            
        if 'google_oauth_token' not in session:
            return jsonify({'success': False, 'error': 'Gmail not connected'}), 400
            
        try:
            # Get the token data
            token_data = session['google_oauth_token']
            user_email = session['user_email']
            logger.info(f"Starting force refresh for user: {user_email}")
            
            # Initialize the Gmail connector
            gmail_connector = ImprovedGmailConnector(token_data)
            logger.info("Gmail connector initialized")
            
            # Test the connection to Gmail API
            test_result = gmail_connector.test_connection()
            if not test_result.get('success'):
                logger.error(f"Gmail connection test failed: {test_result.get('error')}")
                return jsonify({'success': False, 'error': f"Gmail connection failed: {test_result.get('error')}"}), 500
            
            logger.info("Gmail connection test successful")
            
            # Start a background thread to sync emails
            def sync_emails_background():
                global sync_status
                sync_status['is_syncing'] = True
                sync_status['progress'] = 0
                sync_status['user_email'] = user_email
                sync_status['sync_type'] = 'full'
                
                try:
                    # Get recent emails
                    logger.info("Fetching recent emails from Gmail...")
                    emails_result = gmail_connector.get_recent_emails(days_back=30, max_results=100)
                    
                    if not emails_result.get('success'):
                        logger.error(f"Error fetching emails: {emails_result.get('error')}")
                        sync_status['is_syncing'] = False
                        return
                    
                    # Process emails and update database
                    emails = emails_result.get('emails', [])
                    total_emails = len(emails)
                    logger.info(f"Retrieved {total_emails} emails from Gmail")
                    
                    if total_emails == 0:
                        logger.warning("No emails retrieved from Gmail API")
                        sync_status['is_syncing'] = False
                        sync_status['progress'] = 100
                        sync_status['last_sync'] = datetime.now().isoformat()
                        return
                    
                    # Initialize services
                    from services.intelligence_service import IntelligenceService
                    intelligence_service = IntelligenceService(database_url, claude_client)
                    logger.info("Intelligence service initialized")
                    
                    # Process each email
                    for i, email in enumerate(emails):
                        # Update progress
                        sync_status['progress'] = int((i / total_emails) * 100)
                        
                        # Log email details for debugging
                        logger.info(f"Processing email {i+1}/{total_emails}: {email.get('subject', 'No subject')}")
                        
                        # Process the email using our implementation
                        try:
                            intelligence_service.process_email(email, user_email)
                            logger.info(f"Successfully processed email {i+1}/{total_emails}")
                        except Exception as email_error:
                            logger.error(f"Error processing email {i+1}: {str(email_error)}")
                            logger.error(traceback.format_exc())
                            # Continue with next email instead of failing the entire process
                            continue
                    
                    # Update sync status
                    sync_status['is_syncing'] = False
                    sync_status['progress'] = 100
                    sync_status['last_sync'] = datetime.now().isoformat()
                    logger.info(f"Email sync completed successfully for user {user_email}")
                    
                except Exception as e:
                    logger.error(f"Error in sync background task: {str(e)}")
                    logger.error(traceback.format_exc())
                    sync_status['is_syncing'] = False
            
            # Start the background thread if not already syncing
            if not sync_status['is_syncing']:
                sync_thread = threading.Thread(target=sync_emails_background)
                sync_thread.daemon = True
                sync_thread.start()
                return jsonify({'success': True, 'message': 'Sync started'})
            else:
                return jsonify({'success': False, 'error': 'Sync already in progress'}), 400
                
        except Exception as e:
            logger.error(f"Error starting force refresh: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
            
    # Sync status endpoint moved to line ~417
    
    @app.route('/api/chat', methods=['POST'])
    def api_chat():
        """Handle chat messages and get responses from Claude."""
        if 'user_email' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        try:
            data = request.json
            if not data or 'message' not in data:
                return jsonify({'error': 'No message provided'}), 400
            
            user_message = data['message']
            logger.info(f"Chat request from {session['user_email']}: {user_message[:50]}...")
            
            # Get context from session if available
            email_insights = session.get('email_insights', {})
            user_name = session.get('user_name', 'User')
            user_email = session.get('user_email', 'user@example.com')
            
            # Build a more detailed context for Claude
            context_parts = [f"You are an AI Chief of Staff assistant for {user_name} ({user_email})."]
            
            if email_insights and email_insights.get('status') != 'error':
                context_parts.append("\nBased on recent email analysis, here's what I know:")
                
                # Add key relationships
                if email_insights.get('key_relationships'):
                    context_parts.append("\n**Key Relationships:**")
                    for rel in email_insights['key_relationships'][:5]:  # Top 5
                        if isinstance(rel, dict):
                            context_parts.append(f"- {rel.get('name', 'Unknown')} ({rel.get('email', '')}): {rel.get('context', '')}")
                        else:
                            context_parts.append(f"- {rel}")
                
                # Add active projects
                if email_insights.get('active_projects'):
                    context_parts.append("\n**Active Projects:**")
                    for proj in email_insights['active_projects'][:5]:  # Top 5
                        if isinstance(proj, dict):
                            context_parts.append(f"- {proj.get('name', 'Unknown')}: {proj.get('description', '')}")
                        else:
                            context_parts.append(f"- {proj}")
                
                # Add action items
                if email_insights.get('action_items'):
                    context_parts.append("\n**Action Items:**")
                    for action in email_insights['action_items'][:5]:  # Top 5
                        if isinstance(action, dict):
                            context_parts.append(f"- {action.get('description', 'Unknown')} (Due: {action.get('deadline', 'No deadline')})")
                        else:
                            context_parts.append(f"- {action}")
                
                # Add important information
                if email_insights.get('important_information'):
                    context_parts.append("\n**Important Information:**")
                    for info in email_insights['important_information'][:3]:  # Top 3
                        if isinstance(info, dict):
                            context_parts.append(f"- {info.get('description', '')}")
                        else:
                            context_parts.append(f"- {info}")
                
                context_parts.append(f"\nThis information is based on analyzing {user_name}'s emails from the last 30 days.")
            else:
                context_parts.append("\nNo email insights are currently available. The user may need to sync their emails first.")
            
            context = "\n".join(context_parts)
            
            # Log context for debugging
            logger.info(f"Context length: {len(context)} characters")
            logger.info(f"Has insights: {'email_insights' in session and bool(email_insights)}")
            
            # Send message to Claude
            try:
                response = claude_client.messages.create(
                    model=CLAUDE_MODEL,
                    max_tokens=2000,
                    temperature=0.7,
                    system=context,
                    messages=[{"role": "user", "content": user_message}]
                )
                
                # Extract the response text
                assistant_message = response.content[0].text
                
            except AttributeError:
                # Fallback for older SDK versions
                logger.info("Using fallback Claude client interface for chat")
                response = claude_client.completions.create(
                    model=CLAUDE_MODEL,
                    max_tokens=2000,
                    temperature=0.7,
                    system=context,
                    prompt=user_message
                )
                assistant_message = response.completion
            
            logger.info(f"Claude response: {assistant_message[:50]}...")
            
            return jsonify({
                'response': assistant_message,
                'status': 'success'
            })
            
        except Exception as e:
            logger.error(f"Chat API error: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return jsonify({
                'error': f'Failed to process chat: {str(e)}',
                'status': 'error'
            }), 500
    
    @app.route('/test-insights')
    def test_insights():
        """Test page for debugging insights display"""
        if 'user_email' not in session:
            return redirect(url_for('login'))
        return send_file('../test_insights_display.html')
    
    @app.route('/api/debug-session')
    def debug_session():
        """Debug endpoint to check session data"""
        if 'user_email' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        # Get insights from session
        email_insights = session.get('email_insights', {})
        
        # Check structure
        debug_info = {
            'user_email': session.get('user_email'),
            'last_sync': session.get('last_email_sync', 'Never'),
            'has_insights': 'email_insights' in session,
            'insights_keys': list(email_insights.keys()) if email_insights else [],
            'insights_summary': {
                'key_relationships': len(email_insights.get('key_relationships', [])),
                'active_projects': len(email_insights.get('active_projects', [])),
                'action_items': len(email_insights.get('action_items', [])),
                'important_information': len(email_insights.get('important_information', []))
            } if email_insights else {},
            'sample_relationship': email_insights.get('key_relationships', [{}])[0] if email_insights.get('key_relationships') else None,
            'insights_status': email_insights.get('status', 'unknown')
        }
        
        return jsonify(debug_info)
    
    # API routes for structured knowledge
    @app.route('/api/projects', methods=['GET', 'POST'])
    def api_projects():
        if 'user_email' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_email = session.get('user_email')
        
        # Initialize intelligence service
        from services.intelligence_service import IntelligenceService
        intelligence_service = IntelligenceService(database_url, claude_client)
        
        # Initialize structured knowledge service
        from services.structured_knowledge_service import StructuredKnowledgeService
        structured_knowledge_service = StructuredKnowledgeService(intelligence_service.SessionLocal)
        
        if request.method == 'GET':
            projects = structured_knowledge_service.get_projects(user_email)
            return jsonify(projects)
        
        elif request.method == 'POST':
            project_data = request.json
            if not project_data or 'name' not in project_data:
                return jsonify({'error': 'Project name is required', 'success': False}), 400
            
            project = structured_knowledge_service.create_project(user_email, project_data)
            return jsonify({'success': True, 'project': project})
    
    @app.route('/api/projects/<project_id>', methods=['GET', 'PUT', 'DELETE'])
    def api_project(project_id):
        if 'user_email' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_email = session.get('user_email')
        
        # Initialize intelligence service
        from services.intelligence_service import IntelligenceService
        intelligence_service = IntelligenceService(database_url, claude_client)
        
        # Initialize structured knowledge service
        from services.structured_knowledge_service import StructuredKnowledgeService
        structured_knowledge_service = StructuredKnowledgeService(intelligence_service.SessionLocal)
        
        if request.method == 'GET':
            project = structured_knowledge_service.get_project(user_email, project_id)
            if not project:
                return jsonify({'error': 'Project not found'}), 404
            return jsonify(project)
        
        elif request.method == 'PUT':
            project_data = request.json
            if not project_data:
                return jsonify({'error': 'No data provided', 'success': False}), 400
            
            project = structured_knowledge_service.update_project(user_email, project_id, project_data)
            if not project:
                return jsonify({'error': 'Project not found', 'success': False}), 404
            return jsonify({'success': True, 'project': project})
        
        elif request.method == 'DELETE':
            success = structured_knowledge_service.delete_project(user_email, project_id)
            if not success:
                return jsonify({'error': 'Project not found', 'success': False}), 404
            return jsonify({'success': True})
    
    @app.route('/api/goals', methods=['GET', 'POST'])
    def api_goals():
        if 'user_email' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_email = session.get('user_email')
        
        # Initialize intelligence service
        from services.intelligence_service import IntelligenceService
        intelligence_service = IntelligenceService(database_url, claude_client)
        
        # Initialize structured knowledge service
        from services.structured_knowledge_service import StructuredKnowledgeService
        structured_knowledge_service = StructuredKnowledgeService(intelligence_service.SessionLocal)
        
        if request.method == 'GET':
            goals = structured_knowledge_service.get_goals(user_email)
            return jsonify(goals)
        
        elif request.method == 'POST':
            goal_data = request.json
            if not goal_data or 'title' not in goal_data:
                return jsonify({'error': 'Goal title is required', 'success': False}), 400
            
            goal = structured_knowledge_service.create_goal(user_email, goal_data)
            return jsonify({'success': True, 'goal': goal})
    
    @app.route('/api/goals/<goal_id>', methods=['GET', 'PUT', 'DELETE'])
    def api_goal(goal_id):
        if 'user_email' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_email = session.get('user_email')
        
        # Initialize intelligence service
        from services.intelligence_service import IntelligenceService
        intelligence_service = IntelligenceService(database_url, claude_client)
        
        # Initialize structured knowledge service
        from services.structured_knowledge_service import StructuredKnowledgeService
        structured_knowledge_service = StructuredKnowledgeService(intelligence_service.SessionLocal)
        
        if request.method == 'GET':
            goal = structured_knowledge_service.get_goal(user_email, goal_id)
            if not goal:
                return jsonify({'error': 'Goal not found'}), 404
            return jsonify(goal)
        
        elif request.method == 'PUT':
            goal_data = request.json
            if not goal_data:
                return jsonify({'error': 'No data provided', 'success': False}), 400
            
            goal = structured_knowledge_service.update_goal(user_email, goal_id, goal_data)
            if not goal:
                return jsonify({'error': 'Goal not found', 'success': False}), 404
            return jsonify({'success': True, 'goal': goal})
        
        elif request.method == 'DELETE':
            success = structured_knowledge_service.delete_goal(user_email, goal_id)
            if not success:
                return jsonify({'error': 'Goal not found', 'success': False}), 404
            return jsonify({'success': True})
    
    @app.route('/api/knowledge-files', methods=['GET', 'POST'])
    def api_knowledge_files():
        if 'user_email' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_email = session.get('user_email')
        
        # Initialize intelligence service
        from services.intelligence_service import IntelligenceService
        intelligence_service = IntelligenceService(database_url, claude_client)
        
        # Initialize structured knowledge service
        from services.structured_knowledge_service import StructuredKnowledgeService
        structured_knowledge_service = StructuredKnowledgeService(intelligence_service.SessionLocal)
        
        if request.method == 'GET':
            files = structured_knowledge_service.get_knowledge_files(user_email)
            return jsonify(files)
        
        elif request.method == 'POST':
            if 'file' not in request.files:
                return jsonify({'error': 'No file part', 'success': False}), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No selected file', 'success': False}), 400
            
            if not structured_knowledge_service.allowed_file(file.filename):
                return jsonify({'error': 'File type not allowed', 'success': False}), 400
            
            description = request.form.get('description', '')
            category = request.form.get('category', 'general')
            
            # Initialize structured knowledge service for this request
            from services.structured_knowledge_service import StructuredKnowledgeService
            structured_knowledge_service = StructuredKnowledgeService(intelligence_service.SessionLocal)
            file_data = structured_knowledge_service.upload_knowledge_file(user_email, file, description, category)
            
            if not file_data:
                return jsonify({'error': 'Failed to upload file', 'success': False}), 500
            
            return jsonify({'success': True, 'file': file_data})
    
    @app.route('/api/knowledge-files/<file_id>', methods=['GET', 'DELETE'])
    def api_knowledge_file(file_id):
        if 'user_email' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_email = session.get('user_email')
        
        # Initialize intelligence service
        from services.intelligence_service import IntelligenceService
        intelligence_service = IntelligenceService(database_url, claude_client)
        
        # Initialize structured knowledge service
        from services.structured_knowledge_service import StructuredKnowledgeService
        structured_knowledge_service = StructuredKnowledgeService(intelligence_service.SessionLocal)
        
        if request.method == 'GET':
            file_data = structured_knowledge_service.get_knowledge_file(user_email, file_id)
            if not file_data:
                return jsonify({'error': 'File not found'}), 404
            return jsonify(file_data)
        
        elif request.method == 'DELETE':
            success = structured_knowledge_service.delete_knowledge_file(user_email, file_id)
            if not success:
                return jsonify({'error': 'File not found', 'success': False}), 404
            return jsonify({'success': True})

    # Register new blueprints
    try:
        # Import the routes modules
        from routes import tasks, knowledge_graph, email_knowledge
        
        # Register the blueprints
        # Note: Each blueprint might have a different variable name
        # Check the actual variable names in each module
        try:
            app.register_blueprint(tasks.tasks_bp)
            logging.info("Registered tasks blueprint")
        except AttributeError:
            logging.warning("Could not find tasks.tasks_bp blueprint")
            
        try:
            app.register_blueprint(knowledge_graph.kg_bp)
            logging.info("Registered knowledge_graph blueprint")
        except AttributeError:
            logging.warning("Could not find knowledge_graph.kg_bp blueprint")
            
        try:
            app.register_blueprint(email_knowledge.email_knowledge_bp)
            logging.info("Registered email_knowledge blueprint")
        except AttributeError:
            logging.warning("Could not find email_knowledge.email_knowledge_bp blueprint")
        
        logging.info("Finished blueprint registration")
    except ImportError as e:
        logging.error(f"Error importing route modules: {str(e)}")
    except Exception as e:
        logging.error(f"Error registering blueprints: {str(e)}")
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))