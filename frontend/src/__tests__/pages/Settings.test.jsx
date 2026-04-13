/**
 * Settings page tests — replaces Wave 0 stubs from Plan 32-00.
 * Covers FEND-04/FEND-05/FEND-07: 4-tab layout, billing skeleton, billing error+retry, role=tab keyboard a11y.
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '@/mocks/server';
import { AuthProvider } from '@/context/AuthContext';
import Settings from '@/pages/Dashboard/Settings';

jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }) => {
      const { initial, animate, exit, transition, ...rest } = props;
      return <div {...rest}>{children}</div>;
    },
  },
  AnimatePresence: ({ children }) => <>{children}</>,
}));

function renderSettings() {
  return render(
    <MemoryRouter initialEntries={['/dashboard/settings']}>
      <AuthProvider>
        <Settings />
      </AuthProvider>
    </MemoryRouter>
  );
}

describe('Settings', () => {
  test('four_tabs_present: all four tab triggers render', async () => {
    renderSettings();
    await waitFor(
      () => {
        expect(screen.getByTestId('tab-billing')).toBeInTheDocument();
        expect(screen.getByTestId('tab-connections')).toBeInTheDocument();
        expect(screen.getByTestId('tab-profile')).toBeInTheDocument();
        expect(screen.getByTestId('tab-notifications')).toBeInTheDocument();
      },
      { timeout: 3000 }
    );
  });

  test('billing_skeleton_during_load: skeleton renders while billing fetches', async () => {
    server.use(
      http.get('*/api/billing/subscription', async () => {
        await new Promise((r) => setTimeout(r, 200));
        return HttpResponse.json({ tier: 'free' });
      })
    );
    renderSettings();
    const skeleton =
      screen.queryByTestId('billing-skeleton') ||
      document.querySelector('.animate-pulse');
    expect(skeleton).toBeTruthy();
  });

  test('billing_error_retry: error state with retry button renders on fetch failure', async () => {
    server.use(
      http.get('*/api/billing/subscription', () => HttpResponse.error()),
      http.get('*/api/billing/credits', () => HttpResponse.error()),
      http.get('*/api/billing/subscription/tiers', () => HttpResponse.error()),
      http.get('*/api/billing/subscription/limits', () => HttpResponse.error()),
      http.get('*/api/billing/config', () => HttpResponse.error()),
      http.get('*/api/billing/credits/costs', () => HttpResponse.error())
    );
    renderSettings();
    await waitFor(
      () => {
        expect(screen.getByTestId('billing-error')).toBeInTheDocument();
        expect(screen.getByTestId('retry-billing-btn')).toBeInTheDocument();
      },
      { timeout: 3000 }
    );
    expect(screen.getByTestId('billing-error')).toHaveAttribute('role', 'alert');
  });

  test('tabs_keyboard_accessible: at least 4 elements have role=tab', async () => {
    renderSettings();
    await waitFor(
      () => {
        const tabs = screen.getAllByRole('tab');
        expect(tabs.length).toBeGreaterThanOrEqual(4);
      },
      { timeout: 3000 }
    );
  });
});
