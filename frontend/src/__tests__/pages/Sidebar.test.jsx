/**
 * Sidebar component tests.
 * Tests rendered output and interactions — no snapshot assertions.
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '@/mocks/server';
import { AuthProvider } from '@/context/AuthContext';
import Sidebar from '@/pages/Dashboard/Sidebar';

function TestWrapper({ children }) {
  return (
    <MemoryRouter>
      <AuthProvider>{children}</AuthProvider>
    </MemoryRouter>
  );
}

function renderSidebar(props = {}) {
  const defaults = { isOpen: false, onClose: jest.fn() };
  return render(
    <TestWrapper>
      <Sidebar {...defaults} {...props} />
    </TestWrapper>
  );
}

describe('Sidebar', () => {
  test('renders_sidebar: element with data-testid="sidebar" is in document', async () => {
    renderSidebar();
    expect(screen.getByTestId('sidebar')).toBeInTheDocument();
  });

  test('nav_links_rendered: at least 5 nav link labels are visible', async () => {
    renderSidebar();
    // These nav labels are always in the DOM (sidebar is always in DOM, just translated off-screen on mobile)
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Strategy')).toBeInTheDocument();
    expect(screen.getByText('Content Studio')).toBeInTheDocument();
    expect(screen.getByText('Analytics')).toBeInTheDocument();
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  test('credits_displayed: after /api/billing/credits resolves with credits=80, "80" appears in sidebar', async () => {
    // Default handler returns credits: 80
    renderSidebar();
    await waitFor(() => {
      // The sidebar shows credits value; default handler returns 80
      expect(screen.getByText('80')).toBeInTheDocument();
    });
  });

  test('logout_button_present: logout button is present in the sidebar', async () => {
    renderSidebar();
    // AuthProvider will populate user from /api/auth/me (returns test@example.com)
    await waitFor(() => {
      // Logout button uses title="Logout"
      expect(screen.getByTestId('logout-btn')).toBeInTheDocument();
    });
  });

  test('mobile_backdrop: when isOpen=true, data-testid="sidebar-backdrop" is in document', async () => {
    renderSidebar({ isOpen: true });
    expect(screen.getByTestId('sidebar-backdrop')).toBeInTheDocument();
  });

  test('no_backdrop_when_closed: when isOpen=false, data-testid="sidebar-backdrop" is NOT in document', async () => {
    renderSidebar({ isOpen: false });
    expect(screen.queryByTestId('sidebar-backdrop')).not.toBeInTheDocument();
  });
});
