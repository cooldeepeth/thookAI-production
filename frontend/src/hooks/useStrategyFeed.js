import { useState, useEffect, useCallback } from 'react';
import { apiFetch } from '@/lib/api';

/**
 * React hook for managing strategy recommendation cards.
 *
 * - Fetches active (pending_approval) cards on mount.
 * - Fetches history (dismissed + approved) cards on mount.
 * - Exposes approveCard and dismissCard actions.
 * - Returns refresh for SSE-driven re-fetches.
 *
 * Returns: { activeCards, historyCards, loading, approveCard, dismissCard, refresh }
 */
export default function useStrategyFeed() {
  const [activeCards, setActiveCards] = useState([]);
  const [historyCards, setHistoryCards] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchActiveCards = useCallback(async () => {
    try {
      const res = await apiFetch('/api/strategy?status=pending_approval&limit=3');
      if (!res.ok) return;
      const data = await res.json();
      setActiveCards(data.cards || []);
    } catch (err) {
      console.error('[useStrategyFeed] Failed to fetch active cards:', err);
    }
  }, []);

  const fetchHistoryCards = useCallback(async () => {
    try {
      const [dismissedRes, approvedRes] = await Promise.all([
        apiFetch('/api/strategy?status=dismissed&limit=20'),
        apiFetch('/api/strategy?status=approved&limit=20'),
      ]);

      const dismissed = dismissedRes.ok ? (await dismissedRes.json()).cards || [] : [];
      const approved = approvedRes.ok ? (await approvedRes.json()).cards || [] : [];

      // Merge and sort by created_at descending
      const merged = [...dismissed, ...approved].sort(
        (a, b) => new Date(b.created_at) - new Date(a.created_at)
      );
      setHistoryCards(merged);
    } catch (err) {
      console.error('[useStrategyFeed] Failed to fetch history cards:', err);
    }
  }, []);

  /**
   * Approve a card. Refreshes active list and returns the generate_payload.
   * @param {string} recommendationId
   * @returns {Promise<object|null>} generate_payload or null on error
   */
  const approveCard = useCallback(
    async (recommendationId) => {
      const res = await apiFetch(`/api/strategy/${recommendationId}/approve`, {
        method: 'POST',
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Approve failed');
      }
      const data = await res.json();
      // Refresh active list (card just moved out of pending_approval)
      await fetchActiveCards();
      return data.generate_payload;
    },
    [fetchActiveCards]
  );

  /**
   * Dismiss a card. Refreshes both active and history lists.
   * @param {string} recommendationId
   * @param {string} [reason]
   * @returns {Promise<object>} dismiss response (check needs_calibration_prompt)
   */
  const dismissCard = useCallback(
    async (recommendationId, reason) => {
      const body = reason ? JSON.stringify({ reason }) : undefined;

      const res = await apiFetch(`/api/strategy/${recommendationId}/dismiss`, {
        method: 'POST',
        ...(body ? { body } : {}),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Dismiss failed');
      }
      const data = await res.json();
      // Refresh both lists
      await Promise.all([fetchActiveCards(), fetchHistoryCards()]);
      return data;
    },
    [fetchActiveCards, fetchHistoryCards]
  );

  // Initial data load
  useEffect(() => {
    const init = async () => {
      setLoading(true);
      await Promise.all([fetchActiveCards(), fetchHistoryCards()]);
      setLoading(false);
    };
    init();
  }, [fetchActiveCards, fetchHistoryCards]);

  return {
    activeCards,
    historyCards,
    loading,
    approveCard,
    dismissCard,
    refresh: fetchActiveCards,
  };
}
