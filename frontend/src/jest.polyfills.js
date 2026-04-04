/**
 * Jest polyfills — loaded via setupFiles (before test framework and before ESM imports).
 * CommonJS only: no import/export statements.
 */
const { TextEncoder, TextDecoder } = require('util');

if (typeof global.TextEncoder === 'undefined') {
  global.TextEncoder = TextEncoder;
}
if (typeof global.TextDecoder === 'undefined') {
  global.TextDecoder = TextDecoder;
}

// BroadcastChannel polyfill for MSW v2 (not in jsdom)
if (typeof global.BroadcastChannel === 'undefined') {
  global.BroadcastChannel = class BroadcastChannel {
    constructor() {}
    postMessage() {}
    addEventListener() {}
    removeEventListener() {}
    close() {}
  };
}
