import os
import sys
import time
import pathlib
import secrets
import requests
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Add the project root directory to Python's import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))  

load_dotenv()  # Load environment variables from .env file

from flask import Flask, session, render_template, redirect, url_for, request, jsonify, send_file
from flask_session import Session
from werkzeug.middleware.proxy_fix import ProxyFix
import tempfile
import logging
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables for tracking sync status
sync_status = {
    'is_syncing': False,
    'progress': 0,
    'user_email': '',
    'sync_type': '',
    'last_sync': None
}

# Initialize Claude client
from anthropic import Anthropic
claude_client = Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))

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
    Session(app)
    
    # Google OAuth configuration
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    GOOGLE_AUTH_URI = 'https://accounts.google.com/o/oauth2/auth'
    GOOGLE_TOKEN_URI = 'https://oauth2.googleapis.com/token'
    GOOGLE_REDIRECT_URI = 'http://127.0.0.1:8080/login/google/authorized'
    
    @app.route('/')
    def index():
        return render_template('index.html', name=session.get('user_name', 'User'))
    
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
            
            # Store token in session
            session['google_oauth_token'] = {
                'access_token': token_data['access_token'],
                'refresh_token': token_data.get('refresh_token'),
                'token_type': token_data['token_type'],
                'expires_at': int(time.time()) + token_data['expires_in']
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
        
        # Check if user has connected Gmail
        gmail_connected = 'google_oauth_token' in session
        last_sync = session.get('last_email_sync', 'Never')
        
        # Get sync status for the current user
        global sync_status
        current_sync_status = None
        if sync_status.get('user_email') == session.get('user_email'):
            current_sync_status = sync_status
        
        return render_template('settings.html', 
                           name=session.get('user_name', 'User'),
                           gmail_connected=gmail_connected,
                           last_sync=last_sync,
                           sync_status=current_sync_status,
                           email_sync_frequency=session.get('email_sync_frequency', 24),
                           email_days_back=session.get('email_days_back', 30),
                           urgent_alerts_enabled=session.get('urgent_alerts_enabled', True))
    
    @app.route('/email-insights')
    def email_insights():
        if 'user_email' not in session:
            return redirect(url_for('login'))
        
        user_email = session['user_email']
        
        # Initialize intelligence service
        database_url = os.environ.get('DATABASE_URL', 'sqlite:///chief_of_staff.db')
        from backend.services.intelligence_service import IntelligenceService
        intelligence_service = IntelligenceService(database_url, claude_client)
        
        # Check if a sync is in progress for this user
        global sync_status
        if sync_status.get('user_email') == user_email and sync_status.get('is_syncing', False):
            # Redirect to sync progress page if sync is in progress
            return render_template('sync_in_progress.html',
                                name=session.get('user_name', 'User'),
                                sync_type='Email Intelligence',
                                progress=sync_status.get('progress', 0))
        
        # Get insights from database
        insights = intelligence_service.get_user_insights(user_email)
        
        if insights.get('status') == 'no_data':
            return render_template('email_insights.html',
                                name=session.get('user_name', 'User'),
                                insights="<div class='alert alert-info'>No email insights available yet. Please <a href='/sync-emails'>sync your emails</a> first.</div>")
        
        # Debug logging
        logger.info(f"Insights keys: {list(insights.keys())}")
        logger.info(f"Key relationships count: {len(insights.get('key_relationships', []))}")
        
        # Set the last sync time in the session for display
        if 'generated_at' in insights:
            session['last_email_sync'] = insights['generated_at']
        

        

        

        

        

        

        

        
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
        
        # Initialize intelligence service
        database_url = os.environ.get('DATABASE_URL', 'sqlite:///chief_of_staff.db')
        from backend.services.intelligence_service import IntelligenceService
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
    
    @app.route('/api/sync-status')
    def api_sync_status():
        global sync_status
        
        if 'user_email' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
            
        # Only return sync status for the current user
        if sync_status.get('user_email') == session.get('user_email'):
            # If sync is complete, update session with insights
            if not sync_status.get('is_syncing') and sync_status.get('progress') == 100:
                if 'email_insights' in sync_status:
                    session['email_insights'] = sync_status['email_insights']
                    session['last_email_sync'] = sync_status.get('last_sync', datetime.now().strftime("%Y-%m-%d %H:%M"))
                
            return jsonify({
                'is_syncing': sync_status.get('is_syncing', False),
                'progress': sync_status.get('progress', 0),
                'sync_type': sync_status.get('sync_type', ''),
                'redirect': '/email-insights' if not sync_status.get('is_syncing') and sync_status.get('progress') == 100 else None
            })
        else:
            # No sync status for this user
            # Instead of redirecting to settings, redirect to email-insights
            # This prevents the redirect loop when returning from settings page
            return jsonify({
                'is_syncing': False,
                'progress': 0,
                'sync_type': '',
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
                    model="claude-3-opus-20240229",
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
                    model="claude-3-opus-20240229",
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
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=8080, debug=True)