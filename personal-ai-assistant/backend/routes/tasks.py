"""
API routes for task management.
These routes handle creating, retrieving, updating, and deleting tasks.
"""

from flask import Blueprint, request, jsonify, session
import logging
import uuid
from datetime import datetime

from services.intelligence_service import IntelligenceService
from services.knowledge_integration_service import KnowledgeIntegrationService
from models.database.tasks import Task
# Import claude_client from main module
from main import claude_client

logger = logging.getLogger(__name__)

# Create blueprint
tasks_bp = Blueprint('tasks', __name__)

# Get database URL from main app
database_url = None

def init_routes(app, db_url):
    """Initialize routes with database URL"""
    global database_url
    database_url = db_url
    app.register_blueprint(tasks_bp, url_prefix='/api')


@tasks_bp.route('/tasks', methods=['GET'])
def get_tasks():
    """Get tasks for the current user"""
    # Get user email from session
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'error': 'User not logged in'}), 401
    
    # Get query parameters
    status = request.args.get('status')
    limit = int(request.args.get('limit', 50))
    offset = int(request.args.get('offset', 0))
    
    # Initialize services
    intelligence_service = IntelligenceService(database_url, claude_client)
    knowledge_integration_service = KnowledgeIntegrationService(intelligence_service.SessionLocal)
    
    # Get tasks
    tasks = knowledge_integration_service.get_tasks_for_user(
        user_email=user_email,
        status=status,
        limit=limit,
        offset=offset
    )
    
    return jsonify({'success': True, 'tasks': tasks})


@tasks_bp.route('/tasks', methods=['POST'])
def create_task():
    """Create a new task"""
    # Get user email from session
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'error': 'User not logged in'}), 401
    
    # Get task data from request
    task_data = request.json
    if not task_data or 'description' not in task_data:
        return jsonify({'error': 'Task description is required'}), 400
    
    # Create database session
    intelligence_service = IntelligenceService(database_url, claude_client)
    session_db = intelligence_service.SessionLocal()
    
    try:
        # Parse deadline if it's a string
        deadline = None
        if task_data.get('deadline'):
            try:
                deadline = datetime.fromisoformat(task_data['deadline'])
            except (ValueError, TypeError):
                deadline = None
        
        # Create task object
        task = Task(
            id=str(uuid.uuid4()),
            user_email=user_email,
            description=task_data.get('description', ''),
            deadline=deadline,
            status="pending",
            priority=task_data.get('priority', 'medium'),
            source_type="manual",
            related_people=task_data.get('related_people', []),
            related_project_id=task_data.get('related_project_id')
        )
        
        session_db.add(task)
        session_db.commit()
        
        logger.info(f"Created task for user {user_email}: {task.description[:30]}...")
        return jsonify({'success': True, 'task': task.to_dict()})
    except Exception as e:
        session_db.rollback()
        logger.error(f"Error creating task: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        session_db.close()


@tasks_bp.route('/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    """Get a specific task by ID"""
    # Get user email from session
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'error': 'User not logged in'}), 401
    
    # Create database session
    intelligence_service = IntelligenceService(database_url, claude_client)
    session_db = intelligence_service.SessionLocal()
    
    try:
        # Get task
        task = session_db.query(Task).filter(
            Task.id == task_id,
            Task.user_email == user_email
        ).first()
        
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        return jsonify({'success': True, 'task': task.to_dict()})
    except Exception as e:
        logger.error(f"Error retrieving task: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        session_db.close()


@tasks_bp.route('/tasks/<task_id>', methods=['PUT'])
def update_task(task_id):
    """Update a task"""
    # Get user email from session
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'error': 'User not logged in'}), 401
    
    # Get task data from request
    task_data = request.json
    if not task_data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Create database session
    intelligence_service = IntelligenceService(database_url, claude_client)
    session_db = intelligence_service.SessionLocal()
    
    try:
        # Get task
        task = session_db.query(Task).filter(
            Task.id == task_id,
            Task.user_email == user_email
        ).first()
        
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # Update task fields
        if 'description' in task_data:
            task.description = task_data['description']
        
        if 'status' in task_data:
            task.status = task_data['status']
            if task.status == 'completed' and not task.completed_at:
                task.completed_at = datetime.utcnow()
            elif task.status != 'completed':
                task.completed_at = None
        
        if 'priority' in task_data:
            task.priority = task_data['priority']
        
        if 'deadline' in task_data:
            try:
                task.deadline = datetime.fromisoformat(task_data['deadline']) if task_data['deadline'] else None
            except (ValueError, TypeError):
                pass
        
        if 'related_people' in task_data:
            task.related_people = task_data['related_people']
        
        if 'related_project_id' in task_data:
            task.related_project_id = task_data['related_project_id']
        
        # Update timestamp
        task.updated_at = datetime.utcnow()
        
        # Commit changes
        session_db.commit()
        
        logger.info(f"Updated task {task_id} for user {user_email}")
        return jsonify({'success': True, 'task': task.to_dict()})
    except Exception as e:
        session_db.rollback()
        logger.error(f"Error updating task: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        session_db.close()


@tasks_bp.route('/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Delete a task"""
    # Get user email from session
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'error': 'User not logged in'}), 401
    
    # Create database session
    intelligence_service = IntelligenceService(database_url, claude_client)
    session_db = intelligence_service.SessionLocal()
    
    try:
        # Get task
        task = session_db.query(Task).filter(
            Task.id == task_id,
            Task.user_email == user_email
        ).first()
        
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # Delete task
        session_db.delete(task)
        session_db.commit()
        
        logger.info(f"Deleted task {task_id} for user {user_email}")
        return jsonify({'success': True})
    except Exception as e:
        session_db.rollback()
        logger.error(f"Error deleting task: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        session_db.close()
