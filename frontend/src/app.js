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
    this.isAtBottom = true;
    this.messageCount = 0;
    
    // DOM Elements
    this.app = document.getElementById('app');
    this.chatContainer = null;
    this.chatMessages = null;
    this.inputElement = null;
    this.sendButton = null;
    
    // Bind methods
    this.handleSend = this.handleSend.bind(this);
    this.handleKeyDown = this.handleKeyDown.bind(this);
    this.handleScroll = this.handleScroll.bind(this);
    
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
    this.chatMessages = this.app.querySelector('.chat-messages');
    this.inputElement = this.app.querySelector('.chat-input');
    this.sendButton = this.app.querySelector('.send-button');
    
    // Bind scroll handler
    this.chatContainer?.addEventListener('scroll', this.handleScroll);
  }
  
  /**
   * Handle scroll events to detect if user is at bottom
   */
  handleScroll() {
    if (!this.chatContainer) return;
    const { scrollTop, scrollHeight, clientHeight } = this.chatContainer;
    // Consider "at bottom" if within 50px of bottom
    this.isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
  }
  
  /**
   * Bind event listeners
   */
  bindEvents() {
    this.sendButton?.addEventListener('click', this.handleSend);
    this.inputElement?.addEventListener('keydown', this.handleKeyDown);
    
    // Event delegation for collapsible messages - only add once
    if (!this.eventsBound && this.chatMessages) {
      this.eventsBound = true;
      this.chatMessages.addEventListener('click', (e) => {
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
   * Check if user is at bottom of chat
   */
  checkIfAtBottom() {
    if (!this.chatContainer) return true;
    const { scrollTop, scrollHeight, clientHeight } = this.chatContainer;
    return scrollHeight - scrollTop - clientHeight < 50;
  }
  
  /**
   * Scroll to bottom if user is at bottom
   */
  scrollToBottom(force = false) {
    if (!this.chatContainer) return;
    if (force || this.isAtBottom) {
      this.chatContainer.scrollTop = this.chatContainer.scrollHeight;
    }
  }
  
  /**
   * Add a single message to the DOM
   */
  appendMessage(msg, isCollapsed = true, beforeLoading = false) {
    if (!this.chatMessages) return;
    
    // Remove welcome screen if it exists
    const welcome = this.chatMessages.querySelector('.welcome');
    if (welcome) {
      welcome.remove();
    }
    
    // Create message element
    const msgEl = document.createElement('div');
    msgEl.innerHTML = createMessageElement(msg, isCollapsed);
    const messageNode = msgEl.firstElementChild;
    
    // Find loading element
    const loadingEl = this.chatMessages.querySelector('.loading-message');
    
    if (loadingEl && beforeLoading) {
      // Insert before loading element
      this.chatMessages.insertBefore(messageNode, loadingEl);
    } else {
      // Append to end
      this.chatMessages.appendChild(messageNode);
    }
    
    this.messageCount++;
  }
  
  /**
   * Add loading indicator to DOM
   */
  addLoadingIndicator() {
    if (!this.chatMessages) return;
    
    // Remove welcome screen if it exists
    const welcome = this.chatMessages.querySelector('.welcome');
    if (welcome) {
      welcome.remove();
    }
    
    // Create loading element
    const loadingEl = document.createElement('div');
    loadingEl.innerHTML = createLoadingElement();
    this.chatMessages.appendChild(loadingEl.firstElementChild);
    
    // Scroll to bottom only if user is at bottom
    this.scrollToBottom();
  }
  
  /**
   * Send a message to the API
   */
  async sendMessage(message) {
    // Clear input
    this.inputElement.value = '';
    
    // Add user message
    this.messages.push({ type: 'user', content: message });
    this.appendMessage({ type: 'user', content: message }, false);
    
    // Add loading indicator
    this.isLoading = true;
    this.addLoadingIndicator();    
    this.scrollToBottom(true);
    
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
      this.appendMessage({
        type: 'assistant',
        content: `Error: ${error.message}`
      }, false);
    } finally {
      // Remove loading indicator
      this.isLoading = false;
      this.removeLoadingIndicator();
      
      // Scroll to bottom (don't force)
      this.scrollToBottom();
    }
  }
  
  /**
   * Remove loading indicator from DOM
   */
  removeLoadingIndicator() {
    const loadingEl = this.chatMessages?.querySelector('.loading-message');
    if (loadingEl) {
      loadingEl.remove();
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
        this.appendMessage({
          type: 'reasoning',
          content: data.content
        }, true, true); // Collapsed by default, insert before loading
        this.scrollToBottom();
        break;
        
      case 'tool_call':
        this.messages.push({
          type: 'tool-call',
          content: '',
          tool: data.tool,
          args: data.args
        });
        this.appendMessage({
          type: 'tool-call',
          content: '',
          tool: data.tool,
          args: data.args
        }, true, true); // Collapsed by default, insert before loading
        this.scrollToBottom();
        break;
        
      case 'tool_result':
        this.messages.push({
          type: 'tool-result',
          content: '',
          tool: data.tool,
          result: data.result
        });
        this.appendMessage({
          type: 'tool-result',
          content: '',
          tool: data.tool,
          result: data.result
        }, true, true); // Collapsed by default, insert before loading
        this.scrollToBottom();
        break;
        
      case 'final':
        // Check if last message is assistant and append to it
        const lastMsg = this.messages[this.messages.length - 1];
        if (lastMsg && lastMsg.type === 'assistant') {
          lastMsg.content += data.content;
          // Update the last message element
          const msgEls = this.chatMessages?.querySelectorAll('.message.assistant');
          if (msgEls && msgEls.length > 0) {
            const lastEl = msgEls[msgEls.length - 1];
            const textEl = lastEl.querySelector('.message-text');
            if (textEl) {
              textEl.innerHTML = data.content.replace(/\n/g, '<br>');
            }
          }
        } else {
          this.messages.push({
            type: 'assistant',
            content: data.content
          });
          this.appendMessage({
            type: 'assistant',
            content: data.content
          }, false, true);
        }
        this.scrollToBottom();
        break;
        
      case 'done':
        this.totalTokens = data.token_count || 0;
        this.isLoading = false;
        this.updateInputArea();
        this.removeLoadingIndicator();
        break;
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
