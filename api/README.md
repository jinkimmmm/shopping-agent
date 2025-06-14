# Shopping Agent API

RESTful API server for the Shopping Agent system, providing web interface access to the existing CLI-based shopping agent.

## Overview

This API server acts as a bridge between the existing `ShoppingAgentApp` and web-based frontends. It provides:

- **RESTful endpoints** for shopping requests and status tracking
- **WebSocket support** for real-time progress updates
- **History management** for conversation tracking
- **System monitoring** and health checks
- **CORS support** for web frontend integration

## Project Structure

```
api/
├── main.py                 # FastAPI application entry point
├── config.py              # Configuration settings
├── run.py                 # Server startup script
├── requirements.txt       # Python dependencies
├── routers/              # API route handlers
│   ├── __init__.py
│   ├── requests.py       # Shopping request endpoints
│   ├── history.py        # Conversation history endpoints
│   └── system.py         # System status endpoints
├── models/               # Pydantic data models
│   ├── __init__.py
│   └── request.py        # Request/response models
└── services/             # Business logic services
    ├── __init__.py
    ├── agent_service.py  # Integration with ShoppingAgentApp
    └── database_service.py # SQLite database operations
```

## Installation

1. **Install dependencies:**
   ```bash
   cd api
   pip install -r requirements.txt
   ```

2. **Set up environment (optional):**
   ```bash
   # Create .env file for custom configuration
   echo "SHOPPING_AGENT_API_HOST=0.0.0.0" > .env
   echo "SHOPPING_AGENT_API_PORT=8000" >> .env
   echo "SHOPPING_AGENT_LOG_LEVEL=INFO" >> .env
   ```

## Running the Server

### Development Mode
```bash
cd api
python run.py
```

### Production Mode
```bash
cd api
SHOPPING_AGENT_ENV=production python run.py
```

### Using Uvicorn Directly
```bash
cd api
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

## API Documentation

Once the server is running, you can access:

- **Interactive API docs:** http://localhost:8000/docs
- **Alternative docs:** http://localhost:8000/redoc
- **OpenAPI schema:** http://localhost:8000/openapi.json

## API Endpoints

### Shopping Requests
- `POST /api/v1/requests` - Create a new shopping request
- `GET /api/v1/requests/{request_id}/status` - Get request status
- `GET /api/v1/requests/{request_id}/stream` - Stream real-time updates (WebSocket)
- `DELETE /api/v1/requests/{request_id}` - Cancel a request

### History Management
- `GET /api/v1/history/conversations` - Get conversation list
- `GET /api/v1/history/conversations/{conversation_id}` - Get conversation details
- `POST /api/v1/history/search` - Search conversations
- `GET /api/v1/history/analytics` - Get usage analytics
- `DELETE /api/v1/history/conversations/{conversation_id}` - Delete conversation
- `PUT /api/v1/history/conversations/{conversation_id}/archive` - Archive conversation

### System Monitoring
- `GET /api/v1/system/status` - Comprehensive system status
- `GET /api/v1/system/health` - Simple health check
- `GET /api/v1/system/metrics` - Detailed system metrics
- `GET /api/v1/system/config` - Get system configuration
- `PUT /api/v1/system/config` - Update system configuration

### Root Endpoints
- `GET /` - API information
- `GET /health` - Health check

## Usage Examples

### Create a Shopping Request
```bash
curl -X POST "http://localhost:8000/api/v1/requests" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "Find me the best laptop under $1000",
       "context": {"budget": 1000, "category": "electronics"},
       "user_id": "user123",
       "session_id": "session456"
     }'
```

### Check Request Status
```bash
curl "http://localhost:8000/api/v1/requests/{request_id}/status"
```

### Get Conversation History
```bash
curl "http://localhost:8000/api/v1/history/conversations?limit=10&offset=0"
```

### Search Conversations
```bash
curl -X POST "http://localhost:8000/api/v1/history/search" \
     -H "Content-Type: application/json" \
     -d '{
       "keyword": "laptop",
       "limit": 20,
       "offset": 0
     }'
```

## WebSocket Usage

For real-time updates, connect to the WebSocket endpoint:

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/requests/{request_id}/stream');

ws.onmessage = function(event) {
    const status = JSON.parse(event.data);
    console.log('Request status:', status);
};
```

## Configuration

The API server can be configured through environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `SHOPPING_AGENT_API_HOST` | `127.0.0.1` | Server host |
| `SHOPPING_AGENT_API_PORT` | `8000` | Server port |
| `SHOPPING_AGENT_LOG_LEVEL` | `INFO` | Logging level |
| `SHOPPING_AGENT_ENV` | `development` | Environment mode |
| `SHOPPING_AGENT_CORS_ORIGINS` | `http://localhost:3000,...` | Allowed CORS origins |
| `SHOPPING_AGENT_DATABASE_URL` | `shopping_agent.db` | SQLite database path |

## Integration with Existing Agent

The API server integrates with the existing `ShoppingAgentApp` through the `AgentService` class:

1. **Preserves existing functionality** - The CLI agent continues to work unchanged
2. **Async wrapper** - Provides async interface around the synchronous agent
3. **Progress tracking** - Simulates progress updates for better UX
4. **Error handling** - Graceful error handling and reporting
5. **Background processing** - Non-blocking request processing

## Database Schema

The API uses SQLite for storing conversation history:

- **conversations** - User conversation sessions
- **messages** - Individual messages within conversations
- **conversation_analytics** - Usage analytics and metrics

## Development

### Adding New Endpoints
1. Create route handlers in `routers/`
2. Define Pydantic models in `models/`
3. Implement business logic in `services/`
4. Update `main.py` to include new routers

### Testing
```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests (when implemented)
pytest
```

## Security Considerations

- **CORS configuration** - Properly configure allowed origins
- **Rate limiting** - Consider implementing rate limiting for production
- **API keys** - Add authentication for production use
- **Input validation** - All inputs are validated using Pydantic
- **Error handling** - Sensitive information is not exposed in error messages

## Troubleshooting

### Common Issues

1. **Import Error for `shopping_agent`**
   - Ensure the parent directory is in Python path
   - Check that `shopping_agent.py` exists in the project root

2. **Database Permission Issues**
   - Ensure write permissions for SQLite database file
   - Check disk space availability

3. **Port Already in Use**
   - Change the port using `SHOPPING_AGENT_API_PORT` environment variable
   - Kill existing processes using the port

4. **CORS Issues**
   - Update `SHOPPING_AGENT_CORS_ORIGINS` to include your frontend URL
   - Check browser developer tools for CORS errors

### Logging

Logs are output to console. For production, consider:
- Redirecting logs to files
- Using structured logging
- Implementing log rotation

## Next Steps

1. **Frontend Integration** - Connect with React/TypeScript frontend
2. **Authentication** - Add user authentication and authorization
3. **Rate Limiting** - Implement request rate limiting
4. **Caching** - Add response caching for better performance
5. **Monitoring** - Add application performance monitoring
6. **Testing** - Implement comprehensive test suite