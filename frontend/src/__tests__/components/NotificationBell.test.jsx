/**
 * NotificationBell component tests.
 * Tests rendered output and interactions — no snapshot assertions.
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '@/mocks/server';
import { AuthProvider } from '@/context/AuthContext';
import NotificationBell from '@/components/NotificationBell';

function TestWrapper({ children }) {
  return (
    <MemoryRouter>
      <AuthProvider>{children}</AuthProvider>
    </MemoryRouter>
  );
}

function renderBell() {
  return render(
    <TestWrapper>
      <NotificationBell />
    </TestWrapper>
  );
}

describe('NotificationBell', () => {
  let mockEventSource;

  beforeEach(() => {
    // Set up EventSource mock before each test so the SSE connection is controlled
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
    // Clean up EventSource mock
    delete global.EventSource;
  });

  test('renders_bell_button: bell button with data-testid is in the document', async () => {
    renderBell();
    expect(screen.getByTestId('notifications-btn')).toBeInTheDocument();
  });

  test('no_badge_when_zero: when unreadCount=0, no numeric badge is visible', async () => {
    // Default handler returns unread_count: 0
    renderBell();
    await waitFor(() => {
      expect(screen.getByTestId('notifications-btn')).toBeInTheDocument();
    });
    // No badge number should appear
    expect(screen.queryByText('3')).not.toBeInTheDocument();
    expect(screen.queryByText('1')).not.toBeInTheDocument();
  });

  test('badge_shows_count: when /api/notifications/count returns unread_count=3, badge shows "3"', async () => {
    server.use(
      http.get('*/api/notifications/count', () =>
        HttpResponse.json({ unread_count: 3 })
      )
    );
    renderBell();
    await waitFor(() => {
      expect(screen.getByText('3')).toBeInTheDocument();
    });
  });

  test('dropdown_opens_on_click: clicking notifications-btn renders the notification dropdown', async () => {
    const user = userEvent.setup();
    renderBell();
    const btn = screen.getByTestId('notifications-btn');
    await act(async () => {
      await user.click(btn);
    });
    // When dropdown opens, Notifications heading appears
    expect(screen.getByText('Notifications')).toBeInTheDocument();
  });

  test('dropdown_closes_on_second_click: clicking notifications-btn again closes the dropdown', async () => {
    const user = userEvent.setup();
    renderBell();
    const btn = screen.getByTestId('notifications-btn');
    // Open
    await act(async () => {
      await user.click(btn);
    });
    expect(screen.getByText('Notifications')).toBeInTheDocument();
    // Close
    await act(async () => {
      await user.click(btn);
    });
    expect(screen.queryByText('Notifications')).not.toBeInTheDocument();
  });

  test('empty_state_shown: when notifications=[], dropdown shows "No notifications" message', async () => {
    // Default handler returns empty notifications array
    const user = userEvent.setup();
    renderBell();
    const btn = screen.getByTestId('notifications-btn');
    await act(async () => {
      await user.click(btn);
    });
    await waitFor(() => {
      expect(screen.getByText('No notifications yet')).toBeInTheDocument();
    });
  });

  test('notification_item_rendered: when API returns notification, title text appears in dropdown', async () => {
    server.use(
      http.get('*/api/notifications', () =>
        HttpResponse.json({
          notifications: [
            {
              notification_id: 'n1',
              title: 'Job completed',
              body: 'Your content has been generated',
              type: 'job_completed',
              read: false,
              created_at: new Date().toISOString(),
            },
          ],
        })
      )
    );
    const user = userEvent.setup();
    renderBell();
    const btn = screen.getByTestId('notifications-btn');
    await act(async () => {
      await user.click(btn);
    });
    await waitFor(() => {
      expect(screen.getByText('Job completed')).toBeInTheDocument();
    });
  });

  test('mark_all_read_button: "Mark all read" button is visible when there are unread notifications', async () => {
    server.use(
      http.get('*/api/notifications/count', () =>
        HttpResponse.json({ unread_count: 2 })
      ),
      http.get('*/api/notifications', () =>
        HttpResponse.json({
          notifications: [
            {
              notification_id: 'n2',
              title: 'New update',
              body: 'Something happened',
              type: 'system',
              read: false,
              created_at: new Date().toISOString(),
            },
          ],
        })
      )
    );
    const user = userEvent.setup();
    renderBell();
    const btn = screen.getByTestId('notifications-btn');
    await act(async () => {
      await user.click(btn);
    });
    await waitFor(() => {
      expect(screen.getByText('Mark all read')).toBeInTheDocument();
    });
  });
});
