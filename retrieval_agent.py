import logging
from langchain_google_community import VertexAISearchRetriever
from functools import lru_cache

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants for VertexAI configuration
DATA_STORE_ID = "grounding-unfpa_1733828609811"
DATA_STORE_LOCATION = "global"

# Initialize Vertex AI Retriever
retriever = VertexAISearchRetriever(
    project_id="unfpa-444213",
    location_id=DATA_STORE_LOCATION,
    data_store_id=DATA_STORE_ID,
    get_extractive_answers=True,
    max_documents=100,
    max_extractive_segment_count=1,
    max_extractive_answer_count=5,
)

@lru_cache(maxsize=50)  # Increase cache size based on the expected number of queries
def retrieve_chunks(query, limit=5):
    try:
        docs = retriever.get_relevant_documents(query)
        
        if not docs:
            logger.warning(f"No documents found for query: {query}")
            return []  # Return an empty list if no documents are found
        
        # Limit to a configurable number of chunks (default to 5)
        docs = docs[:limit]  
        
        # Return the top chunks with the source metadata
        return [{"chunk": doc.page_content, "source": doc.metadata.get('source', 'Unknown')} for doc in docs]
    
    except Exception as e:
        logger.error(f"An error occurred during retrieval: {e}", exc_info=True)
        return []
