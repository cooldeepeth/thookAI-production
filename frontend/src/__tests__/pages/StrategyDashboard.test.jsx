/**
 * StrategyDashboard page tests.
 * Tests rendered output and interactions — no snapshot assertions.
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '@/mocks/server';
import { AuthProvider } from '@/context/AuthContext';
import StrategyDashboard from '@/pages/Dashboard/StrategyDashboard';

// Mock framer-motion to avoid animation issues in jsdom
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }) => {
      const { initial, animate, exit, transition, ...rest } = props;
      return <div {...rest}>{children}</div>;
    },
    span: ({ children, ...props }) => {
      const { initial, animate, exit, transition, ...rest } = props;
      return <span {...rest}>{children}</span>;
    },
  },
  AnimatePresence: ({ children }) => <>{children}</>,
}));

function TestWrapper({ children }) {
  return (
    <MemoryRouter>
      <AuthProvider>{children}</AuthProvider>
    </MemoryRouter>
  );
}

function renderDashboard() {
  return render(
    <TestWrapper>
      <StrategyDashboard />
    </TestWrapper>
  );
}

const mockCard1 = {
  recommendation_id: 'rec-1',
  platform: 'linkedin',
  topic: 'AI in product development',
  why_now: 'This is trending right now',
  signal_source: 'performance',
  hook_options: ['Hook 1', 'Hook 2'],
  status: 'pending_approval',
  created_at: new Date().toISOString(),
};

const mockCard2 = {
  recommendation_id: 'rec-2',
  platform: 'x',
  topic: 'Remote work productivity',
  why_now: 'Many people are discussing this',
  signal_source: 'trending',
  hook_options: ['Hook A'],
  status: 'pending_approval',
  created_at: new Date().toISOString(),
};

describe('StrategyDashboard', () => {
  let mockEventSource;

  beforeEach(() => {
    // EventSource mock needed because StrategyDashboard uses useNotifications
    mockEventSource = {
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      close: jest.fn(),
      onmessage: null,
      onerror: null,
    };
    global.EventSource = jest.fn(() => mockEventSource);
  });

  afterEach(() => {
    delete global.EventSource;
  });

  test('renders_without_crash: component mounts without throwing', async () => {
    renderDashboard();
    // If it renders, the page heading should be present
    expect(screen.getByText('Strategy Feed')).toBeInTheDocument();
  });

  test('loading_skeleton_shown: while API is in-flight, skeleton with animate-pulse is rendered', () => {
    // Don't await — check immediately for skeleton
    renderDashboard();
    // Skeleton cards have animate-pulse class
    const skeletons = document.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  test('empty_state_shown: when activeCards=[], empty state message is shown', async () => {
    // Default handler returns cards: [] so empty state should appear after loading
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByText('No recommendations right now.')).toBeInTheDocument();
    });
  });

  test('cards_rendered: when API returns 2 active cards, both topics are rendered', async () => {
    server.use(
      http.get('*/api/strategy', ({ request }) => {
        const url = new URL(request.url);
        if (url.searchParams.get('status') === 'pending_approval') {
          return HttpResponse.json({ cards: [mockCard1, mockCard2] });
        }
        return HttpResponse.json({ cards: [] });
      })
    );
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByText('AI in product development')).toBeInTheDocument();
    });
    expect(screen.getByText('Remote work productivity')).toBeInTheDocument();
  });

  test('card_shows_platform: card with platform=linkedin shows LinkedIn label', async () => {
    server.use(
      http.get('*/api/strategy', ({ request }) => {
        const url = new URL(request.url);
        if (url.searchParams.get('status') === 'pending_approval') {
          return HttpResponse.json({ cards: [mockCard1] });
        }
        return HttpResponse.json({ cards: [] });
      })
    );
    renderDashboard();
    await waitFor(() => {
      // Platform badge shows "Linkedin" (capitalized first letter by the component)
      // Component: card.platform.charAt(0).toUpperCase() + card.platform.slice(1)
      expect(screen.getByText('Linkedin')).toBeInTheDocument();
    });
  });

  test('approve_button_present: active card has an Approve button', async () => {
    server.use(
      http.get('*/api/strategy', ({ request }) => {
        const url = new URL(request.url);
        if (url.searchParams.get('status') === 'pending_approval') {
          return HttpResponse.json({ cards: [mockCard1] });
        }
        return HttpResponse.json({ cards: [] });
      })
    );
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /approve/i })).toBeInTheDocument();
    });
  });

  test('dismiss_button_present: active card has a Dismiss button', async () => {
    server.use(
      http.get('*/api/strategy', ({ request }) => {
        const url = new URL(request.url);
        if (url.searchParams.get('status') === 'pending_approval') {
          return HttpResponse.json({ cards: [mockCard1] });
        }
        return HttpResponse.json({ cards: [] });
      })
    );
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /dismiss/i })).toBeInTheDocument();
    });
  });

  test('approve_calls_api: clicking approve on a card triggers POST /api/strategy/:id/approve', async () => {
    let approveCalled = false;

    server.use(
      http.get('*/api/strategy', ({ request }) => {
        const url = new URL(request.url);
        if (url.searchParams.get('status') === 'pending_approval') {
          return HttpResponse.json({ cards: [mockCard1] });
        }
        return HttpResponse.json({ cards: [] });
      }),
      http.post('*/api/strategy/:id/approve', () => {
        approveCalled = true;
        // Return a payload that would normally trigger navigation but missing required fields
        // so navigation won't fire (we just want to verify the API call)
        return HttpResponse.json({ generate_payload: {} });
      }),
      http.post('*/api/content/create', () =>
        HttpResponse.json({ job_id: 'job-999' })
      )
    );

    const user = userEvent.setup();
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /approve/i })).toBeInTheDocument();
    });

    await act(async () => {
      await user.click(screen.getByRole('button', { name: /approve/i }));
    });

    await waitFor(() => {
      expect(approveCalled).toBe(true);
    });
  });
});
