# API Reference

CallBot provides a REST API for programmatic access to call data and system management.

## Base URL

```
http://localhost:5000/api
```

## Authentication

Currently, the API uses session-based authentication. All endpoints require a valid session cookie.

## Endpoints

### Calls

#### GET /api/calls

Retrieve a paginated list of calls.

**Parameters:**
- `page` (optional): Page number (default: 1)
- `per_page` (optional): Items per page (default: 20)
- `search` (optional): Search term for transcripts and responses
- `status` (optional): Filter by call status (completed, in_progress, failed)

**Response:**
```json
{
  "calls": [
    {
      "id": 1,
      "timestamp": "2024-01-15T10:30:00Z",
      "caller_id": "+1234567890",
      "transcript": "Hello, I need help with my account",
      "ai_response": "I'd be happy to help you with your account. What specific issue are you experiencing?",
      "tts_voice": "en_0",
      "audio_filename": "call_1_1705312200.wav",
      "duration": 45,
      "duration_formatted": "00:45",
      "status": "completed"
    }
  ],
  "total": 150,
  "pages": 8,
  "current_page": 1
}
```

#### GET /api/calls/{id}

Retrieve a specific call by ID.

**Response:**
```json
{
  "id": 1,
  "timestamp": "2024-01-15T10:30:00Z",
  "caller_id": "+1234567890",
  "transcript": "Hello, I need help with my account",
  "ai_response": "I'd be happy to help you with your account. What specific issue are you experiencing?",
  "tts_voice": "en_0",
  "audio_filename": "call_1_1705312200.wav",
  "duration": 45,
  "duration_formatted": "00:45",
  "status": "completed"
}
```

#### GET /api/audio/{id}

Download the audio file for a specific call.

**Response:** Audio file (WAV format)

### Active Calls

#### GET /api/active_calls

Get currently active calls.

**Response:**
```json
{
  "call_123": {
    "call_id": "call_123",
    "caller_id": "+1234567890",
    "status": "in_progress",
    "duration": 30,
    "transcript_parts": ["Hello", "I need help"]
  }
}
```

### System Status

#### GET /api/test_ollama

Test the connection to Ollama AI service.

**Response:**
```json
{
  "connected": true,
  "models": ["llama2", "mistral", "codellama"],
  "error": null
}
```

#### GET /api/system_status

Get overall system status.

**Response:**
```json
{
  "sip_status": "connected",
  "ollama_status": "connected",
  "tts_status": "available",
  "whisper_status": "ready",
  "active_calls": 2,
  "total_calls": 150,
  "uptime": "2h 30m"
}
```

### Settings

#### GET /api/settings

Get current system settings.

**Response:**
```json
{
  "sip_domain": "pbx.example.com",
  "sip_username": "1001",
  "ollama_url": "http://localhost:11434",
  "ollama_model": "llama2",
  "tts_engine": "coqui",
  "tts_voice": "en_0",
  "whisper_model_size": "base",
  "whisper_device": "cpu"
}
```

#### POST /api/settings

Update system settings.

**Request Body:**
```json
{
  "sip_domain": "new-pbx.example.com",
  "sip_username": "1002",
  "sip_password": "new-password",
  "ollama_url": "http://localhost:11434",
  "ollama_model": "mistral"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Settings updated successfully"
}
```

## Error Responses

### 400 Bad Request
```json
{
  "error": "Invalid parameter",
  "message": "The 'page' parameter must be a positive integer"
}
```

### 404 Not Found
```json
{
  "error": "Call not found",
  "message": "Call with ID 999 does not exist"
}
```

### 500 Internal Server Error
```json
{
  "error": "Database connection failed",
  "message": "Unable to connect to the database"
}
```

## Rate Limiting

API endpoints are rate-limited to prevent abuse:

- **Default**: 100 requests per minute
- **Authentication endpoints**: 10 requests per minute
- **File uploads**: 10 requests per minute

Rate limit headers are included in responses:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642234567
```

## Pagination

List endpoints support pagination with the following parameters:

- `page`: Page number (1-based)
- `per_page`: Items per page (max 100)

Pagination metadata is included in responses:

```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 150,
    "pages": 8,
    "has_prev": false,
    "has_next": true
  }
}
```

## Filtering and Search

### Search

Use the `search` parameter to search across transcripts and AI responses:

```
GET /api/calls?search=account+help
```

### Status Filtering

Filter calls by status:

```
GET /api/calls?status=completed
GET /api/calls?status=in_progress
GET /api/calls?status=failed
```

### Date Range Filtering

Filter calls by date range:

```
GET /api/calls?start_date=2024-01-01&end_date=2024-01-31
```

## WebSocket API

For real-time updates, CallBot also provides WebSocket endpoints:

### WebSocket Connection

```
ws://localhost:5000/ws
```

### Events

#### call_started
```json
{
  "event": "call_started",
  "data": {
    "call_id": "call_123",
    "caller_id": "+1234567890",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

#### call_ended
```json
{
  "event": "call_ended",
  "data": {
    "call_id": "call_123",
    "duration": 45,
    "transcript": "Hello, I need help",
    "ai_response": "I'd be happy to help you"
  }
}
```

#### transcript_update
```json
{
  "event": "transcript_update",
  "data": {
    "call_id": "call_123",
    "transcript": "Hello, I need help with my account"
  }
}
```

## SDK Examples

### Python SDK

```python
import requests

class CallBotAPI:
    def __init__(self, base_url="http://localhost:5000/api"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def get_calls(self, page=1, search=None):
        params = {"page": page}
        if search:
            params["search"] = search
        
        response = self.session.get(f"{self.base_url}/calls", params=params)
        return response.json()
    
    def get_call(self, call_id):
        response = self.session.get(f"{self.base_url}/calls/{call_id}")
        return response.json()
    
    def download_audio(self, call_id, filename=None):
        response = self.session.get(f"{self.base_url}/audio/{call_id}")
        if filename:
            with open(filename, 'wb') as f:
                f.write(response.content)
        return response.content

# Usage
api = CallBotAPI()
calls = api.get_calls(page=1, search="help")
```

### JavaScript SDK

```javascript
class CallBotAPI {
    constructor(baseURL = 'http://localhost:5000/api') {
        this.baseURL = baseURL;
    }
    
    async getCalls(page = 1, search = null) {
        const params = new URLSearchParams({ page });
        if (search) params.append('search', search);
        
        const response = await fetch(`${this.baseURL}/calls?${params}`);
        return response.json();
    }
    
    async getCall(callId) {
        const response = await fetch(`${this.baseURL}/calls/${callId}`);
        return response.json();
    }
    
    async downloadAudio(callId) {
        const response = await fetch(`${this.baseURL}/audio/${callId}`);
        return response.blob();
    }
}

// Usage
const api = new CallBotAPI();
const calls = await api.getCalls(1, 'help');
```

## Testing the API

### Using curl

```bash
# Get all calls
curl http://localhost:5000/api/calls

# Get specific call
curl http://localhost:5000/api/calls/1

# Search calls
curl "http://localhost:5000/api/calls?search=help"

# Test Ollama connection
curl http://localhost:5000/api/test_ollama
```

### Using Postman

1. Import the API collection
2. Set the base URL to `http://localhost:5000/api`
3. Test endpoints with the provided examples

## API Versioning

The API version is included in the URL path:

- Current version: `/api/v1/`
- Future versions: `/api/v2/`, `/api/v3/`, etc.

Version compatibility is maintained for at least 12 months after a new version is released. 