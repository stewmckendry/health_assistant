/**
 * API configuration for backend connections
 */

export const getApiUrl = () => {
  // Use environment variable or fallback to localhost for development
  return process.env.NEXT_PUBLIC_API_URL || process.env.API_URL || 'http://localhost:8000';
};

export const getApiEndpoint = (path: string) => {
  const baseUrl = getApiUrl();
  // Ensure path starts with /
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${baseUrl}${normalizedPath}`;
};