import { useState } from 'react';
import { Download, ExternalLink, Info, Loader2 } from 'lucide-react';
import {
  downloadTextFile,
  buildLinkedInUrl,
  buildXUrl,
  downloadImages,
} from '@/lib/contentExport';

/**
 * ExportActionsBar
 *
 * Renders download and redirect-to-platform action buttons for a content job.
 * Buttons are conditionally shown based on job platform and available media.
 *
 * @param {{ job: object, contentText: string }} props
 */
export function ExportActionsBar({ job, contentText }) {
  const [downloading, setDownloading] = useState(false);
  const [showInstagramTooltip, setShowInstagramTooltip] = useState(false);
  const [downloadError, setDownloadError] = useState(null);

  const hasImages =
    job.media_assets?.length > 0 ||
    (job.carousel?.generated && job.carousel?.slides?.length > 0);

  const isCarousel =
    job.carousel?.generated === true && job.carousel?.slides?.length > 0;

  const isEmpty = !contentText;

  function handleDownloadText() {
    setDownloadError(null);
    downloadTextFile(contentText, job.platform, new Date());
  }

  async function handleDownloadImages() {
    setDownloadError(null);
    setDownloading(true);
    try {
      await downloadImages(job.media_assets, job.carousel, job.job_id);
    } catch (err) {
      setDownloadError('Image download failed. Please try again.');
    } finally {
      setDownloading(false);
    }
  }

  function handleOpenLinkedIn() {
    setDownloadError(null);
    const url = buildLinkedInUrl(contentText);
    window.open(url, '_blank', 'noopener,noreferrer');
  }

  function handleOpenX() {
    setDownloadError(null);
    const url = buildXUrl(contentText);
    window.open(url, '_blank', 'noopener,noreferrer');
  }

  function handleInstagramInfo() {
    setShowInstagramTooltip((prev) => !prev);
  }

  return (
    <div className="mt-3" data-testid="export-actions-bar">
      <div className="flex flex-wrap gap-2">
        {/* Download .txt — always shown when content exists */}
        <button
          onClick={handleDownloadText}
          disabled={isEmpty}
          className="btn-ghost text-sm px-3 flex items-center gap-1.5 disabled:opacity-40 disabled:cursor-not-allowed"
          title="Download content as a text file"
        >
          <Download size={13} />
          Download .txt
        </button>

        {/* Download image(s) — only when media is present */}
        {hasImages && (
          <button
            onClick={handleDownloadImages}
            disabled={downloading}
            className="btn-ghost text-sm px-3 flex items-center gap-1.5 disabled:opacity-40 disabled:cursor-not-allowed"
            title={isCarousel ? 'Download all slides as a .zip' : 'Download image'}
          >
            {downloading ? (
              <>
                <Loader2 size={13} className="animate-spin" />
                Downloading...
              </>
            ) : (
              <>
                <Download size={13} />
                {isCarousel ? 'Download .zip' : 'Download Image'}
              </>
            )}
          </button>
        )}

        {/* Open in LinkedIn — only for linkedin jobs */}
        {job.platform === 'linkedin' && (
          <button
            onClick={handleOpenLinkedIn}
            disabled={isEmpty}
            className="btn-ghost text-sm px-3 flex items-center gap-1.5 text-blue-400 hover:text-blue-300 disabled:opacity-40 disabled:cursor-not-allowed"
            title="Open LinkedIn compose window with your text pre-filled"
          >
            <ExternalLink size={12} />
            Open in LinkedIn
          </button>
        )}

        {/* Open in X — only for x jobs */}
        {job.platform === 'x' && (
          <button
            onClick={handleOpenX}
            disabled={isEmpty}
            className="btn-ghost text-sm px-3 flex items-center gap-1.5 text-zinc-300 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed"
            title="Open X/Twitter compose window with your text pre-filled (truncated to 280 chars)"
          >
            <ExternalLink size={12} />
            Open in X
          </button>
        )}

        {/* Instagram — show info/tooltip, no broken link */}
        {job.platform === 'instagram' && (
          <button
            onClick={handleInstagramInfo}
            className="btn-ghost text-sm px-3 flex items-center gap-1.5 text-pink-400 hover:text-pink-300"
            title="See how to post to Instagram"
          >
            <Info size={12} />
            Post to Instagram
          </button>
        )}
      </div>

      {/* Instagram tooltip — inline, not a modal */}
      {showInstagramTooltip && (
        <div className="mt-2 p-3 bg-zinc-800 border border-zinc-700 rounded-xl text-xs text-zinc-300 leading-relaxed">
          <p className="font-semibold text-white mb-1">
            Instagram has no web compose URL
          </p>
          <p>1. Copy your post text using the Copy button above</p>
          <p>2. Open the Instagram app on your phone</p>
          <p>3. Tap + to create a new post and paste your text</p>
          <button
            onClick={() => setShowInstagramTooltip(false)}
            className="mt-2 text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            Got it
          </button>
        </div>
      )}

      {/* Download error message */}
      {downloadError && (
        <p className="text-xs text-red-400 mt-1">{downloadError}</p>
      )}
    </div>
  );
}
