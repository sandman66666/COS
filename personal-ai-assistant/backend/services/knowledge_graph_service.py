"""
Knowledge Graph Service for storing and retrieving entities and relationships.
Uses Neo4j as the backend graph database.
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import json

try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    logging.warning("Neo4j driver not available. Knowledge graph features will be disabled.")

logger = logging.getLogger(__name__)

class KnowledgeGraphService:
    """Service for managing knowledge graph operations with Neo4j"""
    
    def __init__(self, uri=None, username=None, password=None):
        """Initialize the knowledge graph service with Neo4j connection"""
        if not NEO4J_AVAILABLE:
            logging.warning("Neo4j driver not installed. Knowledge graph features will be disabled.")
            self.driver = None
            return
            
        self.uri = uri or os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        self.username = username or os.environ.get("NEO4J_USER", "neo4j")
        self.password = password or os.environ.get("NEO4J_PASSWORD", "password")
        
        if not self.uri or not self.username or not self.password:
            logging.warning("Neo4j connection parameters missing. Knowledge graph features will be disabled.")
            self.driver = None
            return
        
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            logging.info("Successfully connected to Neo4j database")
            
            # Initialize schema (constraints and indexes)
            self._initialize_schema()
        except Exception as e:
            logging.error(f"Failed to connect to Neo4j: {str(e)}")
            self.driver = None
    
    def close(self):
        """Close the Neo4j connection"""
        if self.driver:
            self.driver.close()
            logger.info("Closed Neo4j connection")
    
    def _initialize_schema(self):
        """Create constraints and indexes for the knowledge graph"""
        with self.driver.session() as session:
            # Create constraints for unique entities
            session.run("CREATE CONSTRAINT person_email IF NOT EXISTS FOR (p:Person) REQUIRE p.email IS UNIQUE")
            session.run("CREATE CONSTRAINT company_name IF NOT EXISTS FOR (c:Company) REQUIRE c.name IS UNIQUE")
            session.run("CREATE CONSTRAINT project_id IF NOT EXISTS FOR (p:Project) REQUIRE p.id IS UNIQUE")
            session.run("CREATE CONSTRAINT task_id IF NOT EXISTS FOR (t:Task) REQUIRE t.id IS UNIQUE")
            session.run("CREATE CONSTRAINT meeting_id IF NOT EXISTS FOR (m:Meeting) REQUIRE m.id IS UNIQUE")
            
            # Create indexes for faster lookups
            session.run("CREATE INDEX person_name IF NOT EXISTS FOR (p:Person) ON (p.name)")
            session.run("CREATE INDEX task_deadline IF NOT EXISTS FOR (t:Task) ON (t.deadline)")
            
            logger.info("Neo4j schema initialized with constraints and indexes")
    
    # Person operations
    def create_person(self, email: str, name: str, properties: Optional[Dict] = None) -> Dict:
        """Create or update a person node in the knowledge graph"""
        with self.driver.session() as session:
            result = session.execute_write(
                self._create_person_tx, email, name, properties or {})
            logger.info(f"Created/updated person: {email}")
            return result
    
    @staticmethod
    def _create_person_tx(tx, email: str, name: str, properties: Dict) -> Dict:
        """Transaction function to create or update a person node"""
        query = (
            "MERGE (p:Person {email: $email}) "
            "SET p.name = $name "
        )
        
        # Add any additional properties
        for key, value in properties.items():
            query += f"SET p.{key} = ${key} "
        
        query += "RETURN p"
        
        result = tx.run(query, email=email, name=name, **properties)
        record = result.single()
        if record:
            return dict(record["p"])
        return {}
    
    # Company operations
    def create_company(self, name: str, properties: Optional[Dict] = None) -> Dict:
        """Create or update a company node in the knowledge graph"""
        with self.driver.session() as session:
            result = session.execute_write(
                self._create_company_tx, name, properties or {})
            logger.info(f"Created/updated company: {name}")
            return result
    
    @staticmethod
    def _create_company_tx(tx, name: str, properties: Dict) -> Dict:
        """Transaction function to create or update a company node"""
        query = (
            "MERGE (c:Company {name: $name}) "
        )
        
        # Add any additional properties
        for key, value in properties.items():
            query += f"SET c.{key} = ${key} "
        
        query += "RETURN c"
        
        result = tx.run(query, name=name, **properties)
        record = result.single()
        if record:
            return dict(record["c"])
        return {}
    
    # Project operations
    def create_project(self, project_id: str, name: str, properties: Optional[Dict] = None) -> Dict:
        """Create or update a project node in the knowledge graph"""
        with self.driver.session() as session:
            result = session.execute_write(
                self._create_project_tx, project_id, name, properties or {})
            logger.info(f"Created/updated project: {name} (ID: {project_id})")
            return result
    
    @staticmethod
    def _create_project_tx(tx, project_id: str, name: str, properties: Dict) -> Dict:
        """Transaction function to create or update a project node"""
        query = (
            "MERGE (p:Project {id: $project_id}) "
            "SET p.name = $name "
        )
        
        # Add any additional properties
        for key, value in properties.items():
            query += f"SET p.{key} = ${key} "
        
        query += "RETURN p"
        
        result = tx.run(query, project_id=project_id, name=name, **properties)
        record = result.single()
        if record:
            return dict(record["p"])
        return {}
    
    # Task operations
    def create_task(self, task_id: str, description: str, properties: Optional[Dict] = None) -> Dict:
        """Create or update a task node in the knowledge graph"""
        with self.driver.session() as session:
            result = session.execute_write(
                self._create_task_tx, task_id, description, properties or {})
            logger.info(f"Created/updated task: {description[:30]}... (ID: {task_id})")
            return result
    
    @staticmethod
    def _create_task_tx(tx, task_id: str, description: str, properties: Dict) -> Dict:
        """Transaction function to create or update a task node"""
        query = (
            "MERGE (t:Task {id: $task_id}) "
            "SET t.description = $description "
        )
        
        # Add any additional properties
        for key, value in properties.items():
            query += f"SET t.{key} = ${key} "
        
        query += "RETURN t"
        
        result = tx.run(query, task_id=task_id, description=description, **properties)
        record = result.single()
        if record:
            return dict(record["t"])
        return {}
    
    # Meeting operations
    def create_meeting(self, meeting_id: str, title: str, properties: Optional[Dict] = None) -> Dict:
        """Create or update a meeting node in the knowledge graph"""
        with self.driver.session() as session:
            result = session.execute_write(
                self._create_meeting_tx, meeting_id, title, properties or {})
            logger.info(f"Created/updated meeting: {title} (ID: {meeting_id})")
            return result
    
    @staticmethod
    def _create_meeting_tx(tx, meeting_id: str, title: str, properties: Dict) -> Dict:
        """Transaction function to create or update a meeting node"""
        query = (
            "MERGE (m:Meeting {id: $meeting_id}) "
            "SET m.title = $title "
        )
        
        # Add any additional properties
        for key, value in properties.items():
            query += f"SET m.{key} = ${key} "
        
        query += "RETURN m"
        
        result = tx.run(query, meeting_id=meeting_id, title=title, **properties)
        record = result.single()
        if record:
            return dict(record["m"])
        return {}
    
    # Relationship operations
    def create_relationship(self, from_type: str, from_id: str, to_type: str, to_id: str, 
                           rel_type: str, properties: Optional[Dict] = None) -> Dict:
        """Create a relationship between two nodes in the knowledge graph"""
        with self.driver.session() as session:
            result = session.execute_write(
                self._create_relationship_tx, from_type, from_id, to_type, to_id, rel_type, properties or {})
            logger.info(f"Created relationship: ({from_type}:{from_id})-[{rel_type}]->({to_type}:{to_id})")
            return result
    
    @staticmethod
    def _create_relationship_tx(tx, from_type: str, from_id: str, to_type: str, to_id: str, 
                              rel_type: str, properties: Dict) -> Dict:
        """Transaction function to create a relationship between two nodes"""
        # Determine the property to use for each node type
        id_properties = {
            "Person": "email",
            "Company": "name",
            "Project": "id",
            "Task": "id",
            "Meeting": "id"
        }
        
        from_prop = id_properties.get(from_type, "id")
        to_prop = id_properties.get(to_type, "id")
        
        query = (
            f"MATCH (a:{from_type} {{{from_prop}: $from_id}}), (b:{to_type} {{{to_prop}: $to_id}}) "
            f"MERGE (a)-[r:{rel_type}]->(b) "
        )
        
        # Add any additional properties to the relationship
        for key, value in properties.items():
            query += f"SET r.{key} = ${key} "
        
        query += "RETURN r"
        
        result = tx.run(query, from_id=from_id, to_id=to_id, **properties)
        record = result.single()
        if record:
            return dict(record["r"])
        return {}
    
    # Query operations
    def get_entity_connections(self, entity_type: str, entity_id: str, depth: int = 1) -> Dict:
        """Get all connections for a specific entity"""
        with self.driver.session() as session:
            result = session.execute_read(
                self._get_entity_connections_tx, entity_type, entity_id, depth)
            return result
    
    @staticmethod
    def _get_entity_connections_tx(tx, entity_type: str, entity_id: str, depth: int) -> Dict:
        """Transaction function to get all connections for a specific entity"""
        # Determine the property to use for the entity type
        id_properties = {
            "Person": "email",
            "Company": "name",
            "Project": "id",
            "Task": "id",
            "Meeting": "id"
        }
        
        entity_prop = id_properties.get(entity_type, "id")
        
        query = (
            f"MATCH (n:{entity_type} {{{entity_prop}: $entity_id}})-[r]-(m) "
            f"RETURN n, r, m"
        )
        
        result = tx.run(query, entity_id=entity_id)
        
        # Process the results
        connections = {
            "entity": {},
            "relationships": []
        }
        
        for record in result:
            if not connections["entity"]:
                connections["entity"] = dict(record["n"])
            
            rel = {
                "from": dict(record["n"]),
                "to": dict(record["m"]),
                "type": record["r"].type,
                "properties": dict(record["r"])
            }
            
            connections["relationships"].append(rel)
        
        return connections
    
    def search_entities(self, entity_type: str, search_text: str) -> List[Dict]:
        """Search for entities by name or other properties"""
        with self.driver.session() as session:
            result = session.execute_read(
                self._search_entities_tx, entity_type, search_text)
            return result
    
    @staticmethod
    def _search_entities_tx(tx, entity_type: str, search_text: str) -> List[Dict]:
        """Transaction function to search for entities"""
        query = (
            f"MATCH (n:{entity_type}) "
            f"WHERE n.name =~ $search_pattern OR n.email =~ $search_pattern "
            f"RETURN n"
        )
        
        search_pattern = f"(?i).*{search_text}.*"
        result = tx.run(query, search_pattern=search_pattern)
        
        entities = []
        for record in result:
            entities.append(dict(record["n"]))
        
        return entities
    
    # Knowledge graph statistics
    def get_graph_statistics(self) -> Dict:
        """Get statistics about the knowledge graph"""
        with self.driver.session() as session:
            result = session.execute_read(self._get_graph_statistics_tx)
            return result
    
    @staticmethod
    def _get_graph_statistics_tx(tx) -> Dict:
        """Transaction function to get statistics about the knowledge graph"""
        query = (
            "MATCH (n) "
            "RETURN labels(n) AS label, count(n) AS count"
        )
        
        result = tx.run(query)
        
        stats = {
            "node_counts": {},
            "total_nodes": 0
        }
        
        for record in result:
            label = record["label"][0]  # Get the first label
            count = record["count"]
            stats["node_counts"][label] = count
            stats["total_nodes"] += count
        
        # Get relationship counts
        rel_query = (
            "MATCH ()-[r]->() "
            "RETURN type(r) AS type, count(r) AS count"
        )
        
        rel_result = tx.run(rel_query)
        
        stats["relationship_counts"] = {}
        stats["total_relationships"] = 0
        
        for record in rel_result:
            rel_type = record["type"]
            count = record["count"]
            stats["relationship_counts"][rel_type] = count
            stats["total_relationships"] += count
        
        return stats
