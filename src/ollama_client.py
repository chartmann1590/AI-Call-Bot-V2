import requests
import logging
import json
from typing import Optional, Dict, Any
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class OllamaClient:
    """Client for communicating with Ollama API"""
    
    def __init__(self, base_url: str = 'http://localhost:11434'):
        """
        Initialize Ollama client
        
        Args:
            base_url: Base URL of Ollama server
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'CallBot/1.0'
        })
    
    def _make_request(self, endpoint: str, method: str = 'GET', data: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make HTTP request to Ollama API
        
        Args:
            endpoint: API endpoint
            method: HTTP method
            data: Request data
            
        Returns:
            Response data or None if request failed
        """
        url = urljoin(self.base_url, endpoint)
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, timeout=30)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data, timeout=30)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return None
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return None
    
    def generate_response(self, prompt: str, model: str, 
                        system_prompt: Optional[str] = None,
                        temperature: float = 0.7,
                        max_tokens: int = 500) -> Optional[str]:
        """
        Generate AI response using Ollama
        
        Args:
            prompt: User prompt/transcript
            model: Ollama model name
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text response or None if generation failed
        """
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        response = self._make_request('/api/generate', method='POST', data=payload)
        
        if response and 'response' in response:
            return response['response'].strip()
        
        logger.error(f"Failed to generate response: {response}")
        return None
    
    def list_models(self) -> Optional[list]:
        """
        Get list of available models
        
        Returns:
            List of model names or None if request failed
        """
        response = self._make_request('/api/tags')
        
        if response and 'models' in response:
            return [model['name'] for model in response['models']]
        
        logger.error(f"Failed to get models: {response}")
        return None
    
    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific model
        
        Args:
            model_name: Name of the model
            
        Returns:
            Model information or None if request failed
        """
        payload = {"name": model_name}
        response = self._make_request('/api/show', method='POST', data=payload)
        
        if response:
            return response
        
        logger.error(f"Failed to get model info for {model_name}")
        return None
    
    def check_server_status(self) -> bool:
        """
        Check if Ollama server is running
        
        Returns:
            True if server is running, False otherwise
        """
        try:
            response = self.session.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to Ollama server
        
        Returns:
            Dictionary with connection status and available models
        """
        status = {
            'connected': False,
            'models': [],
            'error': None
        }
        
        try:
            # Check if server is running
            if not self.check_server_status():
                status['error'] = 'Server not reachable'
                return status
            
            status['connected'] = True
            
            # Get available models
            models = self.list_models()
            if models:
                status['models'] = models
            else:
                status['error'] = 'Failed to retrieve models'
            
        except Exception as e:
            status['error'] = str(e)
        
        return status
    
    def generate_with_context(self, transcript: str, model: str, 
                            context: Optional[str] = None) -> Optional[str]:
        """
        Generate response with context for call bot
        
        Args:
            transcript: Caller's speech transcript
            model: Ollama model name
            context: Optional context about the bot's role
            
        Returns:
            AI response or None if generation failed
        """
        # Default system prompt for call bot
        system_prompt = """You are a helpful AI assistant answering phone calls. 
        Respond naturally and conversationally to the caller's questions and requests. 
        Keep responses concise and helpful."""
        
        if context:
            system_prompt = context
        
        # Create a conversational prompt
        prompt = f"Caller says: {transcript}\n\nAssistant:"
        
        return self.generate_response(
            prompt=prompt,
            model=model,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=200
        ) 