import { useState, useEffect, useCallback, useRef } from 'react';
import { apiFetch } from '@/lib/api';
import { API_BASE_URL } from '@/lib/constants';

/**
 * React hook for managing notifications via REST + SSE.
 *
 * - Fetches initial unread count on mount.
 * - Opens an SSE connection to /api/notifications/stream.
 * - Updates state on new events.
 * - Exposes: { notifications, unreadCount, markRead, markAllRead, loading }
 */
export default function useNotifications() {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const eventSourceRef = useRef(null);

  // Fetch notifications list
  const fetchNotifications = useCallback(async (limit = 10) => {
    try {
      const res = await apiFetch(`/api/notifications?limit=${limit}`);
      if (!res.ok) return;
      const data = await res.json();
      setNotifications(data.notifications || []);
    } catch (err) {
      console.error('Failed to fetch notifications:', err);
    }
  }, []);

  // Fetch unread count
  const fetchUnreadCount = useCallback(async () => {
    try {
      const res = await apiFetch('/api/notifications/count');
      if (!res.ok) return;
      const data = await res.json();
      setUnreadCount(data.unread_count || 0);
    } catch (err) {
      console.error('Failed to fetch unread count:', err);
    }
  }, []);

  // Mark a single notification as read
  const markRead = useCallback(async (notificationId) => {
    try {
      const res = await apiFetch(`/api/notifications/${notificationId}/read`, {
        method: 'POST',
      });
      if (!res.ok) return;
      setNotifications((prev) =>
        prev.map((n) =>
          n.notification_id === notificationId ? { ...n, read: true } : n
        )
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch (err) {
      console.error('Failed to mark notification read:', err);
    }
  }, []);

  // Mark all notifications as read
  const markAllRead = useCallback(async () => {
    try {
      const res = await apiFetch('/api/notifications/read-all', {
        method: 'POST',
      });
      if (!res.ok) return;
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
      setUnreadCount(0);
    } catch (err) {
      console.error('Failed to mark all notifications read:', err);
    }
  }, []);

  // Open SSE connection
  useEffect(() => {
    // Initial data load
    const init = async () => {
      setLoading(true);
      await Promise.all([fetchNotifications(10), fetchUnreadCount()]);
      setLoading(false);
    };
    init();

    // Open SSE stream
    // Note: EventSource does not support custom headers natively.
    // Auth relies on cookie-based session_token for SSE connections.
    const streamUrl = `${API_BASE_URL}/api/notifications/stream`;

    try {
      const eventSource = new EventSource(streamUrl, {
        withCredentials: true,
      });
      eventSourceRef.current = eventSource;

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.notifications && data.notifications.length > 0) {
            setNotifications((prev) => {
              // Merge new notifications, avoiding duplicates
              const existingIds = new Set(prev.map((n) => n.notification_id));
              const newOnes = data.notifications.filter(
                (n) => !existingIds.has(n.notification_id)
              );
              return [...newOnes, ...prev].slice(0, 20);
            });
          }
          if (typeof data.unread_count === 'number') {
            setUnreadCount(data.unread_count);
          }
        } catch (parseErr) {
          // Ignore parse errors (heartbeats, etc.)
        }
      };

      eventSource.onerror = () => {
        // EventSource will auto-reconnect; no action needed
      };
    } catch (err) {
      console.error('Failed to open SSE connection:', err);
    }

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, [fetchNotifications, fetchUnreadCount]);

  return {
    notifications,
    unreadCount,
    markRead,
    markAllRead,
    loading,
    refresh: () =>
      Promise.all([fetchNotifications(10), fetchUnreadCount()]),
  };
}
