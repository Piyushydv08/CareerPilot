import logging
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
from app.core.config import settings

logger = logging.getLogger(__name__)

class DatabaseManager:
    client: AsyncIOMotorClient = None
    db = None

    async def connect_to_database(self) -> None:
        """Instantiate asynchronous connection to MongoDB Atlas."""
        logger.info("Initializing connection to database...")
        try:
            self.client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                serverSelectionTimeoutMS=5000
            )
            self.db = self.client[settings.DATABASE_NAME]
            # Perform a quick ping operation to verify server availability
            await self.client.admin.command('ping')
            logger.info("MongoDB asynchronous connection established successfully.")
        except Exception as e:
            logger.error(f"Database connection critical failure: {e}")
            # Do not crash app instantly during development, just print warning
            logger.warning("Running database connection offline. Telemetry fallback active.")

    async def close_database_connection(self) -> None:
        """Gracefully release client nodes."""
        if self.client:
            logger.info("Closing database broker nodes...")
            self.client.close()
            logger.info("Database connection closed.")

db_manager = DatabaseManager()

async def get_database():
    """Dependency helper to load db inside route endpoints."""
    return db_manager.db

async def setup_vector_search_index():
    """
    Helper script to explicitly demonstrate how to define a Vector Search 
    index mapping on the MongoDB Atlas collections using cosine similarity.
    Note: In Atlas, this is typically done via the Atlas UI, Atlas CLI, or 
    Atlas Search API. This is the index definition structure required.
    """
    if db_manager.db is None:
        logger.warning("Database not connected. Cannot setup vector index.")
        return

    # Define the search index model for the 'resumes' collection
    # The field 'resume_embeddings' matches our ResumeDocument schema
    search_index_model = {
        "name": "resume_vector_index",
        "type": "vectorSearch",
        "definition": {
            "fields": [
                {
                    "type": "vector",
                    "path": "resume_embeddings",
                    "numDimensions": 768,  # e.g., 768 for Gemini embeddings
                    "similarity": "cosine"
                }
            ]
        }
    }
    
    try:
        # Example of how it would be created programmatically if supported directly by the cluster:
        # await db_manager.db.resumes.create_search_index(search_index_model)
        logger.info(f"Atlas Vector search index mapping defined for creation: {search_index_model}")
    except Exception as e:
        logger.error(f"Failed to demonstrate vector search index: {e}")
