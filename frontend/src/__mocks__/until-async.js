/**
 * CJS shim for until-async (ESM-only package).
 * Used by MSW v2's handleRequest internals.
 * Jest cannot load ESM packages without transformation — this shim
 * provides the same API in CommonJS format.
 */

async function until(callback) {
  try {
    const data = await callback().catch((error) => {
      throw error;
    });
    return [null, data];
  } catch (error) {
    return [error, null];
  }
}

module.exports = { until };
