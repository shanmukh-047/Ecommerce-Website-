/**
 * Bharat Masala - Centralized Production API Client
 *
 * Provides a robust, unified fetch interface to the Django REST Framework backend.
 * Features:
 * - Environment variable base URL resolution (Next.js, Vite, and framework equivalents)
 * - Automatic API prefix normalization (/api/v1)
 * - Extensible Request and Response Interceptor pipeline
 * - Dynamic JWT Bearer token injection and concurrent 401 silent token refresh
 * - Standard DRF response envelope normalization ({ success, request_id, message, data, error })
 * - Reusable user-friendly error formatting and developer diagnostic logging
 * - Request cancellation (AbortController) and configurable timeout handling
 * - Clean backward compatibility with all frontend services and contexts
 */

// ============================================================================
// 1. CONFIGURATION & URL RESOLUTION
// ============================================================================

const DEFAULT_DEV_HOST = 'http://127.0.0.1:8000';
const DEFAULT_API_PREFIX = '/api/v1';

/**
 * Resolves the backend base URL from environment variables.
 * Checks Next.js (NEXT_PUBLIC_API_BASE_URL, NEXT_PUBLIC_API_URL)
 * and Vite/CRA (VITE_API_BASE_URL, REACT_APP_API_BASE_URL).
 */
export function getBaseUrl() {
  // In the browser, ALWAYS use relative URLs (empty string) so all API requests route via
  // the Next.js rewrites proxy. This guarantees that mobile phones on LAN, desktop browsers,
  // tablets, and production domain deployments all communicate without cross-origin blocks,
  // hardcoded 127.0.0.1 unreachable host errors, or cookie partition issues.
  if (typeof window !== 'undefined') {
    const forceAbsolute = process.env.NEXT_PUBLIC_FORCE_ABSOLUTE_API_URL;
    if (forceAbsolute && forceAbsolute.trim()) {
      return forceAbsolute.trim().replace(/\/+$/, '');
    }
    return '';
  }

  const envBase =
    process.env.BACKEND_INTERNAL_URL ||
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.VITE_API_BASE_URL ||
    process.env.REACT_APP_API_BASE_URL;

  if (envBase && envBase.trim()) {
    return envBase.trim().replace(/\/+$/, '');
  }

  // In production SSR/server, relative URL is preferred if no host configured
  if (process.env.NODE_ENV === 'production') {
    return '';
  }

  // Development server fallback
  return DEFAULT_DEV_HOST;
}

export function getApiPrefix() {
  const envPrefix =
    process.env.NEXT_PUBLIC_API_PREFIX ||
    process.env.VITE_API_PREFIX ||
    DEFAULT_API_PREFIX;

  return envPrefix.trim().replace(/\/+$/, '');
}

/**
 * Builds a clean, fully-qualified or normalized API URL.
 * Prevents double slashes and ensures /api/v1 prefix is never duplicated.
 */
export function resolveApiUrl(endpoint) {
  if (!endpoint) return '';

  // Return fully-qualified external URLs as-is
  if (/^https?:\/\//i.test(endpoint)) {
    return endpoint;
  }

  const baseUrl = getBaseUrl();
  const prefix = getApiPrefix();

  // Split query string if any
  const [pathPart, ...queryParts] = endpoint.split('?');
  const queryString = queryParts.join('?');

  // Normalize endpoint: strip leading and trailing slashes
  let cleanEndpoint = pathPart.replace(/^\/+/, '').replace(/\/+$/, '');

  // Strip prefix from endpoint if already provided by caller (e.g. "api/v1/catalog" -> "catalog")
  const cleanPrefix = prefix.replace(/^\/+/, '').replace(/\/+$/, '');
  if (cleanEndpoint.startsWith(cleanPrefix + '/')) {
    cleanEndpoint = cleanEndpoint.slice(cleanPrefix.length + 1);
  } else if (cleanEndpoint === cleanPrefix) {
    cleanEndpoint = '';
  }

  // Construct combined path
  let path = '';
  if (baseUrl) {
    const cleanBase = baseUrl.replace(/\/+$/, '');
    if (cleanBase.endsWith(cleanPrefix)) {
      path = cleanEndpoint ? `${cleanBase}/${cleanEndpoint}` : cleanBase;
    } else if (cleanBase.endsWith('/api') && cleanPrefix.startsWith('api/')) {
      const remainingPrefix = cleanPrefix.slice(4);
      path = cleanEndpoint
        ? `${cleanBase}/${remainingPrefix}/${cleanEndpoint}`
        : `${cleanBase}/${remainingPrefix}`;
    } else {
      path = cleanEndpoint ? `${cleanBase}/${cleanPrefix}/${cleanEndpoint}` : `${cleanBase}/${cleanPrefix}`;
    }
  } else {
    // Relative browser URL
    path = cleanEndpoint ? `/${cleanPrefix}/${cleanEndpoint}` : `/${cleanPrefix}`;
  }

  // Ensure clean single slashes (preserve protocol if absolute)
  if (/^https?:\/\//i.test(path)) {
    const urlObj = new URL(path);
    urlObj.pathname = urlObj.pathname.replace(/\/+/g, '/');
    if (!urlObj.pathname.endsWith('/') && !/\.[a-z0-9]+$/i.test(urlObj.pathname)) {
      urlObj.pathname += '/';
    }
    path = urlObj.toString().replace(/\/+$/, '/');
  } else {
    path = path.replace(/\/+/g, '/');
    if (!path.endsWith('/') && !/\.[a-z0-9]+$/i.test(path)) {
      path += '/';
    }
  }

  return queryString ? `${path}?${queryString}` : path;
}

// ============================================================================
// 2. ERROR CLASSES & USER-FRIENDLY ERROR NORMALIZATION
// ============================================================================

export class ApiError extends Error {
  constructor({
    message,
    status = 0,
    code = 'API_ERROR',
    userMessage = null,
    details = null,
    requestId = null,
    raw = null,
    isNetworkError = false,
    isCancelled = false,
  }) {
    super(message || 'An unexpected API error occurred.');
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
    this.requestId = requestId;
    this.raw = raw;
    this.isNetworkError = isNetworkError;
    this.isCancelled = isCancelled;
    this.userMessage = userMessage || formatApiErrorMessage(this);
  }
}

/**
 * Translates technical error responses into friendly, human-readable messages.
 * Never exposes raw SQL queries, stack traces, or internal server paths.
 */
export function formatApiErrorMessage(error) {
  if (!error) return 'An unexpected error occurred. Please try again.';

  if (error.isCancelled) {
    return 'The request was cancelled.';
  }

  if (error.isNetworkError || error.status === 0) {
    return 'Unable to connect to the server. Please check your internet connection.';
  }

  // Handle detailed field validation errors
  if (error.details && typeof error.details === 'object') {
    const errorEntries = Object.entries(error.details);
    if (errorEntries.length > 0) {
      const messages = [];
      for (const [field, msgs] of errorEntries) {
        if (field === 'non_field_errors' || field === 'detail') {
          messages.push(Array.isArray(msgs) ? msgs.join(' ') : String(msgs));
        } else {
          const fieldLabel = field.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
          const fieldMsg = Array.isArray(msgs) ? msgs.join(' ') : String(msgs);
          messages.push(`${fieldLabel}: ${fieldMsg}`);
        }
      }
      if (messages.length > 0) {
        return messages.join(' • ');
      }
    }
  }

  // Standard status and code translations
  switch (error.code) {
    case 'AUTHENTICATION_FAILED':
    case 'SESSION_EXPIRED':
      return 'Your session has expired. Please sign in again to continue.';
    case 'PERMISSION_DENIED':
      return 'You do not have permission to perform this action.';
    case 'RESOURCE_NOT_FOUND':
      return 'The requested spice item or resource could not be found.';
    case 'RATE_LIMIT_EXCEEDED':
      return 'Too many requests. Please wait a moment before trying again.';
    case 'CONFLICT':
      return error.message || 'The request conflicts with the current order or stock state.';
    case 'VALIDATION_ERROR':
      return error.message || 'Please check your submitted information and try again.';
    case 'TIMEOUT_ERROR':
      return 'The request timed out. Please try again.';
    default:
      break;
  }

  // Status-based fallbacks
  if (error.status === 401) return 'Please sign in to continue.';
  if (error.status === 403) return 'You do not have permission to access this resource.';
  if (error.status === 404) return 'The requested resource was not found.';
  if (error.status === 409) return error.message || 'Action cannot be completed in the current state.';
  if (error.status === 429) return 'Too many attempts. Please wait a moment.';
  if (error.status >= 500) return 'Our spice servers experienced a temporary hiccup. Please try again shortly.';

  return error.message || 'An error occurred while communicating with Bharat Masala.';
}

export function isApiError(err) {
  return err instanceof ApiError || (err && err.name === 'ApiError');
}

export function isCancelError(err) {
  if (!err) return false;
  return Boolean(
    err.isCancelled ||
    err.name === 'AbortError' ||
    err.code === 'CANCELLED_ERROR' ||
    err.code === 20 ||
    err.name === 'CanceledError' ||
    (typeof err.message === 'string' && (
      err.message.toLowerCase().includes('aborted') ||
      err.message.toLowerCase().includes('canceled') ||
      err.message.includes('The user aborted a request')
    )) ||
    err.raw?.name === 'AbortError' ||
    (typeof err.raw?.message === 'string' && (
      err.raw.message.toLowerCase().includes('aborted') ||
      err.raw.message.includes('The user aborted a request')
    ))
  );
}

// ============================================================================
// 3. IN-MEMORY & LOCAL TOKEN STORAGE
// ============================================================================

let inMemoryToken = null;
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

export const getAccessToken = () => {
  if (inMemoryToken) return inMemoryToken;
  if (typeof window !== 'undefined') {
    return localStorage.getItem('bharat_access_token');
  }
  return null;
};

export const setAccessToken = (token) => {
  inMemoryToken = token;
  if (typeof window !== 'undefined') {
    if (token) {
      localStorage.setItem('bharat_access_token', token);
    } else {
      localStorage.removeItem('bharat_access_token');
    }
  }
  if (typeof api !== 'undefined' && api?.clearInFlightRequests) {
    api.clearInFlightRequests();
  }
};

export const clearAccessToken = () => {
  inMemoryToken = null;
  if (typeof window !== 'undefined') {
    localStorage.removeItem('bharat_access_token');
  }
  if (typeof api !== 'undefined' && api?.clearInFlightRequests) {
    api.clearInFlightRequests();
  }
};

/**
 * Execute silent refresh via DRF /auth/token/refresh/ using HttpOnly cookie.
 */
async function refreshAuthToken() {
  const refreshUrl = resolveApiUrl('/auth/token/refresh/');

  try {
    const res = await fetch(refreshUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify({}),
    });

    const payload = await res.json().catch(() => null);

    if (!res.ok || !payload) {
      throw new Error(payload?.error?.message || payload?.message || 'Token refresh failed');
    }

    const newAccessToken =
      payload.data?.access_token || payload.access_token || payload.data?.token;

    if (newAccessToken) {
      setAccessToken(newAccessToken);
      return newAccessToken;
    }
    throw new Error('No access token in refresh response');
  } catch (err) {
    clearAccessToken();
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('bharat:auth-expired'));
    }
    throw err;
  }
}

// ============================================================================
// 4. REQUEST CANCELLATION & TIMEOUT UTILITIES
// ============================================================================

/**
 * Creates an AbortController with helper cancel method.
 */
export function createCancelToken() {
  const controller = new AbortController();
  return {
    controller,
    signal: controller.signal,
    cancel: (reason) => controller.abort(reason),
  };
}

// ============================================================================
// 5. INTERCEPTORS PIPELINE
// ============================================================================

class InterceptorManager {
  constructor() {
    this.handlers = [];
  }

  use(onFulfilled, onRejected) {
    this.handlers.push({ onFulfilled, onRejected });
    return this.handlers.length - 1;
  }

  eject(id) {
    if (this.handlers[id]) {
      this.handlers[id] = null;
    }
  }
}

// ============================================================================
// 6. CORE API CLIENT CLASS
// ============================================================================

export class ApiClient {
  constructor(defaultConfig = {}) {
    this.defaultConfig = defaultConfig;
    this.interceptors = {
      request: new InterceptorManager(),
      response: new InterceptorManager(),
    };
    this.inFlightRequests = new Map();

    this.setupDefaultInterceptors();
  }

  clearInFlightRequests() {
    this.inFlightRequests.clear();
  }

  setupDefaultInterceptors() {
    // Default Request Interceptor: Attach Auth Token, Correlation ID, and Headers
    this.interceptors.request.use(async (config) => {
      const token = getAccessToken();
      const headers = {
        Accept: 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(config.headers || {}),
      };

      // Set JSON Content-Type only if payload is not FormData
      if (!(config.body instanceof FormData) && !headers['Content-Type'] && config.method !== 'GET') {
        headers['Content-Type'] = 'application/json';
      }

      return {
        ...config,
        headers,
        credentials: config.credentials || 'include',
      };
    });
  }

  /**
   * Main request execution method.
   */
  async request(endpoint, options = {}, isRetry = false) {
    const url = resolveApiUrl(endpoint);
    let config = {
      method: 'GET',
      ...this.defaultConfig,
      ...options,
      endpoint,
      url,
    };

    // Run request interceptors
    for (const interceptor of this.interceptors.request.handlers) {
      if (interceptor && interceptor.onFulfilled) {
        try {
          config = await interceptor.onFulfilled(config);
        } catch (err) {
          if (interceptor.onRejected) {
            return interceptor.onRejected(err);
          }
          throw err;
        }
      }
    }

    const isGet = (config.method || 'GET').toUpperCase() === 'GET';

    // Non-GET mutations immediately clear in-flight GET cache and are never deduplicated
    if (!isGet) {
      this.clearInFlightRequests();
    }

    const canDedupe = isGet && !isRetry && !options.noDedupe && !options.skipCache && !config.signal;
    const authKey = config.headers?.Authorization || 'GUEST';
    const cacheKey = canDedupe ? `${authKey}:::${config.url}` : null;

    if (cacheKey && this.inFlightRequests.has(cacheKey)) {
      return this.inFlightRequests.get(cacheKey);
    }

    const execute = async () => {
      // Set up request timeout if specified (default 15,000ms)
      const timeoutMs = config.timeout !== undefined ? config.timeout : 15000;
      let timeoutId = null;
      let internalAbortController = null;

      if (timeoutMs > 0 && !config.signal) {
        internalAbortController = new AbortController();
        config.signal = internalAbortController.signal;
        timeoutId = setTimeout(() => {
          internalAbortController.abort('REQUEST_TIMEOUT');
        }, timeoutMs);
      }

    try {
      if (config.signal?.aborted) {
        throw new ApiError({
          message: 'Request cancelled',
          status: 0,
          code: 'CANCELLED_ERROR',
          isCancelled: true,
        });
      }

      const response = await fetch(config.url, {
        method: config.method,
        headers: config.headers,
        body: config.body,
        credentials: config.credentials,
        signal: config.signal,
      });

      if (timeoutId) clearTimeout(timeoutId);

      const requestIdHeader = response.headers.get('x-request-id') || null;

      // Handle 401 Unauthorized with token refresh
      // Skip for auth login/refresh routes and sensitive non-idempotent mutations (payments, checkout)
      const isAuthRoute =
        endpoint.includes('/auth/login') ||
        endpoint.includes('/auth/token/refresh') ||
        endpoint.includes('/auth/register') ||
        endpoint.includes('/auth/me');

      const isNonIdempotentPost =
        config.method === 'POST' &&
        (endpoint.includes('/payments') || endpoint.includes('/checkout') || endpoint.includes('/orders'));

      if (response.status === 401 && !isRetry && !isAuthRoute && !isNonIdempotentPost) {
        if (isRefreshing) {
          return new Promise((resolve, reject) => {
            failedQueue.push({ resolve, reject });
          })
            .then(() => this.request(endpoint, options, true))
            .catch((err) => Promise.reject(err));
        }

        isRefreshing = true;

        try {
          const newToken = await refreshAuthToken();
          processQueue(null, newToken);
          isRefreshing = false;
          return this.request(endpoint, options, true);
        } catch (refreshErr) {
          processQueue(refreshErr, null);
          isRefreshing = false;
          throw new ApiError({
            message: 'Session expired. Please sign in again.',
            status: 401,
            code: 'SESSION_EXPIRED',
            userMessage: 'Your session has expired. Please sign in again.',
            requestId: requestIdHeader,
          });
        }
      }

      // Parse response body
      const responseText = await response.text();
      let rawData = null;
      try {
        rawData = responseText ? JSON.parse(responseText) : null;
      } catch {
        rawData = responseText;
      }

      // Check HTTP error status
      if (!response.ok) {
        const errorPayload = rawData?.error || null;
        const errorCode = errorPayload?.code || `HTTP_${response.status}`;
        const errorDetails = errorPayload?.details || rawData?.errors || rawData?.detail || null;
        const errorMessage =
          rawData?.message ||
          errorPayload?.message ||
          (typeof rawData === 'string' ? rawData : `Request failed with status ${response.status}`);
        const requestId = rawData?.request_id || requestIdHeader;

        // Developer logging in non-production
        if (process.env.NODE_ENV !== 'production') {
          console.warn(
            `[API ERROR] ${config.method} ${config.url} [Status: ${response.status}] [Req: ${requestId || 'N/A'}]`,
            { error: errorMessage, code: errorCode, details: errorDetails }
          );
        }

        throw new ApiError({
          message: errorMessage,
          status: response.status,
          code: errorCode,
          details: errorDetails,
          requestId,
          raw: rawData,
        });
      }

      // HTTP 204 No Content
      if (response.status === 204 || !rawData) {
        return null;
      }

      // Unpack standard backend envelope { success, request_id, message, data, error }
      if (rawData && typeof rawData === 'object' && 'success' in rawData && 'data' in rawData) {
        const payload = rawData.data;

        // If caller explicitly requested the full envelope via options.rawEnvelope
        if (options.rawEnvelope) {
          return rawData;
        }

        // Attach non-enumerable metadata to payload if it is an object
        if (payload && typeof payload === 'object') {
          try {
            Object.defineProperties(payload, {
              _envelope: {
                value: {
                  success: rawData.success,
                  requestId: rawData.request_id || requestIdHeader,
                  message: rawData.message,
                },
                writable: true,
                enumerable: false,
                configurable: true,
              },
              _requestId: {
                value: rawData.request_id || requestIdHeader,
                writable: true,
                enumerable: false,
                configurable: true,
              },
            });
          } catch {
            // Ignore non-configurable primitives
          }
        }

        return payload;
      }

      return rawData;
    } catch (err) {
      if (timeoutId) clearTimeout(timeoutId);

      if (err instanceof ApiError) {
        throw err;
      }

      // Aborted / Cancelled request
      if (err.name === 'AbortError' || err === 'REQUEST_TIMEOUT' || isCancelError(err)) {
        const isTimeout = err === 'REQUEST_TIMEOUT' || internalAbortController?.signal?.reason === 'REQUEST_TIMEOUT';
        throw new ApiError({
          message: isTimeout ? 'Request timeout' : 'Request cancelled',
          status: 0,
          code: isTimeout ? 'TIMEOUT_ERROR' : 'CANCELLED_ERROR',
          isCancelled: !isTimeout,
          raw: err,
        });
      }

      // Network connection failure
      throw new ApiError({
        message: err.message || 'Network connection failed',
        status: 0,
        code: 'NETWORK_ERROR',
        isNetworkError: true,
        raw: err,
      });
    }
  };

  if (cacheKey) {
    const promise = execute().finally(() => {
      this.inFlightRequests.delete(cacheKey);
    });
    this.inFlightRequests.set(cacheKey, promise);
    return promise;
  }

  return execute();
}

  // Convenience HTTP Verbs
  get(endpoint, options) {
    return this.request(endpoint, { ...options, method: 'GET' });
  }

  post(endpoint, body, options) {
    return this.request(endpoint, {
      ...options,
      method: 'POST',
      body: body instanceof FormData ? body : JSON.stringify(body),
    });
  }

  put(endpoint, body, options) {
    return this.request(endpoint, {
      ...options,
      method: 'PUT',
      body: body instanceof FormData ? body : JSON.stringify(body),
    });
  }

  patch(endpoint, body, options) {
    return this.request(endpoint, {
      ...options,
      method: 'PATCH',
      body: body instanceof FormData ? body : JSON.stringify(body),
    });
  }

  delete(endpoint, options) {
    return this.request(endpoint, { ...options, method: 'DELETE' });
  }

  /**
   * Request helper that returns the raw envelope { success, request_id, message, data, error }
   */
  raw(endpoint, options = {}) {
    return this.request(endpoint, { ...options, rawEnvelope: true });
  }
}

// ============================================================================
// 7. DEFAULT SINGLETON INSTANCE & EXPORTS
// ============================================================================

export const api = new ApiClient();
export const apiRequest = (endpoint, options) => api.request(endpoint, options);

export default api;
