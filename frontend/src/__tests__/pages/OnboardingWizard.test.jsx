/**
 * OnboardingWizard tests for Phase 27 Plan 02.
 * Tests 5-step stepper, localStorage draft persistence, and back navigation.
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '@/mocks/server';
import { AuthProvider } from '@/context/AuthContext';
import OnboardingWizard from '@/pages/Onboarding/index';

// Mock framer-motion to avoid animation issues in jsdom
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }) => {
      const { initial, animate, exit, transition, ...rest } = props;
      return <div {...rest}>{children}</div>;
    },
  },
  AnimatePresence: ({ children }) => <>{children}</>,
}));

// Mock child components to isolate wizard container behavior
jest.mock('@/pages/Onboarding/PhaseOne', () => ({
  __esModule: true,
  default: ({ onContinue }) => (
    <div data-testid="phase-one-mock">
      <button
        data-testid="phase-one-continue"
        onClick={() => onContinue({ analysis: 'Test analysis', detected_patterns: ['direct', 'concise'] }, ['sample post 1', 'sample post 2'])}
      >
        Continue from Phase One
      </button>
    </div>
  ),
}));

jest.mock('@/pages/Onboarding/PhaseTwo', () => ({
  __esModule: true,
  default: ({ onComplete }) => (
    <div data-testid="phase-two-mock">
      <button
        data-testid="phase-two-complete"
        onClick={() => onComplete({ q1: 'answer1' })}
      >
        Complete Interview
      </button>
    </div>
  ),
}));

jest.mock('@/pages/Onboarding/PhaseThree', () => ({
  __esModule: true,
  default: ({ generating }) => (
    <div data-testid="phase-three-mock">
      {generating ? 'Generating...' : 'Persona ready'}
    </div>
  ),
}));

const mockUser = {
  user_id: 'test-user-123',
  email: 'test@example.com',
  onboarding_completed: false,
};

function TestWrapper({ children }) {
  return (
    <MemoryRouter initialEntries={['/onboarding']}>
      <AuthProvider>
        {children}
      </AuthProvider>
    </MemoryRouter>
  );
}

describe('OnboardingWizard — 5-step stepper', () => {
  beforeEach(() => {
    localStorage.clear();
    // Set up default auth handler
    server.use(
      http.get('*/api/auth/me', () =>
        HttpResponse.json(mockUser)
      )
    );
  });

  afterEach(() => {
    localStorage.clear();
  });

  test('renders onboarding-wizard root element', async () => {
    render(<TestWrapper><OnboardingWizard /></TestWrapper>);
    await waitFor(() => {
      expect(screen.getByTestId('onboarding-wizard')).toBeInTheDocument();
    });
  });

  test('renders 5-step stepper with data-testid=onboarding-stepper', async () => {
    render(<TestWrapper><OnboardingWizard /></TestWrapper>);
    await waitFor(() => {
      expect(screen.getByTestId('onboarding-stepper')).toBeInTheDocument();
    });
  });

  test('renders 5 step dots with correct data-testids', async () => {
    render(<TestWrapper><OnboardingWizard /></TestWrapper>);
    await waitFor(() => {
      for (let i = 1; i <= 5; i++) {
        expect(screen.getByTestId(`step-dot-${i}`)).toBeInTheDocument();
      }
    });
  });

  test('shows Writing Style, Voice Sample, Visual Style as step labels', async () => {
    render(<TestWrapper><OnboardingWizard /></TestWrapper>);
    await waitFor(() => {
      expect(screen.getByText('Writing Style')).toBeInTheDocument();
      expect(screen.getByText('Voice Sample')).toBeInTheDocument();
      expect(screen.getByText('Visual Style')).toBeInTheDocument();
    });
  });

  test('shows Interview and Your Persona as step labels', async () => {
    render(<TestWrapper><OnboardingWizard /></TestWrapper>);
    await waitFor(() => {
      expect(screen.getByText('Interview')).toBeInTheDocument();
      expect(screen.getByText('Your Persona')).toBeInTheDocument();
    });
  });

  test('back button is absent on step 1', async () => {
    render(<TestWrapper><OnboardingWizard /></TestWrapper>);
    await waitFor(() => {
      expect(screen.queryByLabelText('Go back to previous step')).not.toBeInTheDocument();
    });
  });

  test('back button appears on step 2 after advancing from step 1', async () => {
    render(<TestWrapper><OnboardingWizard /></TestWrapper>);
    await waitFor(() => screen.getByTestId('phase-one-continue'));
    await act(async () => {
      await userEvent.click(screen.getByTestId('phase-one-continue'));
    });
    await waitFor(() => {
      expect(screen.getByLabelText('Go back to previous step')).toBeInTheDocument();
    });
  });

  test('draft saved to localStorage with key thook_onboarding_draft_v2 after step 1 completes', async () => {
    render(<TestWrapper><OnboardingWizard /></TestWrapper>);
    await waitFor(() => screen.getByTestId('phase-one-continue'));
    await act(async () => {
      await userEvent.click(screen.getByTestId('phase-one-continue'));
    });
    await waitFor(() => {
      const draft = JSON.parse(localStorage.getItem('thook_onboarding_draft_v2'));
      expect(draft).not.toBeNull();
      expect(draft.step).toBe(2);
    });
  });

  test('draft includes postsAnalysis after step 1 completes', async () => {
    render(<TestWrapper><OnboardingWizard /></TestWrapper>);
    await waitFor(() => screen.getByTestId('phase-one-continue'));
    await act(async () => {
      await userEvent.click(screen.getByTestId('phase-one-continue'));
    });
    await waitFor(() => {
      const draft = JSON.parse(localStorage.getItem('thook_onboarding_draft_v2'));
      expect(draft.postsAnalysis).toBeDefined();
      expect(draft.postsAnalysis.analysis).toBe('Test analysis');
    });
  });

  test('skip button is present and has correct data-testid', async () => {
    render(<TestWrapper><OnboardingWizard /></TestWrapper>);
    await waitFor(() => {
      expect(screen.getByTestId('skip-onboarding-btn')).toBeInTheDocument();
    });
  });
});

describe('OnboardingWizard — draft restore on mount', () => {
  beforeEach(() => {
    localStorage.clear();
    server.use(
      http.get('*/api/auth/me', () =>
        HttpResponse.json(mockUser)
      )
    );
  });

  afterEach(() => {
    localStorage.clear();
  });

  test('restores step from draft on mount if onboarding not completed', async () => {
    // Pre-seed draft for step 2
    localStorage.setItem('thook_onboarding_draft_v2', JSON.stringify({
      step: 2,
      postsAnalysis: { analysis: 'Draft analysis' },
      savedAt: Date.now(),
    }));

    render(<TestWrapper><OnboardingWizard /></TestWrapper>);
    await waitFor(() => {
      // Should be on step 2 — voice recording placeholder
      expect(screen.queryByTestId('phase-one-mock')).not.toBeInTheDocument();
    });
  });
});
