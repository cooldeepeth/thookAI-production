/**
 * LandingPage tests — gates Phase 33 DSGN-01..05.
 * Covers section render, mobile nav, token audit, and OG meta tags.
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import LandingPage from '@/pages/LandingPage';

// Radix Slider (used inside PlanBuilder → PricingSection) needs ResizeObserver + pointer capture
global.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
};
if (!Element.prototype.hasPointerCapture) {
  Element.prototype.hasPointerCapture = () => false;
  Element.prototype.setPointerCapture = () => {};
  Element.prototype.releasePointerCapture = () => {};
}

jest.mock('@/lib/api', () => ({
  apiFetch: jest.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve({ total_credits: 200, total_price: 0 }),
  }),
}));

jest.mock('framer-motion', () => ({
  motion: new Proxy(
    {},
    {
      get: () => {
        const Component = ({ children, whileInView, viewport, initial, animate, exit, transition, ...rest }) => (
          <div {...rest}>{children}</div>
        );
        return Component;
      },
    },
  ),
  AnimatePresence: ({ children }) => <>{children}</>,
}));

const renderLanding = () =>
  render(
    <MemoryRouter>
      <LandingPage />
    </MemoryRouter>,
  );

describe('LandingPage', () => {
  test('renders landing page root', () => {
    renderLanding();
    expect(screen.getByTestId('landing-page')).toBeInTheDocument();
  });

  test('renders Navbar with logo and CTA', () => {
    renderLanding();
    expect(screen.getByTestId('landing-navbar')).toBeInTheDocument();
    expect(screen.getByTestId('nav-cta-btn')).toBeInTheDocument();
  });

  test('renders Hero section', () => {
    renderLanding();
    expect(screen.getByTestId('hero-section')).toBeInTheDocument();
  });

  test('renders HowItWorks section with 3 steps (DSGN-02)', () => {
    renderLanding();
    expect(screen.getByTestId('how-it-works-section')).toBeInTheDocument();
    expect(screen.getByTestId('how-it-works-step-1')).toBeInTheDocument();
    expect(screen.getByTestId('how-it-works-step-2')).toBeInTheDocument();
    expect(screen.getByTestId('how-it-works-step-3')).toBeInTheDocument();
  });

  test('renders SocialProof section with metrics (DSGN-03)', () => {
    renderLanding();
    const section = screen.getByTestId('social-proof-section');
    expect(section).toBeInTheDocument();
    // Scope the metric label query to within the SocialProof section to avoid
    // collisions with the hero copy that also mentions AI agents.
    expect(section.textContent).toMatch(/Specialist AI Agents/);
    expect(section.textContent).toMatch(/Free Credits/);
    expect(section.textContent).toMatch(/Social Platforms/);
  });

  test('renders PricingSection (DSGN-02)', () => {
    renderLanding();
    expect(screen.getByTestId('pricing-section')).toBeInTheDocument();
  });

  test('renders Footer with legal links (DSGN-02)', () => {
    renderLanding();
    expect(screen.getByTestId('landing-footer')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /privacy/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /terms/i })).toBeInTheDocument();
  });

  test('Navbar shows mobile hamburger menu button (DSGN-04)', () => {
    renderLanding();
    expect(screen.getByTestId('mobile-menu-btn')).toBeInTheDocument();
  });

  test('mobile hamburger button is keyboard accessible (DSGN-04)', () => {
    renderLanding();
    const hamburger = screen.getByTestId('mobile-menu-btn');
    expect(hamburger).toHaveAttribute('aria-label', 'Open navigation menu');
    expect(hamburger.tagName).toBe('BUTTON');
  });

  test('LandingPage root has overflow-x-hidden (DSGN-04)', () => {
    renderLanding();
    const root = screen.getByTestId('landing-page');
    expect(root.className).toMatch(/overflow-x-hidden/);
  });

  test('DSGN-01: no invalid lime shade variants in Landing/ section files', () => {
    const fs = require('fs');
    const path = require('path');
    const landingDir = path.join(__dirname, '../../pages/Landing');
    const files = fs.readdirSync(landingDir).filter((f) => f.endsWith('.jsx'));
    const violations = [];
    files.forEach((file) => {
      const content = fs.readFileSync(path.join(landingDir, file), 'utf8');
      const matches = content.match(/\blime-[0-9]/g);
      if (matches) violations.push(`${file}: ${matches.join(', ')}`);
    });
    expect(violations).toEqual([]);
  });

  test('DSGN-05: index.html contains required OG meta tags', () => {
    const fs = require('fs');
    const path = require('path');
    const html = fs.readFileSync(
      path.join(__dirname, '../../../public/index.html'),
      'utf8',
    );
    expect(html).toContain('og:image');
    expect(html).toContain('og:title');
    expect(html).toContain('twitter:card');
    expect(html).toContain('thook.ai');
    expect(html).toContain('ThookAI');
    expect(html).toContain('canonical');
  });
});
