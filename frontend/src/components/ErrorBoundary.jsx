import React from 'react';
import { AlertTriangle } from 'lucide-react';

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch() {
    // Sentry integration tracked separately; no console output in production
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          className="min-h-screen bg-[#050505] flex items-center justify-center"
          data-testid="error-boundary-screen"
        >
          <div className="text-center p-8 max-w-md">
            <AlertTriangle size={32} className="text-red-400 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-white mb-2">Something went wrong</h2>
            <p className="text-zinc-400 mb-6">
              An unexpected error occurred. Please try refreshing the page.
            </p>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="px-6 py-2 bg-lime text-black font-medium rounded-lg hover:bg-lime/90 transition-colors focus-ring"
            >
              Refresh Page
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
