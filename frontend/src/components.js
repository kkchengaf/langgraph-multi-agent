/**
 * Components
 * Reusable UI components for the chat application
 */

/**
 * Format message content with basic markdown-like styling
 * @param {string} content - Raw message content
 * @returns {string} - Formatted HTML
 */
export function formatMessage(content) {
  if (!content) return '';
  return content
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>');
}

/**
 * Format JSON object for display
 * @param {Object} obj - Object to format
 * @returns {string} - Formatted JSON string
 */
export function formatJson(obj) {
  try {
    return JSON.stringify(obj, null, 2);
  } catch {
    return String(obj);
  }
}

/**
 * Get icon letter for message type
 * @param {string} type - Message type
 * @returns {string} - Icon letter(s)
 */
export function getMessageIcon(type) {
  const icons = {
    user: 'U',
    assistant: 'AI',
    reasoning: 'R',
    'tool-call': 'TC',
    'tool-result': 'TR'
  };
  return icons[type] || '?';
}

/**
 * Get display label for message type
 * @param {string} type - Message type
 * @returns {string} - Label
 */
export function getMessageLabel(type) {
  const labels = {
    user: 'User',
    assistant: 'Assistant',
    reasoning: 'Reasoning',
    'tool-call': 'Tool Call',
    'tool-result': 'Tool Result'
  };
  return labels[type] || 'Message';
}

/**
 * Check if message type is collapsible
 * @param {string} type - Message type
 * @returns {boolean}
 */
export function isCollapsibleType(type) {
  return ['reasoning', 'tool-call', 'tool-result'].includes(type);
}

/**
 * Create message element with collapsible functionality
 * @param {Object} msg - Message object with type, content, tool, args, result
 * @returns {string} - HTML string
 */
export function createMessageElement(msg, isCollapsed = true) {
  const icon = getMessageIcon(msg.type);
  const label = getMessageLabel(msg.type);
  const collapsible = isCollapsibleType(msg.type);
  const collapsed = collapsible && isCollapsed;
  
  let additionalContent = '';
  
  if (msg.type === 'tool-call') {
    additionalContent = `
      <div class="tool-call-info ">
        <div class="tool-call-info__name">${escapeHtml(msg.tool)}</div>
        <div class="tool-call-info__args">${escapeHtml(formatJson(msg.args))}</div>
      </div>
    `;
  }
  
  if (msg.type === 'tool-result') {
    additionalContent = `
      <div class="tool-result-content ">
        ${escapeHtml(msg.result)}
      </div>
    `;
  }
  
  // Build toggle button for collapsible types
  const toggleButton = collapsible ? `
    <button class="message-toggle" data-label="${label}">
      <span class="toggle-icon">${collapsed ? '▶' : '▼'}</span>
      <span class="toggle-text">${collapsed ? 'Show ' + label : 'Hide ' + label}</span>
    </button>
  ` : '';
  
  // For collapsed reasoning, show a preview
  let contentPreview = '';
  if (msg.type === 'reasoning' && collapsed) {
    const preview = msg.content ? msg.content.substring(0, 100) + '...' : '';
    contentPreview = `<div class="message-preview">${escapeHtml(preview)}</div>`;
  }
  
  return `
    <div class="message ${msg.type} ${collapsed && collapsible ? 'collapsed' : ''}">
      <div class="message-icon">${icon}</div>
      <div class="message-content">
        ${toggleButton}
        <div class="message-text">${formatMessage(msg.content)}${contentPreview}${additionalContent}</div>
      </div>
    </div>
  `;
}

/**
 * Create loading indicator element
 * @returns {string} - HTML string
 */
export function createLoadingElement() {
  return `
    <div class="message assistant loading-message" id="loading-indicator">
      <div class="message-icon">AI</div>
      <div class="message-content">
        <div class="loading">
          <div class="loading-dots">
            <span></span>
            <span></span>
            <span></span>
          </div>
          <span>Thinking...</span>
        </div>
      </div>
    </div>
  `;
}

/**
 * Create welcome screen element
 * @returns {string} - HTML string
 */
export function createWelcomeElement() {
  return `
    <div class="welcome">
      <div class="welcome-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
        </svg>
      </div>
      <h2>How can I help you today?</h2>
      <p>I can help you with weather information, mathematical calculations, web searches, and more.</p>
    </div>
  `;
}

/**
 * Escape HTML special characters
 * @param {string} text - Text to escape
 * @returns {string} - Escaped text
 */
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Create header element
 * @returns {string} - HTML string
 */
export function createHeaderElement() {
  return `
    <header class="header">
      <h1 class="header__title">LangGraph Agent</h1>
    </header>
  `;
}

/**
 * Create input area element
 * @param {boolean} isLoading - Whether chat is loading
 * @param {number} tokenCount - Current token count
 * @returns {string} - HTML string
 */
export function createInputElement(isLoading = false, tokenCount = 0) {
  return `
    <div class="input-container">
      <div class="input-wrapper">
        ${tokenCount > 0 ? `<div class="token-info">${tokenCount} tokens</div>` : ''}
        <textarea 
          class="chat-input" 
          placeholder="Send a message..."
          ${isLoading ? 'disabled' : ''}
        ></textarea>
        <button class="send-button" ${isLoading ? 'disabled' : ''}>
          <svg viewBox="0 0 24 24">
            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"></path>
          </svg>
        </button>
      </div>
    </div>
  `;
}
