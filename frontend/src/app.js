/**
 * Main Application
 * Chat application logic and event handling
 */

import { sendChatMessage, getThreads, createThread, getThread, deleteThread } from './api.js';
import { 
  createMessageElement, 
  createLoadingElement, 
  createWelcomeElement,
  createHeaderElement,
  createInputElement,
  createThreadSidebarElement
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
    
    // Thread management
    this.threads = [];
    this.currentThreadId = null;
    
    // Sidebar state
    this.sidebarVisible = true;
    
    // DOM Elements
    this.app = document.getElementById('app');
    this.chatContainer = null;
    this.chatMessages = null;
    this.inputElement = null;
    this.sendButton = null;
    this.sidebarElement = null;
    this.sidebarToggle = null;
    
    // Bind methods
    this.handleSend = this.handleSend.bind(this);
    this.handleKeyDown = this.handleKeyDown.bind(this);
    this.handleScroll = this.handleScroll.bind(this);
    this.handleThreadClick = this.handleThreadClick.bind(this);
    this.handleNewChat = this.handleNewChat.bind(this);
    this.handleThreadDelete = this.handleThreadDelete.bind(this);
    this.handleSidebarToggle = this.handleSidebarToggle.bind(this);
    
    this.init();
  }
  
  /**
   * Toggle sidebar visibility
   */
  handleSidebarToggle() {
    this.sidebarVisible = !this.sidebarVisible;
    this.updateSidebarVisibility();
  }
  
  /**
   * Update sidebar visibility based on state
   */
  updateSidebarVisibility() {
    if (!this.sidebarElement) return;
    
    if (this.sidebarVisible) {
      this.sidebarElement.classList.remove('sidebar-hidden');
    } else {
      this.sidebarElement.classList.add('sidebar-hidden');
    }
  }
  
  /**
   * Initialize the application
   */
  async init() {
    this.render();
    this.bindEvents();
    await this.loadThreads();
    this.focusInput();
  }
  
  /**
   * Load threads from API
   */
  async loadThreads(loadMessages = true) {
    try {
      this.threads = await getThreads();
      this.renderSidebar();
      
      // If there's a current thread, load its messages
      if (this.currentThreadId && loadMessages) {
        await this.loadThreadMessages(this.currentThreadId);
      }
    } catch (error) {
      console.error('Error loading threads:', error);
    }
  }
  
  /**
   * Load messages for a specific thread from DB
   */
  async loadThreadMessages(threadId) {
    try {
      const thread = await getThread(threadId);
      this.messages = [];
      
      // Clear existing messages
      if (this.chatMessages) {
        this.chatMessages.innerHTML = '';
      }
      
      // Add messages from thread
      for (const msg of thread.messages) {
        const msgObj = {
          type: msg.role === 'user' ? 'user' : 'assistant',
          content: msg.content
        };
        this.messages.push(msgObj);
        this.appendMessage(msgObj, false);
      }

      this.renderSidebar(); // Update message counts in sidebar
      
    } catch (error) {
      console.error('Error loading thread messages:', error);
    }
  }
  
  /**
   * Create a new thread
   */
  async handleNewChat() {
    try {
      const thread = await createThread();
      this.threads.unshift(thread);
      this.currentThreadId = thread.id;
      this.messages = [];
      
      // Clear chat
      if (this.chatMessages) {
        this.chatMessages.innerHTML = '';
      }
      
      this.renderSidebar();
    } catch (error) {
      console.error('Error creating thread:', error);
    }
  }
  
  /**
   * Handle thread click - switch to that thread and load its messages
   */
  async handleThreadClick(threadId) {
    if (this.isLoading) return;
    
    this.currentThreadId = threadId;
    await this.loadThreadMessages(threadId);
  }
  
  /**
   * Handle thread delete
   */
  async handleThreadDelete(threadId, event) {
    event.stopPropagation();
    
    if (!confirm('Delete this chat?')) return;
    
    try {
      await deleteThread(threadId);
      
      // Remove from local list
      this.threads = this.threads.filter(t => t.id !== threadId);
      
      // If deleted current thread, switch to first available or create new
      if (this.currentThreadId === threadId) {
        if (this.threads.length > 0) {
          this.currentThreadId = this.threads[0].id;
          await this.loadThreadMessages(this.currentThreadId);
        } else {
          this.currentThreadId = null;
          this.messages = [];
          if (this.chatMessages) {
            this.chatMessages.innerHTML = createWelcomeElement();
          }
        }
      }
      
      this.renderSidebar();
    } catch (error) {
      console.error('Error deleting thread:', error);
    }
  }
  
  /**
   * Render the sidebar
   */
  renderSidebar() {
    if (!this.sidebarElement) return;
    console.log("create new sidebar", this.currentThreadId, this.threads);
    
    this.sidebarElement.innerHTML = '';
    const temp = document.createElement('div');
    temp.innerHTML = createThreadSidebarElement(this.threads, this.currentThreadId);
    this.sidebarElement.appendChild(temp.firstElementChild);
  }
  
  /**
   * Render the application layout
   */
  render() {
    this.app.innerHTML = `
      ${createHeaderElement()}
      <div class="main-layout">
        <div class="sidebar-container"></div>
        <div class="chat-container">
          <div class="chat-messages">
            ${createWelcomeElement()}
          </div>
        </div>
      </div>
      ${createInputElement(this.isLoading, this.totalTokens)}
    `;
    
    // Cache DOM references
    this.chatContainer = this.app.querySelector('.chat-container');
    this.chatMessages = this.app.querySelector('.chat-messages');
    this.sidebarElement = this.app.querySelector('.sidebar-container');
    this.inputElement = this.app.querySelector('.chat-input');
    this.sendButton = this.app.querySelector('.send-button');
    this.sidebarToggle = this.app.querySelector('#sidebar-toggle');
    
    // Render sidebar
    this.renderSidebar();
    
    // Set initial sidebar visibility
    this.updateSidebarVisibility();
    
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
   * this function will be called multiple times, so we need to ensure we don't bind duplicate listeners for static elements like the chat messages container and sidebar. We can use a flag to track if we've already bound those events.
   * For dynamic elements like the send button and input, we need to re-bind those every time we update the input area.
   */
  bindEvents() {    
    this.sendButton?.addEventListener('click', this.handleSend);
    this.inputElement?.addEventListener('keydown', this.handleKeyDown);
    this.sidebarToggle?.addEventListener('click', this.handleSidebarToggle);
    
    // Bind click events for chat messages and sidebar, but only once
    if (!this.eventsBound) {
      this.eventsBound = true;

      this.chatMessages?.addEventListener('click', (e) => {
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

      this.sidebarElement?.addEventListener('click', (e) => {
        // Handle new chat button
        const newChatBtn = e.target.closest('.new-chat-btn');
        if (newChatBtn) {
          this.handleNewChat();
          return;
        }
        
        // Handle thread item click
        const threadItem = e.target.closest('.thread-item');
        if (threadItem && !e.target.closest('.thread-delete')) {
          const threadId = threadItem.dataset.threadId;
          this.handleThreadClick(threadId);
          // Only toggle sidebar on mobile (where toggle button is visible)
          // On desktop, sidebar is always visible
          if (window.innerWidth <= 768) {
            this.handleSidebarToggle();
          }
          return;
        }
        
        // Handle delete button
        const deleteBtn = e.target.closest('.thread-delete');
        if (deleteBtn) {
          const threadId = deleteBtn.dataset.delete;
          this.handleThreadDelete(threadId, e);
          return;
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
    // Create new thread if none exists
    if (!this.currentThreadId) {
      try {
        const thread = await createThread();
        this.threads.unshift(thread);
        this.currentThreadId = thread.id;
        this.renderSidebar();
      } catch (error) {
        console.error('Error creating thread:', error);
      }
    }
    
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
        this.currentThreadId || 'default',
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
      
      // Refresh threads to update message counts
      await this.loadThreads(false);
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
