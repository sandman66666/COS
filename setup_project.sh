#!/bin/bash

# Personal AI Assistant - Project Setup Script
# This script creates the complete folder structure and initializes files

set -e  # Exit on any error

PROJECT_NAME="personal-ai-assistant"
echo "🚀 Setting up $PROJECT_NAME..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create main project directory
echo -e "${BLUE}📁 Creating project structure...${NC}"
mkdir -p $PROJECT_NAME
cd $PROJECT_NAME

# Backend structure
echo -e "${YELLOW}📂 Creating backend structure...${NC}"
mkdir -p backend/{core,integrations,api,models,services,utils,tasks,tests}
mkdir -p backend/core/{claude_integration,trigger_engine,data_orchestrator}
mkdir -p backend/integrations/{clickup,claude_native}
mkdir -p backend/api/{routes,middleware}
mkdir -p backend/models/{database,schemas}
mkdir -p backend/tests/{unit,integration,fixtures}

# Frontend structure
echo -e "${YELLOW}📂 Creating frontend structure...${NC}"
mkdir -p frontend/src/{components,pages,hooks,services,utils,styles}
mkdir -p frontend/src/components/{common,chat,triggers,insights,integrations}
mkdir -p frontend/public

# Templates and static (for Flask)
mkdir -p templates static

# Infrastructure and docs
mkdir -p {scripts,docs,heroku}
mkdir -p docs/{deployment,architecture,user_guides}

# Create all __init__.py files
echo -e "${YELLOW}🐍 Creating Python package files...${NC}"
find backend -type d -exec touch {}/__init__.py \;

# Create core configuration files
echo -e "${BLUE}⚙️  Creating configuration files...${NC}"

# .env.example
cat > .env.example << 'EOF'
# Flask Configuration
SECRET_KEY=your-secret-key-here
FLASK_ENV=development
DATABASE_URL=postgresql://username:password@localhost/dbname

# Claude API
ANTHROPIC_API_KEY=your-claude-api-key-here

# Google OAuth (for token management)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# ClickUp (optional)
CLICKUP_API_KEY=your-clickup-key-if-needed

# Heroku
PORT=5000
EOF

# requirements.txt
cat > requirements.txt << 'EOF'
# Web Framework
Flask==3.0.0
Flask-Session==0.5.0
Flask-SQLAlchemy==3.1.1
gunicorn==21.2.0

# Claude Integration  
anthropic==0.8.1
httpx==0.26.0

# Database
psycopg2-binary==2.9.9
SQLAlchemy==2.0.23
alembic==1.13.1

# Authentication (Google OAuth)
Flask-Dance==7.0.1
google-auth==2.25.2
google-auth-oauthlib==1.2.0
google-api-python-client==2.111.0

# Task Scheduling & Background Jobs
celery==5.3.0
redis==5.0.1
schedule==1.2.2

# Utilities
python-dotenv==1.0.0
PyYAML==6.0.1
requests==2.31.0
python-dateutil==2.8.2

# Development & Testing
pytest==8.0.2
pytest-flask==1.3.0
pytest-cov==4.1.0

# Production
Werkzeug==3.0.1
EOF

# Procfile for Heroku
cat > Procfile << 'EOF'
web: gunicorn backend.main:app --workers 1 --log-level info
worker: celery -A backend.tasks.celery_app worker --loglevel=info
EOF

# runtime.txt for Heroku
cat > runtime.txt << 'EOF'
python-3.11.6
EOF

# .gitignore
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Environment
.env
.venv
env/
venv/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Database
*.db
*.sqlite

# User data
user_data/
temp/

# Node modules (if you add frontend build)
node_modules/
npm-debug.log*

# Flask session
flask_session/

# Heroku
.heroku/
EOF

# Main backend entry point
cat > backend/main.py << 'EOF'
import os
from datetime import timedelta
from flask import Flask, session
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
    app.config['PREFERRED_URL_SCHEME'] = 'https'
    app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLASK_ENV') != 'development'
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_FILE_DIR'] = os.path.join(tempfile.gettempdir(), 'flask_session')
    
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
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/gmail.readonly"
        ],
        redirect_to='index'
    )
    app.register_blueprint(google_bp, url_prefix='/login')
    
    # Initialize core services
    from backend.core.claude_integration.claude_client import ClaudeClient
    claude_client = ClaudeClient(api_key=os.getenv('ANTHROPIC_API_KEY'))
    app.claude_client = claude_client
    
    # Register routes
    from backend.api.routes import register_routes
    register_routes(app)
    
    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
EOF

# Configuration settings
cat > backend/config/settings.py << 'EOF'
import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///app.db')
    
    # Session configuration
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    
    # Claude API
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
    
    # Google OAuth
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    
    # User data directory
    USER_DATA_DIR = os.getenv('USER_DATA_DIR', 'user_data')

class DevelopmentConfig(Config):
    DEBUG = True
    FLASK_ENV = 'development'

class ProductionConfig(Config):
    DEBUG = False
    FLASK_ENV = 'production'
EOF

# Claude client (main integration)
cat > backend/core/claude_integration/claude_client.py << 'EOF'
import anthropic
from typing import Dict, List, Optional
import json
import os
from datetime import datetime

class ClaudeClient:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is required")
        
        self.client = anthropic.Anthropic(api_key=api_key)
        self.conversation_history = {}  # Store by user_email
        self.max_history = 20  # Keep last 20 messages per user
    
    def send_message(self, user_email: str, message: str, context_data: Dict = None) -> str:
        """Send message to Claude with user context"""
        
        # Initialize conversation history for new users
        if user_email not in self.conversation_history:
            self.conversation_history[user_email] = []
        
        # Build system prompt with context
        system_prompt = self._build_system_prompt(user_email, context_data)
        
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
            return f"Error: {str(e)}"
    
    def _build_system_prompt(self, user_email: str, context_data: Dict = None) -> str:
        """Build system prompt with user context"""
        
        prompt = f"""You are a personalized AI assistant for {user_email}.

You have access to their:
- Gmail (use your native Gmail integration when they ask about emails)
- Google Calendar (use your native Calendar integration for scheduling questions)
- ClickUp tasks and projects (provided in context below)

"""
        
        # Add current context data
        if context_data:
            if context_data.get('tasks_summary'):
                prompt += f"\nCURRENT TASKS FROM CLICKUP:\n{context_data['tasks_summary']}\n"
            
            if context_data.get('calendar_summary'):
                prompt += f"\nCALENDAR SUMMARY:\n{context_data['calendar_summary']}\n"
        
        prompt += """
When users ask about:
- Emails: Use your Gmail integration to check their actual emails
- Calendar/Schedule: Use your Calendar integration to check their actual events  
- Tasks/Projects: Use the ClickUp data provided in context above

Be conversational, helpful, and proactive in suggesting actions based on their data.
"""
        
        return prompt
    
    def clear_history(self, user_email: str):
        """Clear conversation history for a user"""
        if user_email in self.conversation_history:
            del self.conversation_history[user_email]
EOF

# Smart data fetcher
cat > backend/core/data_orchestrator/smart_fetcher.py << 'EOF'
import os
import json
from datetime import datetime
from typing import Dict, Any

class SmartDataFetcher:
    def __init__(self, user_data_dir: str):
        self.user_data_dir = user_data_dir
    
    def fetch_context_for_prompt(self, user_email: str, prompt: str) -> Dict[str, Any]:
        """Intelligently fetch only relevant data based on prompt analysis"""
        
        context = {}
        prompt_lower = prompt.lower()
        
        # Check if prompt needs task data
        task_keywords = ['task', 'todo', 'project', 'clickup', 'deadline', 'due', 'work', 'priority']
        if any(word in prompt_lower for word in task_keywords):
            context['tasks_summary'] = self._get_tasks_context(user_email)
        
        # Check if prompt needs calendar data (Claude will handle this natively)
        calendar_keywords = ['meeting', 'calendar', 'schedule', 'appointment', 'today', 'tomorrow', 'week']
        if any(word in prompt_lower for word in calendar_keywords):
            context['calendar_summary'] = "Calendar data will be accessed via Claude's native integration."
        
        return context
    
    def _get_tasks_context(self, user_email: str) -> str:
        """Get ClickUp tasks context from sync data"""
        try:
            sync_dir = os.path.join(self.user_data_dir, user_email, 'sync')
            tasks_file = os.path.join(sync_dir, 'clickup_summary.txt')
            
            if os.path.exists(tasks_file):
                with open(tasks_file, 'r') as f:
                    content = f.read()
                    return content if content.strip() else "No current task data available."
            
            return "No task data found. Please sync ClickUp in settings."
            
        except Exception as e:
            return f"Error loading tasks: {str(e)}"
EOF

# Route registration
cat > backend/api/routes/__init__.py << 'EOF'
from .main_routes import main_bp
from .chat_routes import chat_bp

def register_routes(app):
    """Register all route blueprints"""
    app.register_blueprint(main_bp)
    app.register_blueprint(chat_bp, url_prefix='/api')
EOF

# Main routes (your existing template routes)
cat > backend/api/routes/main_routes.py << 'EOF'
from flask import Blueprint, render_template, session, redirect, url_for
from flask_dance.contrib.google import google
from flask_dance.consumer import oauth_authorized
from flask_dance.contrib.google import make_google_blueprint

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if 'user_email' not in session:
        return redirect(url_for('google.login'))
    
    return render_template('index.html', name=session.get('user_name'))

@main_bp.route('/settings')
def settings():
    if 'user_email' not in session:
        return redirect(url_for('google.login'))
    
    return render_template('settings.html', name=session.get('user_name'))

@main_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.index'))

# OAuth callback handler
@oauth_authorized.connect
def google_logged_in(blueprint, token):
    if not token:
        return False

    resp = blueprint.session.get('/oauth2/v2/userinfo')
    if not resp.ok:
        return False

    google_info = resp.json()
    
    # Store user info in session
    session.clear()
    session['user_email'] = google_info['email']
    session['user_name'] = google_info['name']
    session['google_id'] = google_info['id']
    session['google_token'] = token['access_token']
    session.permanent = True
    
    return False
EOF

# Chat routes
cat > backend/api/routes/chat_routes.py << 'EOF'
from flask import Blueprint, request, jsonify, session, current_app
from backend.core.data_orchestrator.smart_fetcher import SmartDataFetcher
import os

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/chat', methods=['POST'])
def chat():
    if 'user_email' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_email = session['user_email']
    message = request.json.get('message')
    
    if not message:
        return jsonify({'error': 'No message provided'}), 400
    
    try:
        # Get Claude client from app context
        claude_client = current_app.claude_client
        
        # Fetch relevant context based on prompt
        user_data_dir = os.getenv('USER_DATA_DIR', 'user_data')
        data_fetcher = SmartDataFetcher(user_data_dir)
        context = data_fetcher.fetch_context_for_prompt(user_email, message)
        
        # Send to Claude with context
        response = claude_client.send_message(user_email, message, context)
        
        return jsonify({'response': response})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
EOF

# Basic HTML template
cat > templates/base.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Personal AI Assistant{% endblock %}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            background-color: #fff;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .btn {
            background-color: #007bff;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
        }
        .btn:hover {
            background-color: #0056b3;
        }
        .btn-danger {
            background-color: #dc3545;
        }
        .btn-danger:hover {
            background-color: #c82333;
        }
    </style>
    {% block extra_styles %}{% endblock %}
</head>
<body>
    <div class="container">
        {% block content %}{% endblock %}
    </div>
    {% block scripts %}{% endblock %}
</body>
</html>
EOF

# Main chat template
cat > templates/index.html << 'EOF'
{% extends "base.html" %}
{% block title %}Chat - Personal AI Assistant{% endblock %}

{% block extra_styles %}
<style>
    .chat-container {
        background-color: #fff;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        height: 600px;
        display: flex;
        flex-direction: column;
    }
    .messages {
        flex: 1;
        overflow-y: auto;
        padding: 20px;
        display: flex;
        flex-direction: column;
        gap: 10px;
    }
    .message {
        padding: 12px 16px;
        border-radius: 12px;
        max-width: 70%;
        word-wrap: break-word;
    }
    .message.user {
        background-color: #007bff;
        color: white;
        align-self: flex-end;
    }
    .message.assistant {
        background-color: #f1f3f5;
        color: #333;
        align-self: flex-start;
    }
    .input-container {
        padding: 20px;
        border-top: 1px solid #eee;
        display: flex;
        gap: 10px;
    }
    #messageInput {
        flex: 1;
        padding: 12px;
        border: 1px solid #ddd;
        border-radius: 4px;
        font-size: 16px;
    }
    #sendButton {
        background-color: #007bff;
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 16px;
    }
    #sendButton:hover:not(:disabled) {
        background-color: #0056b3;
    }
    #sendButton:disabled {
        opacity: 0.6;
        cursor: not-allowed;
    }
</style>
{% endblock %}

{% block content %}
<div class="header">
    <h1>Hi {{ name }}! Chat with Claude</h1>
    <div>
        <a href="{{ url_for('main.settings') }}" class="btn">Settings</a>
        <a href="{{ url_for('main.logout') }}" class="btn btn-danger">Logout</a>
    </div>
</div>

<div class="chat-container">
    <div id="messages" class="messages">
        <div class="message assistant">
            Hello! I'm Claude, your personalized AI assistant. I have access to your Gmail, Calendar, and ClickUp data. How can I help you today?
        </div>
    </div>
    
    <div class="input-container">
        <input type="text" id="messageInput" placeholder="Type your message..." autofocus>
        <button id="sendButton">Send</button>
    </div>
</div>

<script>
    const messagesDiv = document.getElementById('messages');
    const messageInput = document.getElementById('messageInput');
    const sendButton = document.getElementById('sendButton');
    
    function addMessage(content, isUser) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user' : 'assistant'}`;
        messageDiv.textContent = content;
        messagesDiv.appendChild(messageDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
    
    async function sendMessage() {
        const message = messageInput.value.trim();
        if (!message) return;
        
        addMessage(message, true);
        messageInput.value = '';
        messageInput.disabled = true;
        sendButton.disabled = true;
        
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                addMessage(data.response, false);
            } else {
                addMessage(`Error: ${data.error}`, false);
            }
        } catch (error) {
            addMessage(`Error: ${error.message}`, false);
        } finally {
            messageInput.disabled = false;
            sendButton.disabled = false;
            messageInput.focus();
        }
    }
    
    sendButton.addEventListener('click', sendMessage);
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            sendMessage();
        }
    });
</script>
{% endblock %}
EOF

# Settings template placeholder
cat > templates/settings.html << 'EOF'
{% extends "base.html" %}
{% block title %}Settings - Personal AI Assistant{% endblock %}

{% block content %}
<div class="header">
    <h1>Settings</h1>
    <div>
        <a href="{{ url_for('main.index') }}" class="btn">Back to Chat</a>
        <a href="{{ url_for('main.logout') }}" class="btn btn-danger">Logout</a>
    </div>
</div>

<div style="background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
    <h2>Integrations</h2>
    <p>Settings page - will be enhanced with ClickUp integration, trigger management, etc.</p>
    <p><strong>User:</strong> {{ name }}</p>
</div>
{% endblock %}
EOF

# Setup script for easy startup
cat > scripts/setup.sh << 'EOF'
#!/bin/bash

echo "🚀 Setting up Personal AI Assistant..."

# Create virtual environment
echo "📦 Creating virtual environment..."
python -m venv venv

# Activate virtual environment
echo "🔌 Activating virtual environment..."
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

# Install dependencies
echo "📚 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create .env from example
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your API keys!"
fi

# Create user data directory
mkdir -p user_data

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your API keys"
echo "2. Run: python backend/main.py"
echo "3. Visit: http://localhost:5000"
EOF

chmod +x scripts/setup.sh

# Run script
cat > scripts/run.sh << 'EOF'
#!/bin/bash

# Activate virtual environment
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

# Run the application
python backend/main.py
EOF

chmod +x scripts/run.sh

# README
cat > README.md << 'EOF'
# Personal AI Assistant

A Claude-powered personal assistant that integrates with your Gmail, Calendar, and ClickUp to provide intelligent insights and task management.

## Features

- 💬 **Chat with Claude**: Natural conversation with access to your data
- 📧 **Gmail Integration**: Claude can read and analyze your emails
- 📅 **Calendar Integration**: Schedule analysis and meeting insights  
- ✅ **ClickUp Integration**: Task management and project tracking
- 🔄 **Smart Data Fetching**: Only loads relevant data based on your prompts
- 📱 **Proactive Triggers**: Save prompts to run automatically

## Quick Start

1. **Run the setup script:**
   ```bash
   ./scripts/setup.sh
   ```

2. **Configure your API keys in `.env`:**
   ```bash
   ANTHROPIC_API_KEY=your-claude-api-key
   GOOGLE_CLIENT_ID=your-google-client-id
   GOOGLE_CLIENT_SECRET=your-google-client-secret
   ```

3. **Run the application:**
   ```bash
   ./scripts/run.sh
   ```

4. **Visit http://localhost:5000**

## Architecture

- **Backend**: Flask + Claude API
- **Frontend**: HTML/CSS/JavaScript
- **Database**: PostgreSQL (SQLite for development)
- **Deployment**: Heroku-ready

## Development

The project follows a modular architecture:

- `backend/core/claude_integration/` - Claude API client
- `backend/core/data_orchestrator/` - Smart data fetching
- `backend/integrations/` - External service integrations
- `backend/api/routes/` - API endpoints
- `templates/` - HTML templates

## Deployment

Ready for Heroku deployment with included `Procfile` and configuration.
EOF

echo -e "${GREEN}✅ Project setup complete!${NC}"
echo ""
echo -e "${BLUE}📁 Created project structure:${NC}"
tree -L 3 $PROJECT_NAME 2>/dev/null || find $PROJECT_NAME -type d | head -20

echo ""
echo -e "${YELLOW}🚀 Next steps:${NC}"
echo "1. cd $PROJECT_NAME"
echo "2. ./scripts/setup.sh"
echo "3. Edit .env file with your API keys"
echo "4. ./scripts/run.sh"
echo ""
echo -e "${GREEN}🎉 Happy coding!${NC}"
