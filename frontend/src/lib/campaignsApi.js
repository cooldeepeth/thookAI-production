import { apiFetch } from './api';

/**
 * Create a new campaign.
 */
export async function createCampaign(payload) {
  const res = await apiFetch('/api/campaigns', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to create campaign');
  }
  return res.json();
}

/**
 * List campaigns for the current user.
 * @param {Object} filters - { status, platform }
 */
export async function getCampaigns(filters = {}) {
  const params = new URLSearchParams();
  if (filters.status) params.append('status', filters.status);
  if (filters.platform) params.append('platform', filters.platform);

  const res = await apiFetch(`/api/campaigns?${params}`);
  if (!res.ok) throw new Error('Failed to fetch campaigns');
  return res.json();
}

/**
 * Get a single campaign with its content jobs.
 */
export async function getCampaign(campaignId) {
  const res = await apiFetch(`/api/campaigns/${campaignId}`);
  if (!res.ok) throw new Error('Campaign not found');
  return res.json();
}

/**
 * Update a campaign.
 */
export async function updateCampaign(campaignId, payload) {
  const res = await apiFetch(`/api/campaigns/${campaignId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to update campaign');
  }
  return res.json();
}

/**
 * Soft-delete (archive) a campaign.
 */
export async function deleteCampaign(campaignId) {
  const res = await apiFetch(`/api/campaigns/${campaignId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to archive campaign');
  return res.json();
}

/**
 * Add a content job to a campaign.
 */
export async function addContentToCampaign(campaignId, jobId) {
  const res = await apiFetch(
    `/api/campaigns/${campaignId}/add-content/${jobId}`,
    { method: 'POST' }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to add content');
  }
  return res.json();
}

/**
 * Remove a content job from a campaign.
 */
export async function removeContentFromCampaign(campaignId, jobId) {
  const res = await apiFetch(
    `/api/campaigns/${campaignId}/content/${jobId}`,
    { method: 'DELETE' }
  );
  if (!res.ok) throw new Error('Failed to remove content');
  return res.json();
}

/**
 * Get aggregate stats for a campaign.
 */
export async function getCampaignStats(campaignId) {
  const res = await apiFetch(`/api/campaigns/${campaignId}/stats`);
  if (!res.ok) throw new Error('Failed to fetch campaign stats');
  return res.json();
}
