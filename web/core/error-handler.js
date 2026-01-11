/**
 * Centralized error handling for API requests
 * Provides user-friendly error messages and retry logic
 */

// Error message mapping for common HTTP status codes
const ERROR_MESSAGES = {
  400: "Invalid request. Please check your input and try again.",
  401: "You are not logged in. Please log in to continue.",
  403: "You don't have permission to perform this action.",
  404: "The requested resource was not found.",
  429: "Too many requests. Please wait a moment and try again.",
  500: "Server error. Please try again later.",
  503: "Service temporarily unavailable. Please try again later.",
};

// Network error messages
const NETWORK_ERRORS = {
  offline: "You appear to be offline. Your changes will be saved when you reconnect.",
  timeout: "The request took too long. Please try again.",
  generic: "Network error. Please check your connection and try again.",
};

/**
 * Show a toast notification
 */
function showToast(message, type = "info") {
  const toast = document.getElementById("toast");
  if (!toast) return;

  toast.textContent = message;
  toast.className = `show ${type}`;

  clearTimeout(window.__toastTimer);
  window.__toastTimer = setTimeout(() => {
    toast.classList.remove("show", type);
  }, type === "error" ? 4000 : 2400);
}

/**
 * Get user-friendly error message from response
 */
function getErrorMessage(response, defaultMessage) {
  if (!response) return defaultMessage || "An unexpected error occurred.";

  // Use mapped message for status code
  if (response.status && ERROR_MESSAGES[response.status]) {
    return ERROR_MESSAGES[response.status];
  }

  return defaultMessage || `Request failed with status ${response.status || "unknown"}`;
}

/**
 * Handle API errors with user feedback
 */
async function handleApiError(error, operation = "operation", options = {}) {
  const {
    showToastNotification = true,
    logToConsole = true,
    defaultMessage = null,
  } = options;

  let message;

  // Network errors (offline, timeout, etc.)
  if (error instanceof TypeError && error.message === "Failed to fetch") {
    message = navigator.onLine === false
      ? NETWORK_ERRORS.offline
      : NETWORK_ERRORS.generic;
  }
  // Timeout errors
  else if (error.name === "AbortError" || error.message?.includes("timeout")) {
    message = NETWORK_ERRORS.timeout;
  }
  // HTTP errors with response
  else if (error.status) {
    message = getErrorMessage(error, defaultMessage);

    // Try to extract error detail from response body
    try {
      const data = await error.json?.();
      if (data?.detail) {
        message = data.detail;
      }
    } catch {
      // Ignore JSON parsing errors
    }
  }
  // Generic errors
  else {
    message = defaultMessage || `Failed to ${operation}. Please try again.`;
  }

  if (logToConsole) {
    console.error(`[${operation}] Error:`, error);
  }

  if (showToastNotification) {
    showToast(message, "error");
  }

  return { success: false, error: message };
}

/**
 * Fetch with automatic retry and error handling
 */
async function fetchWithRetry(url, options = {}, retryOptions = {}) {
  const {
    maxRetries = 2,
    retryDelay = 1000,
    timeout = 30000,
    onRetry = null,
  } = retryOptions;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  const fetchOptions = {
    ...options,
    signal: controller.signal,
    credentials: options.credentials || "same-origin",
  };

  let lastError;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const response = await fetch(url, fetchOptions);
      clearTimeout(timeoutId);

      // Handle rate limiting with automatic retry
      if (response.status === 429 && attempt < maxRetries) {
        const retryAfter = response.headers.get("Retry-After");
        const delay = retryAfter ? parseInt(retryAfter) * 1000 : retryDelay * (attempt + 1);

        if (onRetry) {
          onRetry(attempt + 1, maxRetries, delay);
        }

        await new Promise(resolve => setTimeout(resolve, delay));
        continue;
      }

      return response;
    } catch (error) {
      lastError = error;
      clearTimeout(timeoutId);

      // Don't retry on auth errors or client errors
      if (error.status && error.status >= 400 && error.status < 500 && error.status !== 429) {
        throw error;
      }

      // Retry on network errors
      if (attempt < maxRetries) {
        if (onRetry) {
          onRetry(attempt + 1, maxRetries, retryDelay);
        }
        await new Promise(resolve => setTimeout(resolve, retryDelay * (attempt + 1)));
      }
    }
  }

  throw lastError;
}

/**
 * Wrapper for API calls with error handling
 */
async function apiCall(url, options = {}, errorOptions = {}) {
  try {
    const response = await fetchWithRetry(url, options, errorOptions.retry || {});

    if (!response.ok) {
      return await handleApiError(response, errorOptions.operation || "API call", errorOptions);
    }

    return { success: true, response };
  } catch (error) {
    return await handleApiError(error, errorOptions.operation || "API call", errorOptions);
  }
}

/**
 * Check if user is online and show notification if offline
 */
function checkOnlineStatus() {
  if (!navigator.onLine) {
    showToast(NETWORK_ERRORS.offline, "warning");
    return false;
  }
  return true;
}

// Export functions
window.errorHandler = {
  handleApiError,
  fetchWithRetry,
  apiCall,
  showToast,
  checkOnlineStatus,
  ERROR_MESSAGES,
  NETWORK_ERRORS,
};

// Listen for online/offline events
window.addEventListener("online", () => {
  showToast("Connection restored. Syncing your changes...", "success");
  // Trigger sync if available
  if (window.tlacSync && typeof window.tlacSync.flushAll === "function") {
    window.tlacSync.flushAll();
  }
});

window.addEventListener("offline", () => {
  showToast(NETWORK_ERRORS.offline, "warning");
});

// Handle visibility change to sync when tab becomes visible
document.addEventListener("visibilitychange", () => {
  if (!document.hidden && navigator.onLine) {
    // Trigger sync when user returns to tab
    if (window.tlacSync && typeof window.tlacSync.flushAll === "function") {
      setTimeout(() => window.tlacSync.flushAll(), 100);
    }
  }
});
