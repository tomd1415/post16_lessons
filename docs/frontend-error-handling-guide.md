# Frontend Error Handling Guide

This guide explains how to use the new centralized error handling system for API calls in the frontend.

## Overview

The `error-handler.js` module provides:
- User-friendly error messages for common HTTP status codes
- Automatic retry logic for network errors and rate limiting
- Toast notifications for errors, warnings, and success messages
- Offline/online status detection
- Request timeout handling

## Quick Start

### 1. Include the error handler in your HTML

Add this before other scripts:

```html
<script src="/core/error-handler.js"></script>
```

### 2. Update your pages

The error handler has already been integrated into:
- All index pages (index.html, teacher.html, admin.html, login.html)
- Activity pages
- Lesson pages

## Usage Examples

### Basic API Call with Error Handling

**Before:**
```javascript
try {
  const res = await fetch("/api/activity/state", { credentials: "same-origin" });
  if (!res.ok) return;
  const data = await res.json();
  // process data
} catch {
  // silent failure
}
```

**After:**
```javascript
const result = await window.errorHandler.apiCall(
  "/api/activity/state",
  { credentials: "same-origin" },
  { operation: "load activity state" }
);

if (result.success) {
  const data = await result.response.json();
  // process data
} else {
  // Error already shown to user via toast
  console.log("Error:", result.error);
}
```

### POST Request with CSRF Token

```javascript
const result = await window.errorHandler.apiCall(
  "/api/activity/state/lesson-1/a1",
  {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrfToken
    },
    body: JSON.stringify({ state: myState })
  },
  {
    operation: "save activity state",
    retry: { maxRetries: 3 }  // Retry up to 3 times
  }
);

if (result.success) {
  window.errorHandler.showToast("Saved successfully!", "success");
}
```

### Manual Error Handling (without automatic toast)

```javascript
const result = await window.errorHandler.apiCall(
  "/api/some/endpoint",
  {},
  {
    operation: "custom operation",
    showToastNotification: false  // Don't show automatic toast
  }
);

if (!result.success) {
  // Handle error manually
  if (result.error.includes("not logged in")) {
    window.location.href = "/login.html";
  }
}
```

### Fetch with Retry (lower level API)

```javascript
try {
  const response = await window.errorHandler.fetchWithRetry(
    "/api/some/endpoint",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    },
    {
      maxRetries: 3,
      retryDelay: 1000,
      timeout: 10000,
      onRetry: (attempt, max, delay) => {
        console.log(`Retry attempt ${attempt}/${max} after ${delay}ms`);
      }
    }
  );

  if (response.ok) {
    const data = await response.json();
    // process data
  }
} catch (error) {
  await window.errorHandler.handleApiError(error, "my operation");
}
```

### Show Toast Notifications

```javascript
// Info (default)
window.errorHandler.showToast("Operation completed");

// Success
window.errorHandler.showToast("Saved successfully!", "success");

// Warning
window.errorHandler.showToast("Some items couldn't be processed", "warning");

// Error
window.errorHandler.showToast("Failed to save. Please try again.", "error");
```

### Check Online Status

```javascript
if (!window.errorHandler.checkOnlineStatus()) {
  // User is offline - skip API call
  return;
}

// Proceed with API call
```

## Error Messages

### HTTP Status Codes

The error handler provides user-friendly messages for common status codes:

- **400**: "Invalid request. Please check your input and try again."
- **401**: "You are not logged in. Please log in to continue."
- **403**: "You don't have permission to perform this action."
- **404**: "The requested resource was not found."
- **429**: "Too many requests. Please wait a moment and try again."
- **500**: "Server error. Please try again later."
- **503**: "Service temporarily unavailable. Please try again later."

### Network Errors

- **Offline**: "You appear to be offline. Your changes will be saved when you reconnect."
- **Timeout**: "The request took too long. Please try again."
- **Generic**: "Network error. Please check your connection and try again."

## Automatic Features

### Retry Logic

The error handler automatically retries requests in these scenarios:

1. **Rate Limiting (429)**: Retries with exponential backoff, respecting `Retry-After` header
2. **Network Errors**: Retries transient network failures
3. **Timeout**: Configurable timeout with automatic abort

Retries are **not** attempted for:
- Authentication errors (401)
- Permission errors (403)
- Bad request errors (400)
- Not found errors (404)

### Offline/Online Detection

The error handler listens for browser online/online events:

- **Going offline**: Shows warning toast
- **Coming back online**: Shows success toast and triggers sync
- **Tab visibility**: Syncs data when user returns to tab

### Rate Limiting

When a 429 (Too Many Requests) response is received:
1. Extracts `Retry-After` header if present
2. Waits for specified duration
3. Automatically retries the request
4. Shows user-friendly message if all retries fail

## Migration Guide

### Step 1: Add Script Tag

Add to the `<head>` or before closing `</body>`:

```html
<script src="/core/error-handler.js"></script>
```

### Step 2: Update Existing Fetch Calls

Find patterns like:

```javascript
// Pattern 1: Basic fetch
const res = await fetch("/api/something");
if (!res.ok) return;

// Pattern 2: Try-catch with silent failure
try {
  const res = await fetch("/api/something");
  // ...
} catch {
  // nothing
}

// Pattern 3: Promise chain with catch
fetch("/api/something")
  .then(r => r.ok ? r.json() : Promise.reject())
  .catch(() => {/* nothing */});
```

Replace with:

```javascript
const result = await window.errorHandler.apiCall(
  "/api/something",
  {}, // options
  { operation: "descriptive operation name" }
);

if (result.success) {
  const data = await result.response.json();
  // process data
}
```

### Step 3: Update Toast Calls

Find:

```javascript
const el = $("#toast");
if (el) {
  el.textContent = "Message";
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 2400);
}
```

Replace with:

```javascript
window.errorHandler.showToast("Message", "success");
```

## Testing

### Simulate Offline

```javascript
// In browser console
window.dispatchEvent(new Event("offline"));
// You should see: "You appear to be offline..."

window.dispatchEvent(new Event("online"));
// You should see: "Connection restored..."
```

### Test Error Messages

```javascript
// Test 401 error
window.errorHandler.handleApiError(
  { status: 401 },
  "test operation"
);

// Test network error
window.errorHandler.handleApiError(
  new TypeError("Failed to fetch"),
  "test operation"
);
```

### Test Retry Logic

```javascript
// This will retry 3 times before failing
const result = await window.errorHandler.fetchWithRetry(
  "/api/nonexistent",
  {},
  {
    maxRetries: 3,
    retryDelay: 500,
    onRetry: (attempt, max) => {
      console.log(`Retry ${attempt}/${max}`);
    }
  }
);
```

## Best Practices

1. **Always provide operation names**: Helps with debugging and logs
   ```javascript
   { operation: "save lesson progress" }
   ```

2. **Use appropriate retry settings**: Don't retry indefinitely
   ```javascript
   { retry: { maxRetries: 2 } }  // 2 retries = 3 total attempts
   ```

3. **Show success feedback**: Users want confirmation
   ```javascript
   if (result.success) {
     window.errorHandler.showToast("Changes saved!", "success");
   }
   ```

4. **Handle auth errors specially**: Redirect to login when needed
   ```javascript
   if (!result.success && result.error.includes("not logged in")) {
     window.location.href = "/login.html";
   }
   ```

5. **Log errors for debugging**: Even though toast shows to user
   ```javascript
   { logToConsole: true }  // This is default
   ```

## Configuration Options

### apiCall Options

```javascript
{
  operation: "operation name",          // Required for good error messages
  showToastNotification: true,          // Show toast to user (default: true)
  logToConsole: true,                   // Log to console (default: true)
  defaultMessage: "Custom error msg",   // Override default message
  retry: {                              // Retry configuration
    maxRetries: 2,                      // Max retry attempts (default: 2)
    retryDelay: 1000,                   // Delay between retries in ms (default: 1000)
    timeout: 30000,                     // Request timeout in ms (default: 30000)
    onRetry: (attempt, max, delay) => {}// Callback on retry
  }
}
```

## Compatibility

- Works with all modern browsers (Chrome, Firefox, Safari, Edge)
- Requires ES6+ support (async/await, arrow functions)
- No external dependencies
- Compatible with existing code (non-breaking)

## Troubleshooting

### Toast not showing

1. Check that `<div id="toast"></div>` exists in HTML
2. Verify error-handler.js is loaded before other scripts
3. Check browser console for errors

### Retries not working

1. Check that error is retryable (not 4xx except 429)
2. Verify `maxRetries` is set correctly
3. Use `onRetry` callback to debug

### Custom error messages not appearing

1. Ensure server returns JSON with `detail` field:
   ```python
   raise HTTPException(status_code=400, detail="Custom message")
   ```

2. The error handler will extract and display the detail

---

**Author:** Claude Code
**Version:** 1.0.0
**Last Updated:** 2025-01-11
