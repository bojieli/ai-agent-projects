import json
from typing import Optional
import logging
from openai import OpenAIError
import requests

logger = logging.getLogger(__name__)

class APIError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None, response_body: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(self.message)

def handle_openai_error(e: OpenAIError) -> APIError:
    """Handle OpenAI API errors with detailed logging"""
    error_msg = str(e)
    status_code = None
    response_body = None
    
    if hasattr(e, 'response'):
        try:
            status_code = e.response.status_code
            response_body = e.response.text
            error_details = json.loads(response_body)
            error_msg = f"OpenAI API Error: {error_details.get('error', {}).get('message', str(e))}"
        except Exception:
            error_msg = f"OpenAI API Error: {str(e)}"
    
    logger.error(f"OpenAI API Error (Status: {status_code}): {error_msg}")
    if response_body:
        logger.error(f"Response body: {response_body}")
        
    return APIError(error_msg, status_code, response_body)

def handle_request_error(e: requests.exceptions.RequestException) -> APIError:
    """Handle general request errors with detailed logging"""
    error_msg = str(e)
    status_code = None
    response_body = None
    
    if hasattr(e, 'response'):
        try:
            status_code = e.response.status_code
            response_body = e.response.text
            error_msg = f"Request Error: {e.response.reason} - {response_body}"
        except Exception:
            error_msg = f"Request Error: {str(e)}"
    
    logger.error(f"Request Error (Status: {status_code}): {error_msg}")
    if response_body:
        logger.error(f"Response body: {response_body}")
        
    return APIError(error_msg, status_code, response_body) 