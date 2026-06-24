import json
import os
import logging

logger = logging.getLogger(__name__)

def get_repo_dependencies():
    """
    Simulates an MCP Server reading the package.json from a connected GitHub repository.
    Returns a dictionary of dependencies and their installed versions.
    """
    file_path = os.path.join(os.path.dirname(__file__), "mock_repo", "package.json")
    
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
            # Simulate MCP context retrieval
            logger.info("MCP Context: Successfully read package.json from target repository.")
            return data.get("dependencies", {})
    except Exception as e:
        logger.error(f"MCP Context Error: Failed to read repository: {e}")
        return {}
