import os
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

from flask import Flask, session, render_template, redirect, url_for, request, jsonify
from flask_dance.contrib.google import make_google_blueprint
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
    app.config['SESSION_FILE_DIR'] = tempfile.gettempdir()
    app.config['SESSION_PERMANENT'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
    Session(app)
    
    # Configure Google OAuth
    google_bp = make_google_blueprint(
        client_id=os.environ.get('GOOGLE_CLIENT_ID'),
        client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
        scope=[
            'openid',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile',
            'https://www.googleapis.com/auth/gmail.readonly'
        ],
        redirect_url='/login/google/authorized',
        prefix='/login'
    )
    app.register_blueprint(google_bp, url_prefix='/login')
    
    @app.route('/')
    def index():
        return render_template('index.html', name=session.get('user_name', 'User'))
    
    @app.route('/login')
    def login():
        return redirect(url_for('google.login'))
    
    @app.route('/login/google/authorized')
    def authorized():
        if not google_bp.session.authorized:
            return redirect(url_for('google.login'))
        
        resp = google_bp.session.get('https://www.googleapis.com/oauth2/v1/userinfo')
        if not resp.ok:
            return redirect(url_for('google.login'))
        
        user_info = resp.json()
        session['user_name'] = user_info.get('name', 'User')
        session['user_email'] = user_info.get('email')
        session['google_oauth_token'] = {
            'access_token': google_bp.token['access_token'],
            'refresh_token': google_bp.token.get('refresh_token'),
            'token_type': google_bp.token['token_type'],
            'expires_at': google_bp.token['expires_at']
        }
        
        return redirect(url_for('index'))
    
    @app.route('/chat')
    def chat():
        if 'user_email' not in session:
            return redirect(url_for('google.login'))
        
        return render_template('chat.html', name=session.get('user_name', 'User'))
    
    @app.route('/settings')
    def settings():
        if 'user_email' not in session:
            return redirect(url_for('google.login'))
        
        return render_template('settings.html', 
                              name=session.get('user_name', 'User'),
                              email=session.get('user_email', ''),
                              gmail_connected='google_oauth_token' in session,
                              last_email_sync=session.get('last_email_sync', 'Never'),
                              email_sync_frequency=session.get('email_sync_frequency', 24),
                              email_days_back=session.get('email_days_back', 30),
                              urgent_alerts_enabled=session.get('urgent_alerts_enabled', True))
    
    @app.route('/email-insights')
    def email_insights():
        if 'user_email' not in session or 'google_oauth_token' not in session:
            return redirect(url_for('google.login'))
        
        user_email = session['user_email']
        access_token = session['google_oauth_token']['access_token']
        
        # Check if currently syncing
        global sync_status
        if sync_status['is_syncing'] and sync_status['user_email'] == user_email:
            return render_template('sync_in_progress.html',
                                  name=session.get('user_name', 'User'),
                                  sync_type=sync_status['sync_type'],
                                  progress=sync_status['progress'])
        
        # Check if we need to sync first
        last_sync = session.get('last_email_sync')
        if not last_sync:
            # Redirect to sync emails first
            return render_template('email_insights.html',
                                 name=session.get('user_name', 'User'),
                                 insights="<div class='alert alert-info'>No email insights available yet. Please <a href='/sync-emails'>sync your emails</a> first.</div>")
        
        try:
            # Initialize the EmailIntelligence module
            from backend.core.claude_integration.email_intelligence import EmailIntelligence
            email_intelligence = EmailIntelligence(claude_client)
            
            # Get email insights using the Gmail connector
            insights = email_intelligence.analyze_recent_emails(user_email, access_token, days_back=30)
            
            # Format the insights for display
            formatted_insights = f"""<div class='card mb-4'>
                <div class='card-header bg-primary text-white'>
                    <h2 class='mb-0'>Email Intelligence Report</h2>
                </div>
                <div class='card-body'>
                    <p class='lead'>Analysis of your email communications from the last 30 days</p>
                    
                    {"<div class='alert alert-info'><i class='fas fa-info-circle'></i> " + insights.get('message', '') + "</div>" if insights.get('message') else ""}
                    
                    <div class='card mb-3'>
                        <div class='card-header bg-light'>
                            <h3 class='mb-0'><i class='fas fa-users'></i> Key Relationships</h3>
                        </div>
                        <div class='card-body'>
                            <ul class='list-group list-group-flush'>"""
            
            if insights.get('key_relationships'):
                for relationship in insights.get('key_relationships', []):
                    if isinstance(relationship, dict):
                        name = relationship.get('name', 'Unknown')
                        email = relationship.get('email', '')
                        context = relationship.get('context', '')
                        formatted_insights += f"""<li class='list-group-item'>
                            <strong>{name}</strong> {f"<span class='text-muted'>({email})</span>" if email else ""}
                            <p class='mb-0'>{context}</p>
                        </li>"""
                    else:
                        formatted_insights += f"<li class='list-group-item'>{relationship}</li>"
            else:
                formatted_insights += "<li class='list-group-item'>No key relationships identified</li>"
            
            formatted_insights += """</ul>
                        </div>
                    </div>
                    
                    <div class='card mb-3'>
                        <div class='card-header bg-light'>
                            <h3 class='mb-0'><i class='fas fa-tasks'></i> Active Projects</h3>
                        </div>
                        <div class='card-body'>
                            <ul class='list-group list-group-flush'>"""
            
            if insights.get('active_projects'):
                for project in insights.get('active_projects', []):
                    if isinstance(project, dict):
                        name = project.get('name', 'Unknown')
                        description = project.get('description', '')
                        formatted_insights += f"""<li class='list-group-item'>
                            <strong>{name}</strong>
                            <p class='mb-0'>{description}</p>
                        </li>"""
                    else:
                        formatted_insights += f"<li class='list-group-item'>{project}</li>"
            else:
                formatted_insights += "<li class='list-group-item'>No active projects identified</li>"
            
            formatted_insights += """</ul>
                        </div>
                    </div>
                    
                    <div class='card mb-3'>
                        <div class='card-header bg-light'>
                            <h3 class='mb-0'><i class='fas fa-clipboard-check'></i> Action Items</h3>
                        </div>
                        <div class='card-body'>
                            <ul class='list-group list-group-flush'>"""
            
            if insights.get('action_items'):
                for action in insights.get('action_items', []):
                    if isinstance(action, dict):
                        description = action.get('description', 'Unknown')
                        deadline = action.get('deadline', '')
                        formatted_insights += f"""<li class='list-group-item'>
                            <strong>{description}</strong>
                            {f"<span class='badge bg-warning text-dark'>Due: {deadline}</span>" if deadline else ""}
                        </li>"""
                    else:
                        formatted_insights += f"<li class='list-group-item'>{action}</li>"
            else:
                formatted_insights += "<li class='list-group-item'>No action items identified</li>"
            
            formatted_insights += """</ul>
                        </div>
                    </div>
                    
                    <div class='card mb-3'>
                        <div class='card-header bg-light'>
                            <h3 class='mb-0'><i class='fas fa-info-circle'></i> Important Information</h3>
                        </div>
                        <div class='card-body'>
                            <ul class='list-group list-group-flush'>"""
            
            if insights.get('important_information'):
                for info in insights.get('important_information', []):
                    if isinstance(info, dict):
                        description = info.get('description', '')
                        formatted_insights += f"<li class='list-group-item'>{description}</li>"
                    else:
                        formatted_insights += f"<li class='list-group-item'>{info}</li>"
            else:
                formatted_insights += "<li class='list-group-item'>No important information identified</li>"
            
            formatted_insights += """</ul>
                        </div>
                    </div>
                </div>
            </div>"""
            
            # Update last sync time
            session['last_email_sync'] = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            return render_template('email_insights.html', 
                                  name=session.get('user_name', 'User'),
                                  insights=formatted_insights)
                
        except Exception as e:
            logger.error(f"Email insights error: {str(e)}")
            return jsonify({'error': f'Email insights error: {str(e)}'}), 500
    
    @app.route('/logout')
    def logout():
        session.clear()
        return redirect(url_for('index'))
    
    @app.route('/sync-emails')
    def sync_emails():
        if 'user_email' not in session or 'google_oauth_token' not in session:
            return redirect(url_for('google.login'))
            
        user_email = session['user_email']
        access_token = session['google_oauth_token']['access_token']
        days_back = session.get('email_days_back', 30)
        
        # Start sync in background thread
        def run_sync():
            global sync_status
            sync_status['is_syncing'] = True
            sync_status['progress'] = 0
            sync_status['user_email'] = user_email
            sync_status['sync_type'] = 'Email Intelligence'
            
            try:
                # Initialize the EmailIntelligence module
                import sys
                import os
                # Add the project root to the Python path
                sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                from core.claude_integration.email_intelligence import EmailIntelligence
                email_intelligence = EmailIntelligence(claude_client)
                
                # Simulate progress updates
                sync_status['progress'] = 10
                time.sleep(1)  # Simulate work
                
                # Fetch emails
                sync_status['progress'] = 30
                time.sleep(1)  # Simulate work
                
                # Analyze emails
                sync_status['progress'] = 60
                email_intelligence.analyze_recent_emails(user_email, access_token, days_back=days_back)
                time.sleep(1)  # Simulate work
                
                # Scan for urgent emails
                sync_status['progress'] = 80
                email_intelligence.scan_urgent_emails(user_email, access_token, hours_back=24)
                time.sleep(1)  # Simulate work
                
                # Identify key contacts
                sync_status['progress'] = 90
                email_intelligence.identify_key_contacts(user_email)
                time.sleep(1)  # Simulate work
                
                # Complete
                sync_status['progress'] = 100
                sync_status['last_sync'] = datetime.now().strftime("%Y-%m-%d %H:%M")
                # Store last sync time in session for email insights page
                session['last_email_sync'] = datetime.now().strftime("%Y-%m-%d %H:%M")
                
            except Exception as e:
                logger.error(f"Email sync error: {str(e)}")
            finally:
                sync_status['is_syncing'] = False
        
        # Start sync thread if not already syncing
        global sync_status
        if not sync_status['is_syncing']:
            sync_thread = threading.Thread(target=run_sync)
            sync_thread.daemon = True
            sync_thread.start()
            # Show sync progress page
            return render_template('sync_in_progress.html',
                                 name=session.get('user_name', 'User'),
                                 sync_type='Email Intelligence',
                                 progress=0)
        else:
            return jsonify({'error': 'Sync already in progress'}), 400
            
    @app.route('/api/sync-status')
    def get_sync_status():
        global sync_status
        # If sync is complete, redirect to email insights
        if not sync_status['is_syncing'] and sync_status['progress'] == 100:
            # Reset progress to avoid repeated redirects
            sync_status['progress'] = 0
            return jsonify({
                'is_syncing': False,
                'progress': 100,
                'user_email': sync_status['user_email'],
                'sync_type': sync_status['sync_type'],
                'redirect': '/email-insights'
            })
        return jsonify({
            'is_syncing': sync_status['is_syncing'],
            'progress': sync_status['progress'],
            'user_email': sync_status['user_email'],
            'sync_type': sync_status['sync_type']
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
            
    @app.route('/disconnect-gmail')
    def disconnect_gmail():
        if 'google_oauth_token' in session:
            del session['google_oauth_token']
        return redirect(url_for('settings'))
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=8080, debug=True)
