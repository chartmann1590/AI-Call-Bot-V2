import requests
import logging
import json
from typing import Optional, Dict, Any
from urllib.parse import urljoin
from datetime import datetime

# Configure comprehensive logging for Ollama client
ollama_logger = logging.getLogger('ollama')
ollama_logger.setLevel(logging.DEBUG)

class OllamaClient:
    """Client for communicating with Ollama API"""
    
    def __init__(self, base_url: str = 'http://localhost:11434'):
        """
        Initialize Ollama client
        
        Args:
            base_url: Base URL of Ollama server
        """
        ollama_logger.info("=== INITIALIZING OLLAMA CLIENT ===")
        ollama_logger.info(f"🤖 Initializing Ollama client with URL: {base_url}")
        
        # Ensure base_url is properly formatted
        if not base_url:
            base_url = 'http://localhost:11434'
            ollama_logger.info(f"🤖 Using default URL: {base_url}")
        
        # Remove trailing slash and ensure proper URL format
        self.base_url = base_url.rstrip('/')
        ollama_logger.info(f"🤖 Cleaned base URL: {self.base_url}")
        
        # Validate URL format
        if not self.base_url.startswith(('http://', 'https://')):
            self.base_url = f'http://{self.base_url}'
            ollama_logger.info(f"🤖 Added http:// prefix: {self.base_url}")
        
        ollama_logger.info(f"🤖 Final Ollama URL: {self.base_url}")
        
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'CallBot/1.0'
        })
        ollama_logger.info("🤖 HTTP session configured with headers")
        ollama_logger.info("✅ Ollama client initialized successfully")
    
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
        
        ollama_logger.info(f"🌐 Making {method} request to: {url}")
        if data:
            ollama_logger.debug(f"🌐 Request data: {data}")
        
        try:
            start_time = datetime.now()
            
            if method.upper() == 'GET':
                ollama_logger.debug(f"🌐 Sending GET request...")
                response = self.session.get(url, timeout=30)
            elif method.upper() == 'POST':
                ollama_logger.debug(f"🌐 Sending POST request...")
                response = self.session.post(url, json=data, timeout=30)
            else:
                ollama_logger.error(f"❌ Unsupported HTTP method: {method}")
                return None
            
            response_time = (datetime.now() - start_time).total_seconds()
            ollama_logger.info(f"🌐 Response received in {response_time:.2f}s")
            ollama_logger.info(f"🌐 Response status: {response.status_code}")
            
            response.raise_for_status()
            
            try:
                response_data = response.json()
                ollama_logger.info(f"✅ Request successful - Response size: {len(str(response_data))} chars")
                return response_data
            except json.JSONDecodeError as e:
                ollama_logger.error(f"❌ Failed to parse JSON response: {e}")
                ollama_logger.error(f"❌ Response text: {response.text[:200]}...")
                return None
            
        except requests.exceptions.ConnectionError as e:
            ollama_logger.error(f"❌ Connection failed to {url}: {e}")
            return None
        except requests.exceptions.Timeout as e:
            ollama_logger.error(f"❌ Request timeout to {url}: {e}")
            return None
        except requests.exceptions.RequestException as e:
            ollama_logger.error(f"❌ Request failed to {url}: {e}")
            ollama_logger.error(f"❌ Response status: {response.status_code if 'response' in locals() else 'Unknown'}")
            return None
        except Exception as e:
            ollama_logger.error(f"❌ Unexpected error during request: {e}")
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
        
        ollama_logger.error(f"Failed to generate response: {response}")
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
        
        ollama_logger.error(f"Failed to get models: {response}")
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
        
        ollama_logger.error(f"Failed to get model info for {model_name}")
        return None
    
    def check_server_status(self) -> bool:
        """
        Check if Ollama server is running
        
        Returns:
            True if server is running, False otherwise
        """
        try:
            url = f"{self.base_url}/api/tags"
            ollama_logger.debug(f"Checking server status at: {url}")
            response = self.session.get(url, timeout=5)
            if response.status_code == 200:
                ollama_logger.debug(f"Server status check successful: {response.status_code}")
                return True
            else:
                ollama_logger.warning(f"Server status check failed with status code: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            ollama_logger.debug(f"Server status check failed: {e}")
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
            'error': None,
            'url': self.base_url
        }
        
        try:
            ollama_logger.info(f"Testing connection to Ollama server at: {self.base_url}")
            
            # Check if server is running
            if not self.check_server_status():
                status['error'] = f'Server not reachable at {self.base_url}'
                ollama_logger.error(f"Ollama server not reachable at {self.base_url}")
                return status
            
            status['connected'] = True
            ollama_logger.info(f"Successfully connected to Ollama server at {self.base_url}")
            
            # Get available models
            models = self.list_models()
            if models:
                status['models'] = models
                ollama_logger.info(f"Found {len(models)} models: {', '.join(models)}")
            else:
                status['error'] = 'Failed to retrieve models'
                ollama_logger.error("Failed to retrieve models from Ollama server")
            
        except Exception as e:
            status['error'] = str(e)
            ollama_logger.error(f"Exception during connection test: {e}")
        
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
        ollama_logger.info("=== GENERATING AI RESPONSE WITH CONTEXT ===")
        ollama_logger.info(f"🤖 Input transcript: {transcript}")
        ollama_logger.info(f"🤖 Transcript length: {len(transcript)} characters")
        ollama_logger.info(f"🤖 Using model: {model}")
        ollama_logger.info(f"🤖 Context provided: {context is not None}")
        
        # Default system prompt for call bot
        system_prompt = """You are a helpful AI assistant answering phone calls. 
        Respond naturally and conversationally to the caller's questions and requests. 
        Keep responses concise and helpful."""
        
        if context:
            system_prompt = context
            ollama_logger.info(f"🤖 Using custom context: {context[:100]}...")
        else:
            ollama_logger.info(f"🤖 Using default system prompt")
        
        # Create a conversational prompt
        prompt = f"Caller says: {transcript}\n\nAssistant:"
        ollama_logger.info(f"🤖 Generated prompt: {prompt[:100]}...")
        
        ollama_logger.info(f"🤖 Calling generate_response with model {model}")
        response = self.generate_response(
            prompt=prompt,
            model=model,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=200
        )
        
        if response:
            ollama_logger.info(f"✅ AI response generated successfully")
            ollama_logger.info(f"🤖 Response: {response}")
            ollama_logger.info(f"🤖 Response length: {len(response)} characters")
        else:
            ollama_logger.error(f"❌ Failed to generate AI response")
        
        return response 