// craco.config.js
const path = require("path");
require("dotenv").config();

// Environment variable overrides
const config = {
  enableHealthCheck: process.env.ENABLE_HEALTH_CHECK === "true",
};

// Conditionally load health check modules only if enabled
let WebpackHealthPlugin;
let setupHealthEndpoints;
let healthPluginInstance;

if (config.enableHealthCheck) {
  WebpackHealthPlugin = require("./plugins/health-check/webpack-health-plugin");
  setupHealthEndpoints = require("./plugins/health-check/health-endpoints");
  healthPluginInstance = new WebpackHealthPlugin();
}

// Babel configuration for Jest to handle modern JS in node_modules
// @babel/plugin-transform-class-static-block: handles ES2022 static {} blocks
// used in @mswjs/interceptors CJS bundles
const babelConfig = {
  babel: {
    plugins: ['@babel/plugin-transform-class-static-block'],
  },
};

let webpackConfig = {
  webpack: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
    configure: (webpackConfig) => {

      // Add ignored patterns to reduce watched directories
        webpackConfig.watchOptions = {
          ...webpackConfig.watchOptions,
          ignored: [
            '**/node_modules/**',
            '**/.git/**',
            '**/build/**',
            '**/dist/**',
            '**/coverage/**',
            '**/public/**',
        ],
      };

      // Add health check plugin to webpack if enabled
      if (config.enableHealthCheck && healthPluginInstance) {
        webpackConfig.plugins.push(healthPluginInstance);
      }
      // CI=true treats all webpack warnings as errors; exhaustive-deps stays "warn" in ESLint
      const prev = webpackConfig.ignoreWarnings;
      webpackConfig.ignoreWarnings = [
        ...(Array.isArray(prev) ? prev : prev ? [prev] : []),
        /react-hooks\/exhaustive-deps/,
      ];
      return webpackConfig;
    },
  },
};

webpackConfig.devServer = (devServerConfig) => {
  // Add health check endpoints if enabled
  if (config.enableHealthCheck && setupHealthEndpoints && healthPluginInstance) {
    const originalSetupMiddlewares = devServerConfig.setupMiddlewares;

    devServerConfig.setupMiddlewares = (middlewares, devServer) => {
      // Call original setup if exists
      if (originalSetupMiddlewares) {
        middlewares = originalSetupMiddlewares(middlewares, devServer);
      }

      // Setup health endpoints
      setupHealthEndpoints(devServer, healthPluginInstance);

      return middlewares;
    };
  }

  return devServerConfig;
};

webpackConfig.jest = {
  configure: (jestConfig) => {
    // @/ alias: map to src/ so jest resolves the same as webpack.
    // Custom entries must come AFTER spreading existing CRA-generated mappers
    // so they take precedence over any conflicting CRA patterns.
    jestConfig.moduleNameMapper = {
      // CRA-generated mappers first (CSS modules, SVG stubs, etc.)
      ...jestConfig.moduleNameMapper,
      // Custom overrides — these WIN over the CRA mappers above
      '^@/(.*)$': '<rootDir>/src/$1',
      // Force MSW to use its pre-compiled CJS bundle rather than the MJS/TS
      // sources. Jest resolves the 'module' condition which points to .mjs.
      // The CJS bundles work correctly without Babel transformation.
      '^msw/node$': '<rootDir>/node_modules/msw/lib/node/index.js',
      '^msw$': '<rootDir>/node_modules/msw/lib/core/index.js',
      // react-router-dom v7 has a broken "main" field (./dist/main.js does not exist).
      // Jest 27 resolver falls back to main; point it to the real CJS entry.
      '^react-router-dom$': '<rootDir>/node_modules/react-router-dom/dist/index.js',
      // react-router v7 uses package exports for subpath './dom'.
      // Jest 27 does not support conditional package exports — map explicitly.
      '^react-router/dom$': '<rootDir>/node_modules/react-router/dist/development/dom-export.js',
      '^react-router$': '<rootDir>/node_modules/react-router/dist/development/index.js',
    };

    // Polyfills must run before Jest loads any test modules (including MSW).
    // setupFiles run before setupFilesAfterEnv, so TextEncoder is
    // available when msw/node is first imported.
    jestConfig.setupFiles = [
      '<rootDir>/src/jest-polyfills.js',
      ...(jestConfig.setupFiles || []),
    ];

    // MSW v2 dependencies use a mix of:
    //   - ESM syntax (until-async: export { until })
    //   - ES2022 static class blocks (@mswjs/interceptors: class Foo { static {} })
    //
    // Strategy:
    //   1. Transform @mswjs/* and until-async with Babel (so ESM is converted)
    //   2. craco babel config adds @babel/plugin-transform-class-static-block
    //      so the static {} syntax is handled
    //   3. moduleNameMapper routes msw/node to the CJS lib bundle
    jestConfig.transformIgnorePatterns = [
      // Transform everything in node_modules EXCEPT @mswjs and until-async
      '/node_modules/(?!(@mswjs|until-async)/).*',
      '^.+\\.module\\.(css|sass|scss)$',
    ];

    return jestConfig;
  },
};

module.exports = { ...babelConfig, ...webpackConfig };
