"""
MongoDB database configuration and connection management.
"""
import os
from pymongo import MongoClient
from pymongo.database import Database
from typing import Optional

# MongoDB connection string
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DATABASE_NAME = os.getenv("DATABASE_NAME", "langgraph_chat")

# Global database client
_client: Optional[MongoClient] = None
_db: Optional[Database] = None


def get_database() -> Database:
    """
    Get the MongoDB database instance.
    Creates connection on first call, reuses existing connection.
    """
    global _client, _db
    
    if _db is not None:
        return _db
    
    try:
        _client = MongoClient(MONGO_URI)
        _db = _client[DATABASE_NAME]
        
        # Test connection
        _client.admin.command('ping')
        print(f"Connected to MongoDB: {DATABASE_NAME}")
        
        return _db
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        raise


def get_threads_collection():
    """Get the threads collection."""
    db = get_database()
    return db.threads


def get_messages_collection():
    """Get the messages collection."""
    db = get_database()
    return db.messages


def close_connection():
    """Close the MongoDB connection."""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
        print("MongoDB connection closed")


# Initialize collections with indexes
def init_indexes():
    """Create necessary indexes for collections."""
    threads = get_threads_collection()
    messages = get_messages_collection()
    
    # Threads indexes
    threads.create_index("created_at", background=True)
    threads.create_index("name")
    
    # Messages indexes
    messages.create_index("thread_id", background=True)
    messages.create_index("created_at", background=True)
    messages.create_index([("thread_id", 1), ("created_at", -1)])
    
    print("Database indexes created")
