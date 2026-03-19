# LangGraph Agent Frontend

Minimalist chatbot UI for the LangGraph Agent API.

## Project Structure

```
frontend/
├── index.html          # Entry point
├── src/
│   ├── styles.css      # Global styles (CSS variables, base styles)
│   ├── api.js         # API service (HTTP requests)
│   ├── components.js  # UI components (message, input, etc.)
│   └── app.js         # Main application logic
└── README.md          # This file
```

## Quick Start

### Option 1: Direct Open (with ES Modules support)

You need a local server due to ES modules CORS restrictions:

```bash
# Using Python
cd frontend
python -m http.server 8080

# Using Node.js
npx serve frontend
```

Then open `http://localhost:8080`

### Option 2: With API Server

1. Start the API server:
```bash
python run_api.py
```

2. Start the frontend server:
```bash
cd frontend
python -m http.server 8080
```

3. Open `http://localhost:8080`

## Features

- **Real-time streaming** - See agent thinking, tool calls, and responses as they happen
- **Message types**:
  - User messages (purple icon)
  - Assistant/AI messages (green icon)
  - Reasoning messages (orange icon)
  - Tool call requests (purple icon)
  - Tool execution results (green icon)
- **Minimalist design** - Clean, distraction-free interface
- **Keyboard support** - Press Enter to send message

## API Configuration

The API base URL is configured in `src/api.js`:

```javascript
const API_BASE = 'http://localhost:8000/api';
```

## Design System

### Colors (CSS Variables)

| Variable | Color | Usage |
|----------|-------|-------|
| `--color-accent` | #10a37f | AI messages, buttons |
| `--color-user` | #5436da | User messages |
| `--color-reasoning` | #f59e0b | Reasoning messages |
| `--color-tool-call` | #8b5cf6 | Tool call indicators |
| `--color-tool-result` | #10a37f | Tool results |

### Typography

- Font: Inter (via Google Fonts)
- Monospace: SF Mono / Consolas

## File Descriptions

### `src/styles.css`
- CSS custom properties (design tokens)
- Base styles and resets
- Component styles
- Animations

### `src/api.js`
- `sendChatMessage()` - Send message with streaming
- `getModels()` - List available Ollama models
- `getTokenCount()` - Get context token usage
- `clearConversation()` - Clear conversation history

### `src/components.js`
- `formatMessage()` - Format message content
- `formatJson()` - Format JSON for display
- `createMessageElement()` - Create message HTML
- `createLoadingElement()` - Create loading indicator
- `createWelcomeElement()` - Create welcome screen

### `src/app.js`
- `ChatApp` class - Main application
- Event handling
- State management
- DOM manipulation
