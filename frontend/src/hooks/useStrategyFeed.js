import { useState, useEffect, useCallback } from "react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

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

  const getAuthHeaders = useCallback(() => {
    const token = localStorage.getItem("thook_token");
    const headers = {};
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
    return headers;
  }, []);

  const fetchActiveCards = useCallback(async () => {
    try {
      const res = await fetch(
        `${BACKEND_URL}/api/strategy?status=pending_approval&limit=3`,
        { credentials: "include", headers: getAuthHeaders() }
      );
      if (!res.ok) return;
      const data = await res.json();
      setActiveCards(data.cards || []);
    } catch (err) {
      console.error("[useStrategyFeed] Failed to fetch active cards:", err);
    }
  }, [getAuthHeaders]);

  const fetchHistoryCards = useCallback(async () => {
    try {
      const [dismissedRes, approvedRes] = await Promise.all([
        fetch(`${BACKEND_URL}/api/strategy?status=dismissed&limit=20`, {
          credentials: "include",
          headers: getAuthHeaders(),
        }),
        fetch(`${BACKEND_URL}/api/strategy?status=approved&limit=20`, {
          credentials: "include",
          headers: getAuthHeaders(),
        }),
      ]);

      const dismissed = dismissedRes.ok ? (await dismissedRes.json()).cards || [] : [];
      const approved = approvedRes.ok ? (await approvedRes.json()).cards || [] : [];

      // Merge and sort by created_at descending
      const merged = [...dismissed, ...approved].sort(
        (a, b) => new Date(b.created_at) - new Date(a.created_at)
      );
      setHistoryCards(merged);
    } catch (err) {
      console.error("[useStrategyFeed] Failed to fetch history cards:", err);
    }
  }, [getAuthHeaders]);

  /**
   * Approve a card. Refreshes active list and returns the generate_payload.
   * @param {string} recommendationId
   * @returns {Promise<object|null>} generate_payload or null on error
   */
  const approveCard = useCallback(
    async (recommendationId) => {
      const res = await fetch(
        `${BACKEND_URL}/api/strategy/${recommendationId}/approve`,
        {
          method: "POST",
          credentials: "include",
          headers: getAuthHeaders(),
        }
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Approve failed");
      }
      const data = await res.json();
      // Refresh active list (card just moved out of pending_approval)
      await fetchActiveCards();
      return data.generate_payload;
    },
    [getAuthHeaders, fetchActiveCards]
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
      const headers = {
        ...getAuthHeaders(),
        ...(body ? { "Content-Type": "application/json" } : {}),
      };

      const res = await fetch(
        `${BACKEND_URL}/api/strategy/${recommendationId}/dismiss`,
        {
          method: "POST",
          credentials: "include",
          headers,
          ...(body ? { body } : {}),
        }
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Dismiss failed");
      }
      const data = await res.json();
      // Refresh both lists
      await Promise.all([fetchActiveCards(), fetchHistoryCards()]);
      return data;
    },
    [getAuthHeaders, fetchActiveCards, fetchHistoryCards]
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
