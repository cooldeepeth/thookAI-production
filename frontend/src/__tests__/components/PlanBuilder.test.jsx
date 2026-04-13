/**
 * PlanBuilder component tests — gates Phase 33 DSGN-02.
 * Verifies landing mode CTA, settings mode checkout callback, disabled state.
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { PlanBuilder } from '@/components/PlanBuilder';

// Radix Slider uses ResizeObserver — not in jsdom
global.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Radix Slider also uses pointer events / hasPointerCapture
if (!Element.prototype.hasPointerCapture) {
  Element.prototype.hasPointerCapture = () => false;
  Element.prototype.setPointerCapture = () => {};
  Element.prototype.releasePointerCapture = () => {};
}

jest.mock('@/lib/api', () => ({
  apiFetch: jest.fn().mockResolvedValue({
    ok: true,
    json: () =>
      Promise.resolve({
        total_credits: 200,
        total_price: 15,
        price_per_credit: 0.075,
      }),
  }),
}));

jest.mock('framer-motion', () => ({
  motion: new Proxy(
    {},
    {
      get: () => {
        const Component = ({ children, ...props }) => <div {...props}>{children}</div>;
        return Component;
      },
    },
  ),
  AnimatePresence: ({ children }) => <>{children}</>,
}));

const renderPlanBuilder = (props = {}) =>
  render(
    <MemoryRouter>
      <PlanBuilder {...props} />
    </MemoryRouter>,
  );

describe('PlanBuilder', () => {
  test('renders in landing mode with Get Started CTA (DSGN-02)', () => {
    renderPlanBuilder({ mode: 'landing' });
    expect(screen.getByTestId('plan-builder-cta')).toBeInTheDocument();
    expect(screen.queryByTestId('plan-builder-checkout')).not.toBeInTheDocument();
  });

  test('renders in settings mode with checkout button', () => {
    const onCheckout = jest.fn();
    renderPlanBuilder({
      mode: 'settings',
      onCheckout,
      subscription: null,
      upgrading: null,
    });
    expect(screen.getByTestId('plan-builder-checkout')).toBeInTheDocument();
    expect(screen.queryByTestId('plan-builder-cta')).not.toBeInTheDocument();
  });

  test('settings mode checkout button calls onCheckout with plan usage', () => {
    const onCheckout = jest.fn();
    renderPlanBuilder({
      mode: 'settings',
      onCheckout,
      subscription: null,
      upgrading: null,
    });
    fireEvent.click(screen.getByTestId('plan-builder-checkout'));
    expect(onCheckout).toHaveBeenCalledTimes(1);
    expect(onCheckout).toHaveBeenCalledWith(
      expect.objectContaining({ text_posts: expect.any(Number) }),
    );
  });

  test('settings mode checkout button is disabled when upgrading', () => {
    renderPlanBuilder({
      mode: 'settings',
      onCheckout: jest.fn(),
      subscription: null,
      upgrading: 'custom',
    });
    expect(screen.getByTestId('plan-builder-checkout')).toBeDisabled();
  });

  test('renders sliders for plan builder content types', () => {
    renderPlanBuilder({ mode: 'landing' });
    expect(screen.getByText(/Text Posts/i)).toBeInTheDocument();
    expect(screen.getByText(/Images/i)).toBeInTheDocument();
    expect(screen.getByText(/Videos/i)).toBeInTheDocument();
    expect(screen.getByText(/Carousels/i)).toBeInTheDocument();
  });

  test('settings mode shows different CTA label depending on subscription tier', () => {
    const { rerender } = renderPlanBuilder({
      mode: 'settings',
      onCheckout: jest.fn(),
      subscription: { tier: 'free' },
      upgrading: null,
    });
    expect(screen.getByTestId('plan-builder-checkout')).toHaveTextContent(/Customize My Plan/i);

    rerender(
      <MemoryRouter>
        <PlanBuilder
          mode="settings"
          onCheckout={jest.fn()}
          subscription={{ tier: 'custom' }}
          upgrading={null}
        />
      </MemoryRouter>,
    );
    expect(screen.getByTestId('plan-builder-checkout')).toHaveTextContent(/Update My Plan/i);
  });
});
