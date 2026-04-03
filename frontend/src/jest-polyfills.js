/**
 * Jest polyfills for MSW v2 in jsdom environment (CRA / React 18).
 *
 * Runs via jest.configure.setupFiles BEFORE test framework and module
 * evaluation — this ensures all Web APIs are available when msw/node loads.
 *
 * Why: jsdom does not include Web Streams API or TextEncoder.
 * MSW v2 uses them at module-load time via @mswjs/interceptors.
 */

// Set REACT_APP_BACKEND_URL to a valid base URL so apiFetch constructs
// valid absolute URLs (required for MSW v2 fetch interception in jsdom).
// jsdom has no base URL so relative paths like /api/... fail URL parsing.
process.env.REACT_APP_BACKEND_URL = 'http://localhost';

// TextEncoder / TextDecoder (Node.js util)
const { TextEncoder, TextDecoder } = require('util');
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;

// Web Streams API — ReadableStream, WritableStream, TransformStream
// Required by @mswjs/interceptors/fetch/brotli-decompress
const streamWeb = require('stream/web');
if (typeof global.ReadableStream === 'undefined') {
  global.ReadableStream = streamWeb.ReadableStream;
}
if (typeof global.WritableStream === 'undefined') {
  global.WritableStream = streamWeb.WritableStream;
}
if (typeof global.TransformStream === 'undefined') {
  global.TransformStream = streamWeb.TransformStream;
}

// BroadcastChannel is used by MSW v2 internals — not present in jsdom
if (typeof global.BroadcastChannel === 'undefined') {
  global.BroadcastChannel = class BroadcastChannel {
    constructor() {}
    postMessage() {}
    addEventListener() {}
    removeEventListener() {}
    close() {}
  };
}
