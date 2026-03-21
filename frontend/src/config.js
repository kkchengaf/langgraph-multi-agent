/**
 * Frontend Configuration
 * 
 * This file configures the API endpoint for the LangGraph Agent.
 * 
 * DEFAULT BEHAVIOR (auto-detect):
 * - When accessing from localhost: uses http://localhost:8000
 * - When accessing from other devices (same network): auto-detects IP
 * 
 * MANUAL OVERRIDE:
 * - Edit API_BASE below to set a specific IP/hostname
 * - e.g., 'http://192.168.0.100:8000'
 */

// Default: auto-detect based on current browser hostname
const autoDetectApiBase = () => {
  const hostname = window.location.hostname;
  const isLocalhost = hostname === 'localhost' || hostname === '127.0.0.1';
  
  if (isLocalhost) {
    return 'http://localhost:8000';
  }
  
  // For network access, assume API is on same host but port 8000
  // If frontend is on port 8001, change to ':8001' below if needed
  return `http://${hostname}:8000`;
};

export const config = {
  // API server base URL
  // Override this value to use a specific IP/hostname
  // Example: 'http://192.168.0.100:8000'
  API_BASE: autoDetectApiBase()
};
