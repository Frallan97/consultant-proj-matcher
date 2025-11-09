"""
Dependency injection functions for FastAPI.
Provides services as dependencies instead of global variables.
"""
from fastapi import Depends
from typing import Optional
import weaviate
from storage import LocalFileStorage
from services.consultant_service import ConsultantService
from services.matching_service import MatchingService
from services.overview_service import OverviewService
from services.chat_service import ChatService
from config import get_settings
from logger_config import get_logger

logger = get_logger(__name__)

# Global instances (will be initialized on first use)
_weaviate_client: Optional[weaviate.Client] = None
_storage: Optional[LocalFileStorage] = None
_consultant_service: Optional[ConsultantService] = None
_matching_service: Optional[MatchingService] = None
_overview_service: Optional[OverviewService] = None
_chat_service: Optional[ChatService] = None


def get_weaviate_client() -> Optional[weaviate.Client]:
    """Get or create Weaviate client."""
    global _weaviate_client
    # Check if main module has a client (for test compatibility)
    # If main.client is explicitly set (even to None), use it
    import main
    if hasattr(main, 'client'):
        # If main.client is None, clear cache and return None
        if main.client is None:
            _weaviate_client = None
        return main.client
    
    if _weaviate_client is None:
        settings = get_settings()
        try:
            _weaviate_client = weaviate.Client(url=settings.weaviate_url)
            logger.info(f"Successfully connected to Weaviate at {settings.weaviate_url}")
        except (weaviate.exceptions.WeaviateBaseError, ConnectionError, Exception) as e:
            logger.warning(f"Could not connect to Weaviate at {settings.weaviate_url}: {e}", exc_info=True)
            _weaviate_client = None
    return _weaviate_client


def get_storage() -> LocalFileStorage:
    """Get or create storage instance."""
    global _storage
    # Check if main module has storage (for test compatibility)
    import main
    if hasattr(main, 'storage') and main.storage is not None:
        return main.storage
    
    if _storage is None:
        settings = get_settings()
        _storage = LocalFileStorage(base_dir=settings.upload_dir)
    return _storage


def get_consultant_service(
    client: Optional[weaviate.Client] = Depends(get_weaviate_client)
) -> Optional[ConsultantService]:
    """Get or create ConsultantService."""
    global _consultant_service
    # Check if main module has consultant_service (for test compatibility)
    # If main.consultant_service is explicitly set (even to None), use it
    import main
    if hasattr(main, 'consultant_service'):
        # If main.consultant_service is None, clear cache and return None
        if main.consultant_service is None:
            _consultant_service = None
        return main.consultant_service
    
    # If client is None, clear cache and return None
    if client is None:
        _consultant_service = None
        return None
    
    if _consultant_service is None:
        _consultant_service = ConsultantService(client)
    return _consultant_service


def get_matching_service(
    client: Optional[weaviate.Client] = Depends(get_weaviate_client),
    consultant_service: Optional[ConsultantService] = Depends(get_consultant_service),
    storage: LocalFileStorage = Depends(get_storage)
) -> Optional[MatchingService]:
    """Get or create MatchingService."""
    global _matching_service
    # Check if main module has matching_service (for test compatibility)
    # If main.matching_service is explicitly set (even to None), use it
    import main
    if hasattr(main, 'matching_service'):
        return main.matching_service
    
    if _matching_service is None and client is not None and consultant_service is not None:
        _matching_service = MatchingService(client, consultant_service, storage)
    return _matching_service


def get_overview_service(
    consultant_service: Optional[ConsultantService] = Depends(get_consultant_service)
) -> Optional[OverviewService]:
    """Get or create OverviewService."""
    global _overview_service
    # Check if main module has overview_service (for test compatibility)
    import main
    if hasattr(main, 'overview_service') and main.overview_service is not None:
        return main.overview_service
    
    if _overview_service is None and consultant_service is not None:
        _overview_service = OverviewService(consultant_service)
    return _overview_service


def get_chat_service() -> Optional[ChatService]:
    """Get or create ChatService (lazy initialization)."""
    global _chat_service
    # Check if main module has chat_service (for test compatibility)
    # Only use main.chat_service if it's explicitly set to a non-None value
    # If it's None, try to create a new one
    import main
    if hasattr(main, 'chat_service') and main.chat_service is not None:
        return main.chat_service
    
    # If main.chat_service was explicitly set to None, clear the cache
    if hasattr(main, 'chat_service') and main.chat_service is None:
        _chat_service = None
    
    if _chat_service is None:
        try:
            _chat_service = ChatService()
            logger.info("Chat service initialized")
        except ValueError as e:
            logger.error(f"Failed to initialize chat service: {e}", exc_info=True)
            _chat_service = None
    return _chat_service

