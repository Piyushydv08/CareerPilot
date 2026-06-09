import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import DESCENDING, ASCENDING
from pymongo.errors import ConnectionFailure, OperationFailure
from app.core.config import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    client: Optional[AsyncIOMotorClient] = None
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


async def setup_collections() -> None:
    """
    Create necessary indexes on startup for performance.
    - resumes: uploaded_at (desc)
    - match_logs: computed_match_score (desc)
    - interview_sessions: status
    """
    if db_manager.db is None:
        logger.warning("Database not connected — skipping index setup.")
        return

    try:
        await db_manager.db["resumes"].create_index(
            [("uploaded_at", DESCENDING)], name="idx_resumes_uploaded_at"
        )
        await db_manager.db["match_logs"].create_index(
            [("computed_match_score", DESCENDING)], name="idx_match_logs_score"
        )
        await db_manager.db["interview_sessions"].create_index(
            [("status", ASCENDING)], name="idx_interview_sessions_status"
        )
        logger.info("MongoDB collection indexes created/verified successfully.")
    except OperationFailure as e:
        logger.warning(f"Index creation failed (may already exist): {e}")
    except Exception as e:
        logger.error(f"Unexpected error during index setup: {e}")

    # Check for Vector Search index and log action-required message if missing
    await setup_vector_search_index()


async def setup_vector_search_index() -> None:
    """
    Verifies that the Atlas Vector Search index exists on resumes.resume_embeddings.
    Since Atlas Search indexes cannot be created programmatically via Motor in all
    cluster tiers, this function logs a clear action-required message if it's missing.
    """
    if db_manager.db is None:
        logger.warning("Database not connected. Cannot setup vector index.")
        return

    search_index_model = {
        "name": "resume_vector_index",
        "type": "vectorSearch",
        "definition": {
            "fields": [
                {
                    "type": "vector",
                    "path": "resume_embeddings",
                    "numDimensions": 768,
                    "similarity": "cosine"
                }
            ]
        }
    }

    try:
        # Attempt to list existing search indexes to check if ours exists
        existing_indexes = await db_manager.db["resumes"].list_search_indexes().to_list(length=50)
        index_names = [idx.get("name") for idx in existing_indexes]

        if "resume_vector_index" not in index_names:
            logger.warning(
                "ACTION REQUIRED: Create Atlas Vector Search index 'resume_vector_index' "
                "on resumes.resume_embeddings with numDimensions=768 and similarity=cosine. "
                "See: https://www.mongodb.com/docs/atlas/atlas-vector-search/create-index/"
            )
            logger.info(f"Required index definition: {search_index_model}")
        else:
            logger.info("Atlas Vector Search index 'resume_vector_index' is active.")
    except Exception as e:
        logger.warning(
            f"Could not verify vector search index (cluster may not support programmatic listing): {e}. "
            "ACTION REQUIRED: Manually create Atlas Vector Search index 'resume_vector_index' "
            "on resumes.resume_embeddings with numDimensions=768 and similarity=cosine. "
            "See: https://www.mongodb.com/docs/atlas/atlas-vector-search/create-index/"
        )
