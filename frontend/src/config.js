/**
 * Frontend Configuration
 * 
 * This file configures the API endpoint for the LangGraph Agent.
 * 
 * FOR VERCEL DEPLOYMENT:
 * - Set VERCEL_PROD_URL to your Render backend URL
 * - Format: 'https://your-app.onrender.com'
 * 
 * FOR LOCAL DEVELOPMENT:
 * - Uses http://localhost:8000
 */

const getApiBase = () => {
  const hostname = window.location.hostname;
  const isLocalhost = hostname === 'localhost' || hostname === '127.0.0.1';
  
  if (isLocalhost) {
    return 'http://localhost:8000';
  }
  
  // Production: use environment variable or default to same host
  return window.ENV_API_URL || `https://your-render-app.onrender.com`;
};

export const config = {
  API_BASE: getApiBase()
};

// Expose ENV variable for Vercel
if (typeof window !== 'undefined') {
  window.ENV_API_URL = import.meta?.env?.VITE_API_URL || 'https://your-render-app.onrender.com';
}
