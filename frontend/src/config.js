/**
 * Frontend Configuration
 * 
 * FOR VERCEL DEPLOYMENT:
 * - Replace 'YOUR_VERCEL_API_URL' below with your API deployment URL
 * - Example: 'https://your-api.vercel.app'
 */

const getApiBase = () => {
  const hostname = window.location.hostname;
  const isLocalhost = hostname === 'localhost' || hostname === '127.0.0.1';
  
  if (isLocalhost) {
    return 'http://localhost:8000';
  }
  
  // Production: Update this URL after deploying API to Vercel
  return 'https://langgraph-multi-agent-eosin.vercel.app';
};

export const config = {
  API_BASE: getApiBase()
};
