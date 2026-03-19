# LangGraph Agent API Server

FastAPI-based REST API for LangGraph Agent with streaming support.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the API server
python run_api.py
# Or directly
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agent/chat` | POST | LangGraph Agent with full streaming |
| `/api/chat` | POST | Simple chat (non-agent) |
| `/api/models` | GET | List available Ollama models |
| `/api/token-count` | GET | Get context token count |
| `/api/chat/clear` | POST | Clear conversation context |
| `/api/model/set` | POST | Set default model |
| `/api/model/current` | GET | Get current model |

## Features

- **Model Selection**: Choose from any Ollama model
- **Streaming Output**: Real-time SSE streaming for all responses
- **Tool Calling**: Built-in tools (weather, calculator, web search, time)
- **Context Management**: Token-aware conversation history
- **Thread Support**: Multiple conversation threads via thread_id

## Available Tools

The agent has access to these tools:

1. **get_weather** - Get weather information for a city
   - Input: `{"city": "Taipei"}`

2. **calculate** - Execute mathematical calculations
   - Input: `{"expression": "2 + 2"}`

3. **web_search** - Search the internet
   - Input: `{"query": "latest AI news"}`

4. **get_current_time** - Get current time
   - Input: `{"timezone": "Asia/Taipei"}`

## API Reference

### POST /api/agent/chat

LangGraph Agent with full ReAct workflow and streaming.

**Request:**
```json
{
  "message": "台北天氣如何？",
  "model": "qwen3.5:9b",
  "max_tokens": 2048,
  "temperature": 0.7,
  "thread_id": "default"
}
```

**Response (SSE Stream):**
```json
// Deep Reasoning
{"type": "reasoning", "content": "用戶詢問台北的天氣..."}

// Tool Call Request
{"type": "tool_call", "tool": "get_weather", "args": {"city": "Taipei"}, "reasoning": "需要獲取天氣資訊"}

// Tool Result
{"type": "tool_result", "tool": "get_weather", "result": "天氣：晴朗，溫度：25°C"}

// Final Answer
{"type": "final", "content": "台北目前天氣晴朗，溫度25°C..."}

// Done
{"type": "done", "token_count": 150}
```

### POST /api/chat

Simple chat without agent workflow.

**Request:**
```json
{
  "message": "你好",
  "model": "llama3.2",
  "max_tokens": 1024,
  "temperature": 0.7,
  "stream": true,
  "thread_id": "default"
}
```

**Response (SSE Stream):**
```json
{"content": "你好"}
{"done": true, "token_count": 10}
```

### GET /api/models

List available Ollama models.

**Response:**
```json
{
  "models": [
    {"name": "llama3.2", "size": 1234567890, "modified_at": "2024-01-01T00:00:00Z"}
  ],
  "count": 1
}
```

### GET /api/token-count

Get current context token usage.

**Query Parameters:**
- `thread_id`: Conversation thread ID (default: "default")

**Response:**
```json
{
  "total_tokens": 1500,
  "max_tokens": 4000,
  "usage_percentage": 37.5,
  "messages_count": 6
}
```

### POST /api/chat/clear

Clear conversation context.

**Query Parameters:**
- `thread_id`: Conversation thread ID (default: "default")

**Response:**
```json
{
  "status": "success",
  "message": "Conversation 'default' cleared"
}
```

### POST /api/model/set

Set default model.

**Query Parameters:**
- `model`: Model name

**Response:**
```json
{
  "status": "success",
  "message": "Default model set to 'qwen3.5:9b'",
  "current_model": "qwen3.5:9b"
}
```

### GET /api/model/current

Get current model.

**Response:**
```json
{
  "model": "qwen3.5:9b"
}
```

## Architecture

```
api/
├── main.py       # FastAPI app with CORS and lifespan
├── routes.py     # API endpoints
├── services.py   # Ollama & Agent services
└── models.py     # Pydantic models
```

## Environment Variables

Create a `.env` file:

```bash
# OpenWeather API (for weather tool)
OPEN_WEATHER_API_KEY=your_api_key

# LangSmith (optional, for debugging)
LANGCHAIN_API_KEY=your_langsmith_key
LANGCHAIN_TRACING_V2=true
```

## Testing with curl

```bash
# Test simple chat
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你好", "stream": true}'

# Test LangGraph agent
curl -X POST http://localhost:8000/api/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "台北天氣如何？", "model": "qwen3.5:9b"}'

# List models
curl http://localhost:8000/api/models

# Get token count
curl "http://localhost:8000/api/token-count?thread_id=default"
```

## Web UI

FastAPI auto-generates interactive documentation:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
