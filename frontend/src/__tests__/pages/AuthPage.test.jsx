/**
 * AuthPage page tests — replaces Wave 0 stubs from Plan 32-00.
 * Covers FEND-01: ARIA error alert, Google auth button, password rules in register mode.
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '@/mocks/server';
import { AuthProvider } from '@/context/AuthContext';
import AuthPage from '@/pages/AuthPage';

jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }) => {
      const { initial, animate, exit, transition, ...rest } = props;
      return <div {...rest}>{children}</div>;
    },
  },
  AnimatePresence: ({ children }) => <>{children}</>,
}));

function renderAuth() {
  return render(
    <MemoryRouter initialEntries={['/auth']}>
      <AuthProvider>
        <AuthPage />
      </AuthProvider>
    </MemoryRouter>
  );
}

describe('AuthPage', () => {
  test('renders_without_crash: page renders login form', () => {
    renderAuth();
    const emailInput = document.querySelector('input[type="email"]');
    const passInput = document.querySelector('input[type="password"]');
    expect(emailInput).toBeTruthy();
    expect(passInput).toBeTruthy();
  });

  test('google_auth_button: Google button is present with data-testid', () => {
    renderAuth();
    expect(screen.getByTestId('google-auth-btn')).toBeInTheDocument();
  });

  test('error_alert_aria: failed login shows error with role=alert', async () => {
    server.use(
      http.post('*/api/auth/login', () =>
        HttpResponse.json({ detail: 'Invalid credentials' }, { status: 401 })
      )
    );

    const user = userEvent.setup();
    renderAuth();

    const emailInput = screen.getByTestId('input-email');
    const passInput = screen.getByTestId('input-password');
    const submitBtn = screen.getByTestId('auth-submit-btn');

    await act(async () => {
      await user.type(emailInput, 'wrong@example.com');
      await user.type(passInput, 'wrongpassword');
      await user.click(submitBtn);
    });

    await waitFor(
      () => {
        const errorEl = screen.getByTestId('auth-error');
        expect(errorEl).toHaveAttribute('role', 'alert');
      },
      { timeout: 3000 }
    );
  });

  test('password_rules_register: rules list appears after password focus in register mode', async () => {
    const user = userEvent.setup();
    renderAuth();

    await act(async () => {
      await user.click(screen.getByTestId('tab-register'));
    });

    const passInput = screen.getByTestId('input-password');
    await act(async () => {
      await user.click(passInput);
      await user.type(passInput, 'Test');
    });

    const rulesList = document.querySelector('[role="list"][aria-label*="Password"]');
    expect(rulesList).toBeInTheDocument();
  });
});
