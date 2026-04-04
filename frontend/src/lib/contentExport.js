/**
 * contentExport.js
 * Pure utility functions for downloading content and opening platform compose windows.
 * All operations are client-side — no backend calls required.
 */

import JSZip from 'jszip';

/**
 * Formats a Date object as YYYY-MM-DD.
 * @param {Date} date
 * @returns {string}
 */
function formatDate(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

/**
 * Triggers a browser download of a .txt file containing the provided text.
 * @param {string} text - Content to write into the file
 * @param {string} platform - Platform name (e.g. "linkedin", "x", "instagram")
 * @param {Date} date - Date used in the filename (defaults to now)
 * @returns {void}
 */
export function downloadTextFile(text, platform, date = new Date()) {
  const filename = `${platform}-${formatDate(date)}.txt`;
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

/**
 * Builds a LinkedIn shareArticle URL with the post text pre-filled.
 * Uses the official LinkedIn share endpoint.
 * @param {string} text - Content to pre-fill
 * @returns {string} Full URL
 */
export function buildLinkedInUrl(text) {
  const params = new URLSearchParams({
    mini: 'true',
    summary: text,
  });
  return `https://www.linkedin.com/shareArticle?${params.toString()}`;
}

/**
 * Builds an X/Twitter tweet intent URL with the text truncated to 280 chars.
 * @param {string} text - Content to pre-fill
 * @returns {string} Full URL
 */
export function buildXUrl(text) {
  const MAX_CHARS = 280;
  const truncated =
    text.length > MAX_CHARS ? text.slice(0, 277) + '...' : text;
  const params = new URLSearchParams({ text: truncated });
  return `https://twitter.com/intent/tweet?${params.toString()}`;
}

/**
 * Extracts the file extension from a URL.
 * Defaults to 'jpg' if none can be determined.
 * @param {string} url
 * @returns {string}
 */
function extensionFromUrl(url) {
  try {
    const pathname = new URL(url).pathname;
    const match = pathname.match(/\.(\w{2,5})$/);
    return match ? match[1].toLowerCase() : 'jpg';
  } catch {
    return 'jpg';
  }
}

/**
 * Downloads image(s) for a content job.
 * - Single image: triggers a direct anchor download.
 * - Carousel: fetches all slide images, zips them, and triggers a .zip download.
 *
 * @param {Array<{image_url: string}>} mediaAssets - Single-image media assets
 * @param {{ generated: boolean, slides: Array<{image_url: string, slide_number: number}> } | null} carousel - Carousel data
 * @param {string} jobId - Job ID used in the zip filename
 * @returns {Promise<void>}
 */
export async function downloadImages(mediaAssets, carousel, jobId) {
  const isCarousel =
    carousel?.generated === true && carousel?.slides?.length > 0;

  if (!isCarousel) {
    // Single image download via anchor
    const imageUrl = mediaAssets?.[0]?.image_url;
    if (!imageUrl) {
      throw new Error('No image URL available for download');
    }
    const ext = extensionFromUrl(imageUrl);
    const anchor = document.createElement('a');
    anchor.href = imageUrl;
    anchor.download = `image-${jobId}.${ext}`;
    anchor.target = '_blank';
    anchor.rel = 'noopener noreferrer';
    anchor.click();
    return;
  }

  // Carousel: fetch each slide and build a zip
  try {
    const zip = new JSZip();

    await Promise.all(
      carousel.slides.map(async (slide, index) => {
        const slideUrl = slide.image_url;
        if (!slideUrl) return;
        const response = await fetch(slideUrl);
        if (!response.ok) {
          throw new Error(
            `Failed to fetch slide ${slide.slide_number ?? index + 1}: ${response.status}`
          );
        }
        const buffer = await response.arrayBuffer();
        const ext = extensionFromUrl(slideUrl);
        const slideNumber = slide.slide_number ?? index + 1;
        zip.file(`slide-${slideNumber}.${ext}`, buffer);
      })
    );

    const blob = await zip.generateAsync({ type: 'blob' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `carousel-${jobId}.zip`;
    anchor.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    console.error('[contentExport] downloadImages failed:', err);
    throw err;
  }
}
