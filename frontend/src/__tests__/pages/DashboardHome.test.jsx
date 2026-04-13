/**
 * DashboardHome page tests — replaces Wave 0 stubs from Plan 32-00.
 * Covers FEND-02/FEND-05: skeleton, error+retry, empty-content CTA.
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '@/mocks/server';
import { AuthProvider } from '@/context/AuthContext';
import DashboardHome from '@/pages/Dashboard/DashboardHome';

jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }) => {
      const { initial, animate, exit, transition, ...rest } = props;
      return <div {...rest}>{children}</div>;
    },
    button: ({ children, ...props }) => {
      const { initial, animate, exit, transition, ...rest } = props;
      return <button {...rest}>{children}</button>;
    },
  },
  AnimatePresence: ({ children }) => <>{children}</>,
}));

jest.mock('@/pages/Dashboard/DailyBrief', () => ({
  __esModule: true,
  default: () => null,
}));

function renderDashboard() {
  return render(
    <MemoryRouter initialEntries={['/dashboard']}>
      <AuthProvider>
        <DashboardHome />
      </AuthProvider>
    </MemoryRouter>
  );
}

describe('DashboardHome', () => {
  test('skeleton_during_load: skeleton renders during stats fetch', async () => {
    server.use(
      http.get('*/api/dashboard/stats', async () => {
        await new Promise((r) => setTimeout(r, 200));
        return HttpResponse.json({});
      })
    );
    renderDashboard();
    const skeleton = document.querySelector('.animate-pulse');
    expect(skeleton).toBeTruthy();
  });

  test('error_state_with_retry: retry button visible when stats fetch fails', async () => {
    server.use(
      http.get('*/api/dashboard/stats', () =>
        HttpResponse.json({ error: 'Server error' }, { status: 500 })
      )
    );
    renderDashboard();
    await waitFor(
      () => {
        expect(screen.getByTestId('retry-stats-btn')).toBeInTheDocument();
      },
      { timeout: 3000 }
    );
    expect(screen.getByTestId('stats-error')).toHaveAttribute('role', 'alert');
  });

  test('empty_content_cta: CTA visible when no content jobs', async () => {
    server.use(
      http.get('*/api/auth/me', () =>
        HttpResponse.json({
          user_id: 'u1',
          email: 'test@example.com',
          name: 'Test User',
          subscription_tier: 'pro',
          credits: 100,
          onboarding_completed: true,
        })
      ),
      http.get('*/api/dashboard/stats', () =>
        HttpResponse.json({
          credits: 100,
          posts_created: 0,
          platforms_count: 0,
          persona_score: null,
          recent_jobs: [],
          learning_signals_count: 0,
        })
      )
    );
    renderDashboard();
    await waitFor(
      () => {
        expect(screen.getByTestId('empty-content-cta')).toBeInTheDocument();
      },
      { timeout: 3000 }
    );
  });
});
