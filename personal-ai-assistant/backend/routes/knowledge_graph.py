"""
API routes for knowledge graph operations.
These routes handle retrieving entities and relationships from the knowledge graph.
"""

from flask import Blueprint, request, jsonify, session
import logging
import os

from services.intelligence_service import IntelligenceService
from services.knowledge_integration_service import KnowledgeIntegrationService

logger = logging.getLogger(__name__)

# Create blueprint
kg_bp = Blueprint('knowledge_graph', __name__)

# Get database URL from main app
database_url = None

def init_routes(app, db_url):
    """Initialize routes with database URL"""
    global database_url
    database_url = db_url
    app.register_blueprint(kg_bp, url_prefix='/api')


@kg_bp.route('/knowledge-graph/stats', methods=['GET'])
def get_knowledge_graph_stats():
    """Get statistics about the knowledge graph"""
    # Get user email from session
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'error': 'User not logged in'}), 401
    
    # Check if Neo4j is configured
    if not os.environ.get("NEO4J_URI") or not os.environ.get("NEO4J_USER") or not os.environ.get("NEO4J_PASSWORD"):
        return jsonify({
            'success': False,
            'error': 'Knowledge graph is not configured. Please set NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD environment variables.'
        }), 503
    
    # Initialize services
    intelligence_service = IntelligenceService(database_url)
    knowledge_integration_service = KnowledgeIntegrationService(intelligence_service.SessionLocal)
    
    # Get knowledge graph statistics
    stats = knowledge_integration_service.get_knowledge_graph_statistics()
    
    if 'error' in stats:
        return jsonify({'success': False, 'error': stats['error']}), 500
    
    return jsonify({'success': True, 'statistics': stats})


@kg_bp.route('/knowledge-graph/entities/<entity_type>', methods=['GET'])
def search_entities(entity_type):
    """Search for entities in the knowledge graph"""
    # Get user email from session
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'error': 'User not logged in'}), 401
    
    # Check if Neo4j is configured
    if not os.environ.get("NEO4J_URI") or not os.environ.get("NEO4J_USER") or not os.environ.get("NEO4J_PASSWORD"):
        return jsonify({
            'success': False,
            'error': 'Knowledge graph is not configured. Please set NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD environment variables.'
        }), 503
    
    # Get search query
    search_text = request.args.get('q', '')
    
    # Initialize services
    intelligence_service = IntelligenceService(database_url)
    knowledge_integration_service = KnowledgeIntegrationService(intelligence_service.SessionLocal)
    
    try:
        # Search for entities
        entities = knowledge_integration_service.knowledge_graph_service.search_entities(entity_type, search_text)
        
        return jsonify({'success': True, 'entities': entities})
    except Exception as e:
        logger.error(f"Error searching entities: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@kg_bp.route('/knowledge-graph/entity/<entity_type>/<entity_id>/connections', methods=['GET'])
def get_entity_connections(entity_type, entity_id):
    """Get connections for an entity in the knowledge graph"""
    # Get user email from session
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'error': 'User not logged in'}), 401
    
    # Check if Neo4j is configured
    if not os.environ.get("NEO4J_URI") or not os.environ.get("NEO4J_USER") or not os.environ.get("NEO4J_PASSWORD"):
        return jsonify({
            'success': False,
            'error': 'Knowledge graph is not configured. Please set NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD environment variables.'
        }), 503
    
    # Get depth parameter
    depth = int(request.args.get('depth', 1))
    
    # Initialize services
    intelligence_service = IntelligenceService(database_url)
    knowledge_integration_service = KnowledgeIntegrationService(intelligence_service.SessionLocal)
    
    try:
        # Get entity connections
        connections = knowledge_integration_service.knowledge_graph_service.get_entity_connections(entity_type, entity_id, depth)
        
        return jsonify({'success': True, 'connections': connections})
    except Exception as e:
        logger.error(f"Error getting entity connections: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@kg_bp.route('/knowledge-graph/process-email', methods=['POST'])
def process_email_for_knowledge_graph():
    """Process an email to extract entities and relationships for the knowledge graph"""
    # Get user email from session
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'error': 'User not logged in'}), 401
    
    # Check if Neo4j is configured
    if not os.environ.get("NEO4J_URI") or not os.environ.get("NEO4J_USER") or not os.environ.get("NEO4J_PASSWORD"):
        return jsonify({
            'success': False,
            'error': 'Knowledge graph is not configured. Please set NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD environment variables.'
        }), 503
    
    # Get email data from request
    email_data = request.json
    if not email_data or 'content' not in email_data:
        return jsonify({'error': 'Email content is required'}), 400
    
    # Initialize services
    intelligence_service = IntelligenceService(database_url)
    knowledge_integration_service = KnowledgeIntegrationService(intelligence_service.SessionLocal)
    
    try:
        # Process email
        result = knowledge_integration_service.process_email(
            user_email=user_email,
            email_content=email_data['content'],
            email_metadata=email_data.get('metadata', {})
        )
        
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        logger.error(f"Error processing email for knowledge graph: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
