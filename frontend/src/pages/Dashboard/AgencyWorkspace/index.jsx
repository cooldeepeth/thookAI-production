import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Building2, Users, Plus, Mail, Shield, Crown, 
  UserPlus, Settings, Trash2, Eye, Calendar, 
  FileText, ChevronRight, Check, X, AlertCircle,
  Loader2
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const ROLE_BADGES = {
  owner: { label: "Owner", color: "bg-lime text-black" },
  admin: { label: "Admin", color: "bg-violet text-white" },
  manager: { label: "Manager", color: "bg-cyan-500 text-white" },
  creator: { label: "Creator", color: "bg-white/10 text-zinc-300" },
};

function WorkspaceCard({ workspace, onSelect, isSelected }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      onClick={() => onSelect(workspace)}
      className={`p-4 rounded-xl border cursor-pointer transition-all ${
        isSelected 
          ? "bg-lime/10 border-lime/30" 
          : "bg-white/5 border-white/10 hover:border-white/20"
      }`}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
            isSelected ? "bg-lime/20" : "bg-white/10"
          }`}>
            <Building2 size={20} className={isSelected ? "text-lime" : "text-zinc-400"} />
          </div>
          <div>
            <h3 className="font-semibold text-white">{workspace.name}</h3>
            <p className="text-xs text-zinc-500">{workspace.member_count} members</p>
          </div>
        </div>
        <span className={`text-xs px-2 py-1 rounded-full ${ROLE_BADGES[workspace.role]?.color || ROLE_BADGES.creator.color}`}>
          {ROLE_BADGES[workspace.role]?.label || workspace.role}
        </span>
      </div>
      {workspace.description && (
        <p className="text-sm text-zinc-500 line-clamp-2">{workspace.description}</p>
      )}
    </motion.div>
  );
}

function CreatorRow({ creator }) {
  return (
    <div className="flex items-center justify-between p-4 bg-white/5 rounded-xl">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-violet/20 flex items-center justify-center overflow-hidden">
          {creator.picture ? (
            <img src={creator.picture} alt="" className="w-full h-full object-cover" />
          ) : (
            <span className="text-violet font-semibold">{creator.name?.[0]?.toUpperCase() || "?"}</span>
          )}
        </div>
        <div>
          <p className="text-white font-medium">{creator.name || "Unknown"}</p>
          <p className="text-xs text-zinc-500">{creator.email}</p>
        </div>
      </div>
      
      <div className="flex items-center gap-6">
        {/* Persona status */}
        <div className="text-right">
          <p className="text-xs text-zinc-500">Persona</p>
          {creator.persona?.has_persona ? (
            <p className="text-sm text-lime">{creator.persona.archetype}</p>
          ) : (
            <p className="text-sm text-zinc-600">Not set up</p>
          )}
        </div>
        
        {/* Content stats */}
        <div className="text-right">
          <p className="text-xs text-zinc-500">Content</p>
          <p className="text-sm text-white">{creator.stats?.total_content || 0} posts</p>
        </div>
        
        {/* Last active */}
        <div className="text-right min-w-[80px]">
          <p className="text-xs text-zinc-500">Last active</p>
          <p className="text-sm text-zinc-400">
            {creator.stats?.last_content_date 
              ? new Date(creator.stats.last_content_date).toLocaleDateString()
              : "Never"
            }
          </p>
        </div>
        
        {/* Role badge */}
        <span className={`text-xs px-2 py-1 rounded-full ${ROLE_BADGES[creator.role]?.color || ROLE_BADGES.creator.color}`}>
          {ROLE_BADGES[creator.role]?.label || creator.role}
        </span>
      </div>
    </div>
  );
}

function InviteModal({ workspace, onClose, onSuccess }) {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("creator");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleInvite = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    
    try {
      const res = await fetch(`${BACKEND_URL}/api/agency/workspace/${workspace.workspace_id}/invite`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email, role }),
      });
      
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to send invite");
      
      onSuccess(data);
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        className="bg-[#0F0F0F] border border-white/10 rounded-2xl p-6 max-w-md w-full"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-violet/10 rounded-xl flex items-center justify-center">
            <UserPlus size={20} className="text-violet" />
          </div>
          <div>
            <h3 className="font-display font-bold text-white">Invite Creator</h3>
            <p className="text-zinc-500 text-xs">Add a team member to {workspace.name}</p>
          </div>
        </div>
        
        <form onSubmit={handleInvite} className="space-y-4">
          <div>
            <label className="text-xs text-zinc-500 mb-1 block">Email Address</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="creator@example.com"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-zinc-600 outline-none focus:border-violet/50"
              required
            />
          </div>
          
          <div>
            <label className="text-xs text-zinc-500 mb-1 block">Role</label>
            <select
              value={role}
              onChange={e => setRole(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white outline-none focus:border-violet/50"
            >
              <option value="creator">Creator</option>
              <option value="manager">Manager</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          
          {error && (
            <div className="flex items-center gap-2 text-red-400 text-sm">
              <AlertCircle size={14} />
              {error}
            </div>
          )}
          
          <div className="flex gap-2 pt-2">
            <button type="button" onClick={onClose} className="flex-1 btn-ghost py-2">
              Cancel
            </button>
            <button 
              type="submit" 
              disabled={loading}
              className="flex-1 btn-primary py-2 flex items-center justify-center gap-2"
            >
              {loading ? <Loader2 size={16} className="animate-spin" /> : <Mail size={16} />}
              Send Invite
            </button>
          </div>
        </form>
      </motion.div>
    </motion.div>
  );
}

function CreateWorkspaceModal({ onClose, onSuccess }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleCreate = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    
    try {
      const res = await fetch(`${BACKEND_URL}/api/agency/workspace`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ name, description }),
      });
      
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to create workspace");
      
      onSuccess(data);
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        className="bg-[#0F0F0F] border border-white/10 rounded-2xl p-6 max-w-md w-full"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-lime/10 rounded-xl flex items-center justify-center">
            <Building2 size={20} className="text-lime" />
          </div>
          <div>
            <h3 className="font-display font-bold text-white">Create Workspace</h3>
            <p className="text-zinc-500 text-xs">Set up a new agency workspace</p>
          </div>
        </div>
        
        <form onSubmit={handleCreate} className="space-y-4">
          <div>
            <label className="text-xs text-zinc-500 mb-1 block">Workspace Name</label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="My Agency"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-zinc-600 outline-none focus:border-lime/50"
              required
            />
          </div>
          
          <div>
            <label className="text-xs text-zinc-500 mb-1 block">Description (optional)</label>
            <textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="What's this workspace for?"
              rows={3}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-zinc-600 outline-none focus:border-lime/50 resize-none"
            />
          </div>
          
          {error && (
            <div className="flex items-center gap-2 text-red-400 text-sm">
              <AlertCircle size={14} />
              {error}
            </div>
          )}
          
          <div className="flex gap-2 pt-2">
            <button type="button" onClick={onClose} className="flex-1 btn-ghost py-2">
              Cancel
            </button>
            <button 
              type="submit" 
              disabled={loading}
              className="flex-1 btn-primary py-2 flex items-center justify-center gap-2"
            >
              {loading ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />}
              Create Workspace
            </button>
          </div>
        </form>
      </motion.div>
    </motion.div>
  );
}

export default function AgencyWorkspace() {
  const { user } = useAuth();
  const [workspaces, setWorkspaces] = useState({ owned: [], member_of: [] });
  const [selectedWorkspace, setSelectedWorkspace] = useState(null);
  const [creators, setCreators] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creatorsLoading, setCreatorsLoading] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [tierError, setTierError] = useState(null);

  // Fetch workspaces
  useEffect(() => {
    const fetchWorkspaces = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/api/agency/workspaces`, { credentials: "include" });
        const data = await res.json();
        
        if (res.status === 403) {
          setTierError(data.detail);
        } else if (data.success) {
          setWorkspaces(data);
          // Auto-select first workspace
          const allWorkspaces = [...(data.owned || []), ...(data.member_of || [])];
          if (allWorkspaces.length > 0 && !selectedWorkspace) {
            setSelectedWorkspace(allWorkspaces[0]);
          }
        }
      } catch (err) {
        console.error("Failed to fetch workspaces:", err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchWorkspaces();
  }, []);

  // Fetch creators when workspace selected
  useEffect(() => {
    if (!selectedWorkspace) return;
    
    const fetchCreators = async () => {
      setCreatorsLoading(true);
      try {
        const res = await fetch(
          `${BACKEND_URL}/api/agency/workspace/${selectedWorkspace.workspace_id}/creators`,
          { credentials: "include" }
        );
        const data = await res.json();
        if (data.success) {
          setCreators(data.creators || []);
        }
      } catch (err) {
        console.error("Failed to fetch creators:", err);
      } finally {
        setCreatorsLoading(false);
      }
    };
    
    fetchCreators();
  }, [selectedWorkspace]);

  const handleWorkspaceCreated = (data) => {
    setWorkspaces(prev => ({
      ...prev,
      owned: [...prev.owned, { ...data, role: "owner", member_count: 1 }]
    }));
  };

  const handleInviteSent = () => {
    // Could refresh members list here
  };

  const allWorkspaces = [...(workspaces.owned || []), ...(workspaces.member_of || [])];
  const userTier = user?.subscription_tier || "free";
  const canCreateWorkspace = ["studio", "agency"].includes(userTier);

  if (loading) {
    return (
      <main className="flex-1 flex items-center justify-center p-6">
        <div className="w-6 h-6 border-2 border-lime border-t-transparent rounded-full animate-spin" />
      </main>
    );
  }

  // Show upgrade prompt for non-agency tiers
  if (!canCreateWorkspace && allWorkspaces.length === 0) {
    return (
      <main className="flex-1 p-6" data-testid="agency-workspace-page">
        <div className="max-w-2xl mx-auto text-center py-16">
          <div className="w-20 h-20 bg-violet/10 rounded-2xl flex items-center justify-center mx-auto mb-6">
            <Building2 size={40} className="text-violet" />
          </div>
          <h2 className="font-display font-bold text-3xl text-white mb-3">Agency Workspace</h2>
          <p className="text-zinc-500 mb-8 max-w-md mx-auto">
            Manage multiple creator accounts, view unified content feeds, and collaborate with your team.
          </p>
          
          <div className="bg-white/5 border border-white/10 rounded-2xl p-6 mb-6">
            <div className="flex items-center justify-center gap-2 mb-4">
              <Crown size={20} className="text-yellow-400" />
              <span className="font-semibold text-white">Requires Studio or Agency Tier</span>
            </div>
            <p className="text-sm text-zinc-500 mb-4">
              Upgrade your subscription to unlock agency features including multi-creator management,
              unified content feeds, and team collaboration tools.
            </p>
            <a href="/dashboard/settings" className="btn-primary inline-flex items-center gap-2">
              View Plans <ChevronRight size={16} />
            </a>
          </div>
          
          <p className="text-xs text-zinc-600">
            Current tier: <span className="text-zinc-400 capitalize">{userTier}</span>
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="flex-1 p-6" data-testid="agency-workspace-page">
      {/* Modals */}
      <AnimatePresence>
        {showCreateModal && (
          <CreateWorkspaceModal 
            onClose={() => setShowCreateModal(false)}
            onSuccess={handleWorkspaceCreated}
          />
        )}
        {showInviteModal && selectedWorkspace && (
          <InviteModal
            workspace={selectedWorkspace}
            onClose={() => setShowInviteModal(false)}
            onSuccess={handleInviteSent}
          />
        )}
      </AnimatePresence>

      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="font-display font-bold text-2xl text-white">Agency Workspace</h2>
          <p className="text-zinc-500 text-sm">Manage your creators and content across workspaces</p>
        </div>
        {canCreateWorkspace && (
          <button
            onClick={() => setShowCreateModal(true)}
            className="btn-primary flex items-center gap-2"
          >
            <Plus size={16} /> New Workspace
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Workspace List */}
        <div className="lg:col-span-1 space-y-3">
          <h3 className="text-xs text-zinc-500 uppercase tracking-wider mb-2">Workspaces</h3>
          {allWorkspaces.length === 0 ? (
            <div className="text-center py-8 text-zinc-600 text-sm">
              No workspaces yet
            </div>
          ) : (
            allWorkspaces.map(ws => (
              <WorkspaceCard
                key={ws.workspace_id}
                workspace={ws}
                onSelect={setSelectedWorkspace}
                isSelected={selectedWorkspace?.workspace_id === ws.workspace_id}
              />
            ))
          )}
        </div>

        {/* Main Content */}
        <div className="lg:col-span-3">
          {selectedWorkspace ? (
            <div className="space-y-6">
              {/* Workspace header */}
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-display font-bold text-xl text-white">{selectedWorkspace.name}</h3>
                  {selectedWorkspace.description && (
                    <p className="text-zinc-500 text-sm">{selectedWorkspace.description}</p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setShowInviteModal(true)}
                    className="btn-ghost flex items-center gap-2 text-sm"
                  >
                    <UserPlus size={16} /> Invite
                  </button>
                </div>
              </div>

              {/* Stats */}
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-white/5 rounded-xl p-4">
                  <div className="flex items-center gap-2 mb-1">
                    <Users size={16} className="text-violet" />
                    <span className="text-xs text-zinc-500">Members</span>
                  </div>
                  <p className="text-2xl font-bold text-white">{selectedWorkspace.member_count || 1}</p>
                </div>
                <div className="bg-white/5 rounded-xl p-4">
                  <div className="flex items-center gap-2 mb-1">
                    <FileText size={16} className="text-cyan-400" />
                    <span className="text-xs text-zinc-500">Total Content</span>
                  </div>
                  <p className="text-2xl font-bold text-white">{selectedWorkspace.content_count || 0}</p>
                </div>
                <div className="bg-white/5 rounded-xl p-4">
                  <div className="flex items-center gap-2 mb-1">
                    <Calendar size={16} className="text-lime" />
                    <span className="text-xs text-zinc-500">Created</span>
                  </div>
                  <p className="text-sm text-white">
                    {new Date(selectedWorkspace.created_at).toLocaleDateString()}
                  </p>
                </div>
              </div>

              {/* Creators list */}
              <div>
                <h4 className="text-sm font-semibold text-white mb-3">Team Members</h4>
                {creatorsLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 size={24} className="animate-spin text-zinc-500" />
                  </div>
                ) : creators.length === 0 ? (
                  <div className="text-center py-8 bg-white/5 rounded-xl">
                    <Users size={32} className="text-zinc-700 mx-auto mb-2" />
                    <p className="text-zinc-600 text-sm">No team members yet</p>
                    <button
                      onClick={() => setShowInviteModal(true)}
                      className="text-violet text-sm mt-2 hover:underline"
                    >
                      Invite your first creator
                    </button>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {creators.map(creator => (
                      <CreatorRow key={creator.user_id} creator={creator} />
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-64 text-zinc-600">
              Select a workspace to view details
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
