import { Component } from 'react';

/**
 * Error boundary wrapping page content. Shows a fallback UI on crash.
 */
export class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error('ErrorBoundary caught:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center min-h-[50vh] p-8 text-center">
          <div className="text-5xl mb-4">⚠️</div>
          <h2 className="text-xl font-semibold text-text-primary mb-2">
            Something went wrong
          </h2>
          <p className="text-text-secondary mb-4 text-sm">
            {this.state.error?.message || 'An unexpected error occurred'}
          </p>
          <button
            className="btn-primary"
            onClick={() => this.setState({ hasError: false, error: null })}
          >
            Try Again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
