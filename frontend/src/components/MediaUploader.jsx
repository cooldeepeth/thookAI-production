import { useCallback, useRef, useState } from 'react';
import { Image as ImageIcon, Link2, Play, X, Upload } from 'lucide-react';
import { apiFetch } from '@/lib/api';
import { API_BASE_URL } from '@/lib/constants';

const MAX_FILE_BYTES = 100 * 1024 * 1024;

/**
 * @param {object} props
 * @param {Array<{ upload_id: string, url: string, content_type: string, title?: string, context_type?: string }>} props.items
 * @param {(next: typeof props.items) => void} props.onItemsChange
 * @param {(upload: object) => void} [props.onUploadComplete]
 */
export default function MediaUploader({ items, onItemsChange, onUploadComplete }) {
  const [urlInput, setUrlInput] = useState('');
  const [urlLoading, setUrlLoading] = useState(false);
  const [fileProgress, setFileProgress] = useState(0);
  const [fileBusy, setFileBusy] = useState(false);
  const inputRef = useRef(null);

  const removeItem = (uploadId) => {
    onItemsChange((prev) => (Array.isArray(prev) ? prev : items).filter((i) => i.upload_id !== uploadId));
  };

  const addItem = useCallback(
    (u) => {
      onItemsChange((prev) => [...(Array.isArray(prev) ? prev : items), u]);
      onUploadComplete?.(u);
    },
    [items, onItemsChange, onUploadComplete]
  );

  const inferContextType = (file) => {
    const t = file.type || '';
    if (t.startsWith('image/')) return 'image';
    if (t.startsWith('video/')) return 'video';
    if (t === 'application/pdf' || t === 'text/plain') return 'document';
    const n = file.name.toLowerCase();
    if (/\.(jpg|jpeg|png|gif|webp)$/i.test(n)) return 'image';
    if (/\.(mp4|mov|webm)$/i.test(n)) return 'video';
    if (/\.(pdf|txt)$/i.test(n)) return 'document';
    return null;
  };

  const uploadFile = async (file) => {
    if (file.size > MAX_FILE_BYTES) {
      alert('File must be 100MB or smaller');
      return;
    }
    const contextType = inferContextType(file);
    if (!contextType) {
      alert('Unsupported file type');
      return;
    }
    setFileBusy(true);
    setFileProgress(10);
    const fd = new FormData();
    fd.append('file', file);
    fd.append('context_type', contextType);
    try {
      // Use XHR for file upload to track progress via xhr.upload.onprogress.
      // apiFetch wraps fetch() which does not expose upload progress.
      // Auth via cookie: xhr.withCredentials = true sends the session_token cookie automatically.
      const xhr = new XMLHttpRequest();
      const p = new Promise((resolve, reject) => {
        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable) setFileProgress(Math.min(90, 10 + (e.loaded / e.total) * 80));
        };
        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            try {
              resolve(JSON.parse(xhr.responseText));
            } catch {
              reject(new Error('Invalid response'));
            }
          } else {
            try {
              const j = JSON.parse(xhr.responseText);
              reject(new Error(j.detail || 'Upload failed'));
            } catch {
              reject(new Error('Upload failed'));
            }
          }
        };
        xhr.onerror = () => reject(new Error('Network error'));
      });
      xhr.open('POST', `${API_BASE_URL}/api/uploads/media`);
      xhr.withCredentials = true;
      xhr.send(fd);
      const data = await p;
      setFileProgress(100);
      addItem({
        upload_id: data.upload_id,
        url: data.url,
        content_type: data.content_type,
        context_type: contextType,
        filename: file.name,
        size_bytes: file.size,
      });
    } catch (e) {
      alert(e.message || 'Upload failed');
    } finally {
      setFileBusy(false);
      setFileProgress(0);
    }
  };

  const onDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    const f = e.dataTransfer.files?.[0];
    if (f) uploadFile(f);
  };

  const submitUrl = async (e) => {
    e.preventDefault();
    const u = urlInput.trim();
    if (!u) return;
    setUrlLoading(true);
    try {
      const res = await apiFetch('/api/uploads/url', {
        method: 'POST',
        body: JSON.stringify({ url: u, context_type: 'link' }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || 'Could not add link');
      addItem({
        upload_id: data.upload_id,
        url: data.url,
        content_type: 'link',
        title: data.title,
        context_type: 'link',
      });
      setUrlInput('');
    } catch (err) {
      alert(err.message);
    } finally {
      setUrlLoading(false);
    }
  };

  return (
    <div className="space-y-3">
      <div
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && inputRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={onDrop}
        onClick={() => !fileBusy && inputRef.current?.click()}
        className="rounded-xl border border-dashed border-white/10 bg-[#18181B] p-4 text-center cursor-pointer hover:border-white/20 transition-colors"
      >
        <input
          ref={inputRef}
          type="file"
          accept=".jpg,.jpeg,.png,.gif,.webp,.mp4,.mov,.webm,.pdf,.txt,image/*,video/*"
          className="hidden"
          disabled={fileBusy}
          onChange={(e) => {
            const f = e.target.files?.[0];
            e.target.value = '';
            if (f) uploadFile(f);
          }}
        />
        <Upload className="w-6 h-6 text-zinc-500 mx-auto mb-2" />
        <p className="text-xs text-zinc-400">Drag & drop or click to upload</p>
        <p className="text-[10px] text-zinc-600 mt-1">Images, video, PDF — max 100MB</p>
        {fileBusy && (
          <div className="mt-3 h-1.5 bg-white/5 rounded-full overflow-hidden">
            <div
              className="h-full bg-lime transition-all duration-300"
              style={{ width: `${fileProgress}%` }}
            />
          </div>
        )}
      </div>

      <form onSubmit={submitUrl} className="flex gap-2">
        <input
          type="url"
          value={urlInput}
          onChange={(e) => setUrlInput(e.target.value)}
          placeholder="Paste a URL or link..."
          className="flex-1 bg-[#18181B] border border-white/10 rounded-xl h-10 px-3 text-xs text-white placeholder:text-zinc-600 outline-none focus:border-lime/40"
        />
        <button
          type="submit"
          disabled={urlLoading || !urlInput.trim()}
          className="px-3 rounded-xl border border-white/10 text-xs text-zinc-300 hover:bg-white/5 disabled:opacity-50"
        >
          {urlLoading ? '…' : 'Add'}
        </button>
      </form>

      {items.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {items.map((it) => (
            <div
              key={it.upload_id}
              className="flex items-center gap-2 pl-1 pr-1 py-1 rounded-lg bg-white/5 border border-white/10 max-w-full"
            >
              {it.context_type === 'image' && it.url?.startsWith('http') ? (
                <img src={it.url} alt="" className="w-8 h-8 rounded object-cover flex-shrink-0" />
              ) : it.context_type === 'image' ? (
                <ImageIcon className="w-8 h-8 text-zinc-500 flex-shrink-0" />
              ) : it.context_type === 'video' ? (
                <Play className="w-8 h-8 text-zinc-400 flex-shrink-0 p-1" />
              ) : it.context_type === 'link' ? (
                <Link2 className="w-8 h-8 text-zinc-400 flex-shrink-0 p-1" />
              ) : (
                <span className="w-8 h-8 flex items-center justify-center text-[10px] text-zinc-500 font-mono">DOC</span>
              )}
              <span className="text-[10px] text-zinc-400 truncate max-w-[140px]">
                {it.title || it.filename || it.url?.slice(-24) || it.upload_id}
              </span>
              <button
                type="button"
                onClick={() => removeItem(it.upload_id)}
                className="p-1 rounded text-zinc-500 hover:text-white hover:bg-white/10"
                aria-label="Remove"
              >
                <X size={14} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
