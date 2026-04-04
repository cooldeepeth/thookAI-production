import { apiFetch } from './api';

/**
 * Browse templates with optional filters.
 * @param {Object} filters - { platform, category, hook_type, sort, limit, offset }
 */
export async function getTemplates(filters = {}) {
  const params = new URLSearchParams();
  if (filters.platform) params.append('platform', filters.platform);
  if (filters.category) params.append('category', filters.category);
  if (filters.hook_type) params.append('hook_type', filters.hook_type);
  if (filters.sort) params.append('sort', filters.sort);
  if (filters.limit) params.append('limit', String(filters.limit));
  if (filters.offset !== undefined) params.append('offset', String(filters.offset));

  const res = await apiFetch(`/api/templates?${params}`);
  if (!res.ok) throw new Error('Failed to fetch templates');
  return res.json();
}

/**
 * Get a single template by ID.
 */
export async function getTemplate(templateId) {
  const res = await apiFetch(`/api/templates/${templateId}`);
  if (!res.ok) throw new Error('Template not found');
  return res.json();
}

/**
 * Toggle upvote on a template.
 */
export async function upvoteTemplate(templateId) {
  const res = await apiFetch(`/api/templates/${templateId}/upvote`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to upvote template');
  return res.json();
}

/**
 * Use a template — returns prefill data for Content Studio.
 * @param {string} templateId
 * @param {Object} options - { platform }
 */
export async function useTemplate(templateId, options = {}) {
  const res = await apiFetch(`/api/templates/${templateId}/use`, {
    method: 'POST',
    body: JSON.stringify({ platform: options.platform || null }),
  });
  if (!res.ok) throw new Error('Failed to use template');
  return res.json();
}

/**
 * Publish approved content as a template.
 * @param {Object} templateData - { job_id, title, category, description, tags }
 */
export async function createTemplate(templateData) {
  const res = await apiFetch('/api/templates', {
    method: 'POST',
    body: JSON.stringify(templateData),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || 'Failed to create template');
  }
  return res.json();
}

/**
 * Get templates published by the current user.
 */
export async function getMyPublishedTemplates() {
  const res = await apiFetch('/api/templates/my/published');
  if (!res.ok) throw new Error('Failed to fetch your templates');
  return res.json();
}

/**
 * Get templates the current user has used.
 */
export async function getMyUsedTemplates() {
  const res = await apiFetch('/api/templates/my/used');
  if (!res.ok) throw new Error('Failed to fetch used templates');
  return res.json();
}

/**
 * Get available categories and hook types.
 */
export async function getCategories() {
  const res = await apiFetch('/api/templates/categories');
  if (!res.ok) throw new Error('Failed to fetch categories');
  return res.json();
}

/**
 * Get featured/trending templates.
 */
export async function getFeaturedTemplates() {
  const res = await apiFetch('/api/templates/featured');
  if (!res.ok) throw new Error('Failed to fetch featured templates');
  return res.json();
}

/**
 * Delete a template (author only).
 */
export async function deleteTemplate(templateId) {
  const res = await apiFetch(`/api/templates/${templateId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete template');
  return res.json();
}
