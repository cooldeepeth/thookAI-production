import { useState, useRef, useCallback } from "react";
import { Upload, X, CheckCircle, AlertCircle, Loader2, FileVideo, FileAudio, Image, FileText } from "lucide-react";

const BACKEND_URL = import.meta.env.REACT_APP_BACKEND_URL || process.env.REACT_APP_BACKEND_URL;

// File type icons
const FILE_TYPE_ICONS = {
  video: FileVideo,
  audio: FileAudio,
  image: Image,
  document: FileText
};

// Default max sizes in MB
const DEFAULT_MAX_SIZES = {
  video: 500,
  audio: 50,
  image: 10,
  document: 25
};

/**
 * MediaUploader - Client-side direct upload to R2 via presigned URLs
 * 
 * Props:
 * - fileType: "video" | "audio" | "image" | "document"
 * - onUploadComplete: function({ media_id, storage_key, public_url, filename })
 * - onError: function(errorMessage)
 * - accept: string (MIME types, e.g. "video/*,audio/*")
 * - maxSizeMB: number (max file size in MB)
 * - label: string (display label)
 * - jobId: string (optional, to associate upload with a content job)
 */
export default function MediaUploader({
  fileType = "image",
  onUploadComplete,
  onError,
  accept,
  maxSizeMB,
  label,
  jobId
}) {
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("idle"); // idle, uploading, confirming, complete, error
  const [progress, setProgress] = useState(0);
  const [errorMessage, setErrorMessage] = useState(null);
  const [uploadedAsset, setUploadedAsset] = useState(null);
  const fileInputRef = useRef(null);

  const maxSize = maxSizeMB || DEFAULT_MAX_SIZES[fileType] || 50;
  const acceptTypes = accept || getDefaultAcceptTypes(fileType);
  const displayLabel = label || `Upload ${fileType}`;
  const FileIcon = FILE_TYPE_ICONS[fileType] || Upload;

  function getDefaultAcceptTypes(type) {
    switch (type) {
      case "video": return "video/mp4,video/webm,video/quicktime";
      case "audio": return "audio/mpeg,audio/wav,audio/ogg,audio/aac";
      case "image": return "image/jpeg,image/png,image/webp,image/gif";
      case "document": return "application/pdf,text/plain";
      default: return "*/*";
    }
  }

  const handleError = useCallback((message) => {
    setStatus("error");
    setErrorMessage(message);
    onError?.(message);
  }, [onError]);

  const validateFile = (selectedFile) => {
    if (!selectedFile) return false;
    
    // Check file size
    const fileSizeMB = selectedFile.size / (1024 * 1024);
    if (fileSizeMB > maxSize) {
      handleError(`File too large. Maximum size is ${maxSize}MB.`);
      return false;
    }

    // Check file type (basic validation)
    const allowedTypes = acceptTypes.split(",").map(t => t.trim());
    const isAllowed = allowedTypes.some(type => {
      if (type.endsWith("/*")) {
        return selectedFile.type.startsWith(type.replace("/*", ""));
      }
      return selectedFile.type === type;
    });

    if (!isAllowed && acceptTypes !== "*/*") {
      handleError(`Invalid file type. Allowed: ${acceptTypes}`);
      return false;
    }

    return true;
  };

  const uploadFile = async (selectedFile) => {
    if (!validateFile(selectedFile)) return;

    setFile(selectedFile);
    setStatus("uploading");
    setProgress(0);
    setErrorMessage(null);

    try {
      const token = localStorage.getItem("thook_token");

      // Step 1: Get presigned upload URL
      const urlRes = await fetch(`${BACKEND_URL}/api/media/upload-url`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          file_type: fileType,
          filename: selectedFile.name,
          content_type: selectedFile.type
        })
      });

      if (!urlRes.ok) {
        const err = await urlRes.json();
        throw new Error(err.detail || "Failed to get upload URL");
      }

      const { upload_url, storage_key } = await urlRes.json();

      // Step 2: Upload file directly to R2 using XMLHttpRequest for progress
      await new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        
        xhr.upload.addEventListener("progress", (e) => {
          if (e.lengthComputable) {
            const percentComplete = Math.round((e.loaded / e.total) * 100);
            setProgress(percentComplete);
          }
        });

        xhr.addEventListener("load", () => {
          if (xhr.status === 200 || xhr.status === 204) {
            resolve();
          } else {
            reject(new Error(`Upload failed with status ${xhr.status}`));
          }
        });

        xhr.addEventListener("error", () => {
          reject(new Error("Network error during upload"));
        });

        xhr.open("PUT", upload_url);
        xhr.setRequestHeader("Content-Type", selectedFile.type);
        xhr.send(selectedFile);
      });

      // Step 3: Confirm upload
      setStatus("confirming");
      
      const confirmRes = await fetch(`${BACKEND_URL}/api/media/confirm`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          storage_key,
          file_type: fileType,
          filename: selectedFile.name,
          content_type: selectedFile.type,
          file_size_bytes: selectedFile.size,
          job_id: jobId || null
        })
      });

      if (!confirmRes.ok) {
        const err = await confirmRes.json();
        throw new Error(err.detail || "Failed to confirm upload");
      }

      const { media_id, public_url, asset } = await confirmRes.json();

      setStatus("complete");
      setUploadedAsset(asset);
      
      onUploadComplete?.({
        media_id,
        storage_key,
        public_url,
        filename: selectedFile.name,
        asset
      });

    } catch (err) {
      handleError(err.message);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      uploadFile(droppedFile);
    }
  };

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      uploadFile(selectedFile);
    }
  };

  const handleClick = () => {
    if (status === "idle" || status === "error") {
      fileInputRef.current?.click();
    }
  };

  const handleReset = () => {
    setFile(null);
    setStatus("idle");
    setProgress(0);
    setErrorMessage(null);
    setUploadedAsset(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="w-full">
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept={acceptTypes}
        onChange={handleFileSelect}
        className="hidden"
      />

      {/* Drop zone */}
      <div
        onClick={handleClick}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          relative border-2 border-dashed rounded-xl p-6 transition-all cursor-pointer
          ${isDragging 
            ? "border-lime bg-lime/5" 
            : status === "error" 
              ? "border-red-500/50 bg-red-500/5"
              : status === "complete"
                ? "border-lime/50 bg-lime/5"
                : "border-zinc-700 bg-zinc-900/50 hover:border-zinc-600 hover:bg-zinc-900"
          }
        `}
      >
        {/* Idle state */}
        {status === "idle" && (
          <div className="flex flex-col items-center justify-center text-center space-y-3">
            <div className="w-12 h-12 rounded-xl bg-zinc-800 flex items-center justify-center">
              <FileIcon className="text-zinc-400" size={24} />
            </div>
            <div>
              <p className="text-white font-medium">{displayLabel}</p>
              <p className="text-zinc-500 text-sm mt-1">
                Drag & drop or click to browse
              </p>
              <p className="text-zinc-600 text-xs mt-1">
                Max size: {maxSize}MB
              </p>
            </div>
          </div>
        )}

        {/* Uploading state */}
        {(status === "uploading" || status === "confirming") && (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <Loader2 className="text-lime animate-spin" size={20} />
              <div className="flex-1 min-w-0">
                <p className="text-white text-sm font-medium truncate">
                  {file?.name}
                </p>
                <p className="text-zinc-500 text-xs">
                  {status === "confirming" ? "Confirming..." : `${progress}%`}
                </p>
              </div>
              <span className="text-zinc-500 text-xs">
                {formatFileSize(file?.size || 0)}
              </span>
            </div>
            
            {/* Progress bar */}
            <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
              <div 
                className="h-full bg-lime transition-all duration-300 rounded-full"
                style={{ width: status === "confirming" ? "100%" : `${progress}%` }}
              />
            </div>
          </div>
        )}

        {/* Complete state */}
        {status === "complete" && uploadedAsset && (
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-lime/20 flex items-center justify-center">
                <CheckCircle className="text-lime" size={20} />
              </div>
              <div>
                <p className="text-white text-sm font-medium truncate max-w-[200px]">
                  {uploadedAsset.filename}
                </p>
                <p className="text-lime text-xs">
                  Upload complete
                </p>
              </div>
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleReset();
              }}
              className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-lg transition-colors"
            >
              <X size={16} />
            </button>
          </div>
        )}

        {/* Error state */}
        {status === "error" && (
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-red-500/20 flex items-center justify-center">
                <AlertCircle className="text-red-400" size={20} />
              </div>
              <div>
                <p className="text-white text-sm font-medium">Upload failed</p>
                <p className="text-red-400 text-xs max-w-[250px] truncate">
                  {errorMessage}
                </p>
              </div>
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleReset();
              }}
              className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-lg transition-colors"
            >
              <X size={16} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
