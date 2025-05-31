import os
from datetime import timedelta
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

from flask import Flask, session, render_template, redirect, url_for
from flask_dance.contrib.google import make_google_blueprint
from flask_session import Session
from werkzeug.middleware.proxy_fix import ProxyFix
import tempfile
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__, 
               template_folder='../templates',
               static_folder='../static')
    
    # Configuration
    app.secret_key = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_FILE_DIR'] = os.path.join(tempfile.gettempdir(), 'flask_session')
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)
    
    # Initialize extensions
    Session(app)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # Google OAuth setup
    google_bp = make_google_blueprint(
        client_id=os.getenv('GOOGLE_CLIENT_ID'),
        client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
        scope=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile"
        ],
        redirect_to='index'
    )
    app.register_blueprint(google_bp, url_prefix='/login')
    
    # OAuth callback
    from flask_dance.consumer import oauth_authorized
    from flask_dance.contrib.google import google
    
    @oauth_authorized.connect_via(google_bp)
    def google_logged_in(blueprint, token):
        if not token:
            logger.error("No token received from Google")
            return False
        resp = blueprint.session.get('/oauth2/v2/userinfo')
        if not resp.ok:
            logger.error(f"Failed to get user info: {resp.status_code}")
            return False
        google_info = resp.json()
        logger.info(f"User logged in: {google_info.get('email')}")
        session.clear()
        session['user_email'] = google_info['email']
        session['user_name'] = google_info['name']
        session['google_id'] = google_info['id']
        session.permanent = True
        return False
    
    # Routes
    @app.route('/')
    def index():
        if 'user_email' not in session:
            logger.info("User not authenticated, redirecting to Google login")
            return redirect(url_for('google.login'))
        return render_template('index.html', name=session.get('user_name', 'User'))
    
    @app.route('/logout')
    def logout():
        session.clear()
        return redirect(url_for('index'))
    
    @app.route('/debug')
    def debug():
        import os
        from flask_dance.contrib.google import google
        return f"""
        <h2>Debug Info</h2>
        <p><strong>Client ID:</strong> {os.getenv('GOOGLE_CLIENT_ID')}</p>
        <p><strong>Client Secret:</strong> {'SET' if os.getenv('GOOGLE_CLIENT_SECRET') else 'NOT SET'}</p>
        <p><strong>Google authorized:</strong> {google.authorized}</p>
        <p><strong>Session:</strong> {dict(session)}</p>
        <p><strong>App blueprints:</strong> {list(app.blueprints.keys())}</p>
        <hr>
        <p><a href="/login/google">Flask-Dance Login Link</a></p>
        <p><a href="/">Go to Home</a></p>
        """
    
    @app.route('/test-manual')
    def test_manual():
        from urllib.parse import urlencode
        client_id = os.getenv('GOOGLE_CLIENT_ID')
        redirect_uri = f"http://localhost:{os.getenv('PORT', '8080')}/login/google/authorized"
        
        params = {
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'scope': 'openid email profile',
            'response_type': 'code',
            'access_type': 'offline'
        }
        
        manual_url = f"https://accounts.google.com/o/oauth2/auth?{urlencode(params)}"
        
        return f"""
        <h2>Manual OAuth Test</h2>
        <p><strong>Client ID:</strong> {client_id}</p>
        <p><strong>Redirect URI:</strong> {redirect_uri}</p>
        <hr>
        <p><a href="{manual_url}" target="_blank">Manual OAuth URL (opens in new tab)</a></p>
        <p><a href="/login/google">Flask-Dance OAuth URL</a></p>
        <hr>
        <p>Compare these two URLs to see any differences</p>
        """
    
    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)