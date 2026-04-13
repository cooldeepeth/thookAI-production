import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Download, AlertTriangle } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";

export function DataTab() {
  const [exporting, setExporting] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState("");
  const [deleting, setDeleting] = useState(false);
  const { toast } = useToast();
  const navigate = useNavigate();

  const handleExport = async () => {
    setExporting(true);
    try {
      const res = await apiFetch("/api/auth/export");
      if (!res.ok) {
        if (res.status === 429) {
          throw new Error("Export limit reached (3 per minute). Try again shortly.");
        }
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Export failed");
      }
      const data = await res.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `thookai-export-${Date.now()}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast({
        title: "Export complete",
        description: "Your data has been downloaded.",
      });
    } catch (err) {
      toast({
        title: "Export failed",
        description: err.message,
        variant: "destructive",
      });
    } finally {
      setExporting(false);
    }
  };

  const handleDelete = async () => {
    if (deleteConfirm !== "DELETE") return;
    setDeleting(true);
    try {
      const res = await apiFetch("/api/auth/delete-account", {
        method: "POST",
        body: JSON.stringify({ confirm: "DELETE" }),
        headers: { "Content-Type": "application/json" },
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Account deletion failed");
      }
      toast({
        title: "Account deleted",
        description: "Your account has been anonymized. Redirecting...",
        variant: "destructive",
      });
      setTimeout(() => navigate("/"), 2000);
    } catch (err) {
      toast({
        title: "Deletion failed",
        description: err.message,
        variant: "destructive",
      });
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="space-y-6" data-testid="data-tab">
      <div className="card-thook p-6">
        <h3 className="font-display font-semibold text-white text-lg mb-2 flex items-center gap-2">
          <Download size={18} className="text-lime" />
          Export Your Data
        </h3>
        <p className="text-sm text-zinc-400 mb-4 leading-relaxed">
          Download a JSON file containing all of your content, persona, scheduled posts,
          uploaded media, analytics, and billing history. Limited to the 500 most recent
          items per collection — contact support for full archives.
        </p>
        <button
          type="button"
          data-testid="export-data-btn"
          onClick={handleExport}
          disabled={exporting}
          className="btn-primary text-sm disabled:opacity-50 focus-ring"
        >
          {exporting ? "Exporting…" : "Export My Data"}
        </button>
      </div>

      <div className="card-thook p-6 border-red-500/20">
        <h3 className="font-display font-semibold text-red-400 text-lg mb-2 flex items-center gap-2">
          <AlertTriangle size={18} className="text-red-400" />
          Delete Account
        </h3>
        <p className="text-sm text-zinc-400 mb-4 leading-relaxed">
          Permanently anonymize your account. Your email and profile information will be
          removed from our database. Content you created may be retained in anonymized
          form for platform analytics. This action cannot be undone.
        </p>
        <div className="space-y-3">
          <label
            htmlFor="delete-confirm"
            className="block text-xs text-zinc-300 uppercase tracking-wider font-mono"
          >
            Type <span className="text-red-400">DELETE</span> to confirm
          </label>
          <input
            id="delete-confirm"
            data-testid="delete-confirm-input"
            type="text"
            value={deleteConfirm}
            onChange={(e) => setDeleteConfirm(e.target.value)}
            placeholder="DELETE"
            className="w-full max-w-xs bg-surface-2 border border-border-subtle rounded-lg px-3 py-2 text-sm text-white placeholder:text-zinc-600 outline-none focus:border-red-500/50 focus-ring"
          />
          <div>
            <button
              type="button"
              data-testid="delete-account-btn"
              onClick={handleDelete}
              disabled={deleteConfirm !== "DELETE" || deleting}
              className="btn-danger text-sm disabled:opacity-30 disabled:cursor-not-allowed focus-ring"
            >
              {deleting ? "Deleting…" : "Delete My Account"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
