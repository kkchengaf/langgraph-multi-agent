/**
 * Main Application
 * Chat application logic and event handling
 */

import { sendChatMessage } from './api.js';
import { 
  createMessageElement, 
  createLoadingElement, 
  createWelcomeElement,
  createHeaderElement,
  createInputElement 
} from './components.js';

/**
 * Chat Application Class
 */
class ChatApp {
  constructor() {
    this.messages = [];
    this.isLoading = false;
    this.totalTokens = 0;
    this.eventsBound = false;
    
    // DOM Elements
    this.app = document.getElementById('app');
    this.chatContainer = null;
    this.inputElement = null;
    this.sendButton = null;
    
    // Bind methods
    this.handleSend = this.handleSend.bind(this);
    this.handleKeyDown = this.handleKeyDown.bind(this);
    
    this.init();
  }
  
  /**
   * Initialize the application
   */
  init() {
    this.render();
    this.bindEvents();
    this.focusInput();
  }
  
  /**
   * Render the application layout
   */
  render() {
    this.app.innerHTML = `
      ${createHeaderElement()}
      <div class="chat-container">
        <div class="chat-messages">
          ${createWelcomeElement()}
        </div>
      </div>
      ${createInputElement(this.isLoading, this.totalTokens)}
    `;
    
    // Cache DOM references
    this.chatContainer = this.app.querySelector('.chat-container');
    this.inputElement = this.app.querySelector('.chat-input');
    this.sendButton = this.app.querySelector('.send-button');
  }
  
  /**
   * Bind event listeners
   */
  bindEvents() {
    this.sendButton?.addEventListener('click', this.handleSend);
    this.inputElement?.addEventListener('keydown', this.handleKeyDown);
    
    // Event delegation for collapsible messages - only add once
    if (!this.eventsBound && this.chatContainer) {
      this.eventsBound = true;
      this.chatContainer.addEventListener('click', (e) => {
        const toggleBtn = e.target.closest('.message-toggle');
        if (toggleBtn) {
          const messageEl = toggleBtn.closest('.message');
          if (messageEl) {
            messageEl.classList.toggle('collapsed');
            const isCollapsed = messageEl.classList.contains('collapsed');
            const label = toggleBtn.querySelector('.toggle-text');
            if (label) {
              const type = messageEl.classList.contains('reasoning') ? 'Reasoning' : 
                          messageEl.classList.contains('tool-call') ? 'Tool Call' : 
                          messageEl.classList.contains('tool-result') ? 'Tool Result' : 'Message';
              label.textContent = isCollapsed ? `Show ${type}` : `Hide ${type}`;
            }
          }
        }
      });
    }
  }
  
  /**
   * Handle send button click
   */
  async handleSend() {
    if (this.isLoading || !this.inputElement?.value.trim()) return;
    await this.sendMessage(this.inputElement.value.trim());
  }
  
  /**
   * Handle keyboard events
   */
  handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.handleSend();
    }
  }
  
  /**
   * Send a message to the API
   */
  async sendMessage(message) {
    // Clear input
    this.inputElement.value = '';
    
    // Add user message
    this.messages.push({ type: 'user', content: message });
    
    // Show loading immediately
    this.isLoading = true;
    this.updateMessages();
    this.updateInputArea();
    this.scrollToBottom();
    
    try {
      await sendChatMessage(
        message,
        'qwen3.5:9b',
        'default',
        (data) => {
          console.log('Received event:', data);
          this.handleStreamEvent(data);
        }
      );
    } catch (error) {
      console.error('Error:', error);
      this.messages.push({
        type: 'assistant',
        content: `Error: ${error.message}`
      });
      this.updateMessages();
    } finally {
      // Make sure loading state is properly reset
      this.isLoading = false;
      this.updateInputArea();
      this.updateMessages();
      this.scrollToBottom();
    }
  }
  
  /**
   * Handle streaming events from API
   */
  handleStreamEvent(data) {
    switch (data.type) {
      case 'reasoning':
        this.messages.push({
          type: 'reasoning',
          content: data.content
        });
        break;
        
      case 'tool_call':
        this.messages.push({
          type: 'tool-call',
          content: '',
          tool: data.tool,
          args: data.args
        });
        break;
        
      case 'tool_result':
        this.messages.push({
          type: 'tool-result',
          content: '',
          tool: data.tool,
          result: data.result
        });
        break;
        
      case 'final':
        const lastMsg = this.messages[this.messages.length - 1];
        if (lastMsg && lastMsg.type === 'assistant') {
          lastMsg.content += data.content;
        } else {
          this.messages.push({
            type: 'assistant',
            content: data.content
          });
        }
        break;
        
      case 'done':
        this.totalTokens = data.token_count || 0;
        this.isLoading = false;  // Ensure loading is stopped
        this.updateInputArea();
        break;
    }
    
    this.updateMessages();
  }
  
  /**
   * Update messages display
   */
  updateMessages() {
    const chatMessages = this.chatContainer?.querySelector('.chat-messages');
    if (!chatMessages) return;
    
    if (this.messages.length === 0) {
      chatMessages.innerHTML = createWelcomeElement();
      return;
    }
    
    chatMessages.innerHTML = this.messages
      .map(msg => createMessageElement(msg, true))
      .join('');
    
    if (this.isLoading) {
      chatMessages.insertAdjacentHTML('beforeend', createLoadingElement());
    }
  }
  
  /**
   * Update input area (loading state, token count)
   */
  updateInputArea() {
    const inputContainer = this.app.querySelector('.input-container');
    if (inputContainer) {
      inputContainer.outerHTML = createInputElement(this.isLoading, this.totalTokens);
      
      // Re-cache and rebind
      this.inputElement = this.app.querySelector('.chat-input');
      this.sendButton = this.app.querySelector('.send-button');
      this.bindEvents();
    }
  }
  
  /**
   * Scroll chat to bottom
   */
  scrollToBottom() {
    requestAnimationFrame(() => {
      this.chatContainer?.scrollTo({
        top: this.chatContainer.scrollHeight,
        behavior: 'smooth'
      });
    });
  }
  
  /**
   * Focus input element
   */
  focusInput() {
    this.inputElement?.focus();
  }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  new ChatApp();
});
