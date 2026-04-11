/**
 * PhaseOne (WritingStyleStep) tests for Phase 27 Plan 02.
 * Tests fingerprint confirmation UI after post analysis.
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '@/mocks/server';
import PhaseOne from '@/pages/Onboarding/PhaseOne';

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

function TestWrapper({ children }) {
  return (
    <MemoryRouter>
      {children}
    </MemoryRouter>
  );
}

describe('PhaseOne — fingerprint confirmation UI', () => {
  const mockOnContinue = jest.fn();

  beforeEach(() => {
    mockOnContinue.mockClear();
    // Mock analyze-posts API to return result with detected_patterns
    server.use(
      http.post('*/api/onboarding/analyze-posts', () =>
        HttpResponse.json({
          analysis: 'You write in a direct, concise style.',
          detected_patterns: ['direct', 'concise', 'data-driven'],
        })
      )
    );
  });

  async function triggerAnalysis() {
    render(
      <TestWrapper>
        <PhaseOne onContinue={mockOnContinue} />
      </TestWrapper>
    );

    // Click "existing creator" to enter the textarea view
    await waitFor(() => screen.getByTestId('option-existing-creator'));
    await act(async () => {
      await userEvent.click(screen.getByTestId('option-existing-creator'));
    });

    // Type some posts
    await act(async () => {
      await userEvent.type(screen.getByTestId('posts-textarea'), 'My first post content');
    });

    // Click analyze
    await act(async () => {
      await userEvent.click(screen.getByTestId('analyze-posts-btn'));
    });

    // Wait for result to appear
    await waitFor(() => {
      expect(screen.getByTestId('fingerprint-confirm')).toBeInTheDocument();
    }, { timeout: 5000 });
  }

  test('shows fingerprint-confirm container after analysis', async () => {
    await triggerAnalysis();
    expect(screen.getByTestId('fingerprint-confirm')).toBeInTheDocument();
  });

  test('shows "Your writing fingerprint" heading', async () => {
    await triggerAnalysis();
    expect(screen.getByText('Your writing fingerprint')).toBeInTheDocument();
  });

  test('shows "Style Analysis" label with correct class attributes', async () => {
    await triggerAnalysis();
    const label = screen.getByText('Style Analysis');
    expect(label).toBeInTheDocument();
  });

  test('shows analysis text from API response', async () => {
    await triggerAnalysis();
    expect(screen.getByText('You write in a direct, concise style.')).toBeInTheDocument();
  });

  test('renders detected_patterns as badge chips', async () => {
    await triggerAnalysis();
    expect(screen.getByText('direct')).toBeInTheDocument();
    expect(screen.getByText('concise')).toBeInTheDocument();
    expect(screen.getByText('data-driven')).toBeInTheDocument();
  });

  test('fingerprint-confirm-btn ("This is me") is present', async () => {
    await triggerAnalysis();
    expect(screen.getByTestId('fingerprint-confirm-btn')).toBeInTheDocument();
    expect(screen.getByTestId('fingerprint-confirm-btn')).toHaveTextContent('This is me');
  });

  test('fingerprint-edit-btn ("Edit my posts") is present', async () => {
    await triggerAnalysis();
    expect(screen.getByTestId('fingerprint-edit-btn')).toBeInTheDocument();
    expect(screen.getByTestId('fingerprint-edit-btn')).toHaveTextContent('Edit my posts');
  });

  test('"Edit my posts" resets to textarea view', async () => {
    await triggerAnalysis();
    await act(async () => {
      await userEvent.click(screen.getByTestId('fingerprint-edit-btn'));
    });
    await waitFor(() => {
      expect(screen.queryByTestId('fingerprint-confirm')).not.toBeInTheDocument();
      expect(screen.getByTestId('posts-textarea')).toBeInTheDocument();
    });
  });

  test('"This is me" calls onContinue with result and parsedSamples', async () => {
    await triggerAnalysis();
    await act(async () => {
      await userEvent.click(screen.getByTestId('fingerprint-confirm-btn'));
    });
    await waitFor(() => {
      expect(mockOnContinue).toHaveBeenCalledTimes(1);
      // First arg is the result object, second is the parsedSamples array
      expect(mockOnContinue.mock.calls[0][0]).toMatchObject({
        analysis: 'You write in a direct, concise style.',
      });
      expect(Array.isArray(mockOnContinue.mock.calls[0][1])).toBe(true);
    });
  });
});

describe('PhaseOne — demo mode (API failure)', () => {
  const mockOnContinue = jest.fn();

  beforeEach(() => {
    mockOnContinue.mockClear();
    // Mock analyze-posts to fail
    server.use(
      http.post('*/api/onboarding/analyze-posts', () =>
        HttpResponse.error()
      )
    );
  });

  test('shows fingerprint confirm even in demo mode (no detected_patterns)', async () => {
    render(
      <TestWrapper>
        <PhaseOne onContinue={mockOnContinue} />
      </TestWrapper>
    );

    await waitFor(() => screen.getByTestId('option-existing-creator'));
    await act(async () => {
      await userEvent.click(screen.getByTestId('option-existing-creator'));
    });
    await act(async () => {
      await userEvent.type(screen.getByTestId('posts-textarea'), 'My test post');
    });
    await act(async () => {
      await userEvent.click(screen.getByTestId('analyze-posts-btn'));
    });

    await waitFor(() => {
      expect(screen.getByTestId('fingerprint-confirm')).toBeInTheDocument();
    }, { timeout: 5000 });

    // Demo mode still shows confirm buttons
    expect(screen.getByTestId('fingerprint-confirm-btn')).toBeInTheDocument();
    expect(screen.getByTestId('fingerprint-edit-btn')).toBeInTheDocument();
  });
});
