/**
 * API Service
 * Handles communication with the LangGraph Agent API
 */

const API_BASE = 'http://localhost:8000/api';

/**
 * Send a chat message and receive streaming response
 * @param {string} message - The user's message
 * @param {string} model - Model name (default: qwen3.5:9b)
 * @param {string} threadId - Thread ID for conversation context
 * @param {function} onEvent - Callback for each streaming event
 * @returns {Promise<void>}
 */
export async function sendChatMessage(message, model = 'qwen3.5:9b', threadId = 'default', onEvent = () => {}) {
  const response = await fetch(`${API_BASE}/agent/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      message,
      model,
      thread_id: threadId
    })
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        // Process any remaining buffer
        if (buffer.trim()) {
          processLine(buffer, onEvent);
        }
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      
      // Split by double newlines (SSE event separator)
      const lines = buffer.split('\n\n');
      
      // Keep the last part in buffer (might be incomplete)
      buffer = lines.pop() || '';
      
      // Process all complete lines
      for (const line of lines) {
        processLine(line, onEvent);
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/**
 * Process a single SSE line
 * @param {string} line - The raw line
 * @param {function} onEvent - Callback for each event
 */
function processLine(line, onEvent) {
  const trimmed = line.trim();
  
  if (trimmed.startsWith('data: ')) {
    try {
      const jsonStr = trimmed.slice(6); // Remove 'data: ' prefix
      const data = JSON.parse(jsonStr);
      onEvent(data);
    } catch (e) {
      console.error('Parse error:', e, 'Raw:', trimmed);
    }
  }
}

/**
 * Get list of available models
 * @returns {Promise<Array>}
 */
export async function getModels() {
  const response = await fetch(`${API_BASE}/models`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  const data = await response.json();
  return data.models || [];
}

/**
 * Get token count for a thread
 * @param {string} threadId - Thread ID
 * @returns {Promise<Object>}
 */
export async function getTokenCount(threadId = 'default') {
  const response = await fetch(`${API_BASE}/token-count?thread_id=${threadId}`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

/**
 * Clear conversation context
 * @param {string} threadId - Thread ID
 * @returns {Promise<void>}
 */
export async function clearConversation(threadId = 'default') {
  const response = await fetch(`${API_BASE}/chat/clear?thread_id=${threadId}`, {
    method: 'POST'
  });
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
}
