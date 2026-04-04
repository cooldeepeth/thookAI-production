/**
 * Centralized application constants.
 * All config values sourced here — no hardcoded URLs or ad-hoc config in component files.
 */

/** Backend API base URL. Used by apiFetch and any direct URL construction. */
export const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || '';

/** Default request timeout in milliseconds. */
export const DEFAULT_TIMEOUT_MS = 15000;

/** Max retries for 5xx responses. */
export const MAX_RETRIES = 1;

/** Backoff delay for first retry in milliseconds. */
export const RETRY_BACKOFF_MS = 1000;

/** Application-wide configuration. */
export const APP_CONFIG = {
  appName: 'ThookAI',
  supportEmail: 'support@thookai.com',
  maxFileUploadBytes: 100 * 1024 * 1024,
};

/** Feature flags — toggle features without code changes. */
export const FEATURE_FLAGS = {
  enableVoiceClone: true,
  enableVideoGeneration: true,
  enableObsidianIntegration: true,
  enableCampaigns: true,
  enableTemplateMarketplace: true,
};
