/**
 * Centralized application constants.
 * All config values sourced here — no hardcoded URLs or ad-hoc config in component files.
 */

/** Backend API base URL. Used by apiFetch and any direct URL construction. */
export const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || "";

/** Default request timeout in milliseconds. */
export const DEFAULT_TIMEOUT_MS = 15000;

/** Max retries for 5xx responses. */
export const MAX_RETRIES = 1;

/** Backoff delay for first retry in milliseconds. */
export const RETRY_BACKOFF_MS = 1000;

/** Application-wide configuration. */
export const APP_CONFIG = {
  appName: "ThookAI",
  supportEmail: "support@thookai.com",
  maxFileUploadBytes: 100 * 1024 * 1024,
};

/** Feature flags — override via REACT_APP_FF_* env vars, default to enabled. */
export const FEATURE_FLAGS = {
  enableVoiceClone: process.env.REACT_APP_FF_VOICE_CLONE !== "false",
  enableVideoGeneration: process.env.REACT_APP_FF_VIDEO_GENERATION !== "false",
  enableObsidianIntegration: process.env.REACT_APP_FF_OBSIDIAN !== "false",
  enableCampaigns: process.env.REACT_APP_FF_CAMPAIGNS !== "false",
  enableTemplateMarketplace: process.env.REACT_APP_FF_TEMPLATES !== "false",
};
