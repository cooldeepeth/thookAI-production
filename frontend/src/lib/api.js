/**
 * Centralized API fetch wrapper.
 *
 * Features:
 *   - Cookie auth: session_token cookie (httpOnly) sent automatically via credentials: 'include'
 *   - CSRF: X-CSRF-Token header injected on POST/PUT/PATCH/DELETE from the csrf_token cookie
 *   - Timeout: 15-second AbortController timeout (override via options.timeout)
 *   - Retry: 1 automatic retry after 1s backoff on any 5xx response
 *   - Global error handling:
 *       401 → redirect to /auth?expired=1
 *       403 → permission-denied toast
 *       5xx (after retry) → server-error toast
 *
 * New code should use apiFetch() instead of raw fetch().
 * Existing pages will be migrated progressively (Phase 22).
 */
import {
  API_BASE_URL,
  DEFAULT_TIMEOUT_MS,
  MAX_RETRIES,
  RETRY_BACKOFF_MS,
} from "./constants";
import { toast } from "@/hooks/use-toast";

/**
 * Read the CSRF token from the JS-readable csrf_token cookie set by the backend.
 * @returns {string|null}
 */
function getCsrfToken() {
  const match = document.cookie.match(/(?:^|; )csrf_token=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

/**
 * Sleep for the given number of milliseconds.
 * @param {number} ms
 * @returns {Promise<void>}
 */
function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Perform a single fetch attempt with an AbortController timeout.
 *
 * @param {string} url - Full URL to fetch
 * @param {RequestInit & { timeout?: number }} fetchOptions - Options forwarded to fetch
 * @returns {Promise<Response>}
 */
async function fetchWithTimeout(url, fetchOptions) {
  const { timeout, signal: callerSignal, ...restOptions } = fetchOptions;
  const timeoutMs = timeout !== undefined ? timeout : DEFAULT_TIMEOUT_MS;

  // If the caller provided their own signal, respect it without adding a timeout layer
  if (callerSignal) {
    return fetch(url, { ...restOptions, signal: callerSignal });
  }

  const controller = new AbortController();
  const timerId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(url, { ...restOptions, signal: controller.signal });
  } catch (err) {
    if (err.name === "AbortError") {
      toast({
        title: "Request timed out",
        description: "Please try again.",
        variant: "destructive",
      });
    }
    throw err;
  } finally {
    clearTimeout(timerId);
  }
}

/**
 * Centralized fetch wrapper for all API calls.
 *
 * @param {string} path - API path starting with /api/...
 * @param {RequestInit & { timeout?: number }} options - Standard fetch options plus optional timeout override
 * @returns {Promise<Response>} Raw Response object (backward compatible — callers still call .json())
 */
export async function apiFetch(path, options = {}) {
  const skipAuthRedirect = options._skipAuthRedirect || false;
  const headers = {
    ...options.headers,
  };

  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  // Inject CSRF token header for state-changing requests
  const method = (options.method || "GET").toUpperCase();
  if (method !== "GET" && method !== "HEAD") {
    const csrfToken = getCsrfToken();
    if (csrfToken) {
      headers["X-CSRF-Token"] = csrfToken;
    }
  }

  const fetchOptions = {
    ...options,
    headers,
    credentials: "include",
  };

  const url = `${API_BASE_URL}${path}`;
  let res;
  let attempt = 0;

  // Retry loop: attempt up to MAX_RETRIES + 1 total tries
  while (attempt <= MAX_RETRIES) {
    if (attempt > 0) {
      await sleep(RETRY_BACKOFF_MS);
    }

    res = await fetchWithTimeout(url, fetchOptions);

    if (res.status < 500 || attempt >= MAX_RETRIES) {
      break;
    }

    attempt += 1;
  }

  // Global error handling — skip redirect for auth-check calls (e.g. AuthContext mount)
  if (res.status === 401 && !skipAuthRedirect) {
    window.location.href = "/auth?expired=1";
    throw new Error("Session expired");
  }

  if (res.status === 403) {
    toast({
      title: "Permission denied",
      description: "You don't have access to this resource.",
      variant: "destructive",
    });
    throw new Error("Permission denied");
  }

  if (res.status >= 500) {
    toast({
      title: "Server error",
      description: "Something went wrong. Please try again later.",
      variant: "destructive",
    });
    // Return response so caller can inspect if needed
    return res;
  }

  return res;
}
