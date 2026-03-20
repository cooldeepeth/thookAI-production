import { createContext, useContext, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, XCircle, AlertCircle, Info, X } from 'lucide-react';

const ToastContext = createContext(null);

const TOAST_ICONS = {
  success: { icon: CheckCircle2, color: 'text-green-400', bg: 'bg-green-400/10', border: 'border-green-400/20' },
  error: { icon: XCircle, color: 'text-red-400', bg: 'bg-red-400/10', border: 'border-red-400/20' },
  warning: { icon: AlertCircle, color: 'text-yellow-400', bg: 'bg-yellow-400/10', border: 'border-yellow-400/20' },
  info: { icon: Info, color: 'text-blue-400', bg: 'bg-blue-400/10', border: 'border-blue-400/20' },
};

function Toast({ id, type = 'info', title, message, onClose }) {
  const config = TOAST_ICONS[type] || TOAST_ICONS.info;
  const Icon = config.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 10, scale: 0.95 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
      className={`flex items-start gap-3 p-4 rounded-xl border ${config.border} ${config.bg} backdrop-blur-sm shadow-modal min-w-[320px] max-w-[420px]`}
    >
      <div className={`flex-shrink-0 ${config.color}`}>
        <Icon size={20} />
      </div>
      <div className="flex-1 min-w-0">
        {title && (
          <p className="text-sm font-semibold text-white mb-0.5">{title}</p>
        )}
        {message && (
          <p className="text-sm text-zinc-400">{message}</p>
        )}
      </div>
      <button
        onClick={() => onClose(id)}
        className="flex-shrink-0 text-zinc-500 hover:text-white transition-colors"
      >
        <X size={16} />
      </button>
    </motion.div>
  );
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback(({ type = 'info', title, message, duration = 5000 }) => {
    const id = Date.now().toString();
    setToasts(prev => [...prev, { id, type, title, message }]);

    if (duration > 0) {
      setTimeout(() => {
        setToasts(prev => prev.filter(t => t.id !== id));
      }, duration);
    }

    return id;
  }, []);

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const toast = {
    success: (title, message) => addToast({ type: 'success', title, message }),
    error: (title, message) => addToast({ type: 'error', title, message }),
    warning: (title, message) => addToast({ type: 'warning', title, message }),
    info: (title, message) => addToast({ type: 'info', title, message }),
    custom: addToast,
    dismiss: removeToast,
  };

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <div className="fixed bottom-6 right-6 z-[9999] flex flex-col gap-3">
        <AnimatePresence mode="popLayout">
          {toasts.map(t => (
            <Toast key={t.id} {...t} onClose={removeToast} />
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within ToastProvider');
  }
  return context;
}

// ============ LOADING COMPONENTS ============

export function Spinner({ size = 'md', className = '' }) {
  const sizes = {
    sm: 'w-4 h-4 border-2',
    md: 'w-6 h-6 border-2',
    lg: 'w-8 h-8 border-3',
    xl: 'w-12 h-12 border-3',
  };

  return (
    <div
      className={`${sizes[size]} border-lime border-t-transparent rounded-full animate-spin ${className}`}
    />
  );
}

export function LoadingDots({ className = '' }) {
  return (
    <div className={`flex items-center gap-1 ${className}`}>
      {[0, 1, 2].map(i => (
        <motion.div
          key={i}
          className="w-1.5 h-1.5 bg-lime rounded-full"
          animate={{ opacity: [0.3, 1, 0.3] }}
          transition={{ duration: 1, repeat: Infinity, delay: i * 0.2 }}
        />
      ))}
    </div>
  );
}

export function Skeleton({ className = '', animate = true }) {
  return (
    <div
      className={`bg-zinc-800 rounded ${animate ? 'animate-pulse' : ''} ${className}`}
    />
  );
}

export function SkeletonCard() {
  return (
    <div className="card-thook p-4 space-y-3">
      <div className="flex items-center gap-3">
        <Skeleton className="w-10 h-10 rounded-xl" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-3 w-1/2" />
        </div>
      </div>
      <Skeleton className="h-20 w-full" />
      <div className="flex gap-2">
        <Skeleton className="h-8 w-20 rounded-full" />
        <Skeleton className="h-8 w-24 rounded-full" />
      </div>
    </div>
  );
}

// ============ PROGRESS COMPONENTS ============

export function ProgressBar({ value, max = 100, showLabel = false, color = 'lime' }) {
  const percentage = Math.min((value / max) * 100, 100);
  
  const colors = {
    lime: 'bg-lime',
    violet: 'bg-violet',
    gradient: 'bg-gradient-to-r from-lime to-violet',
  };

  return (
    <div className="w-full">
      <div className="progress-bar">
        <motion.div
          className={`progress-bar-fill ${colors[color] || colors.lime}`}
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
        />
      </div>
      {showLabel && (
        <p className="text-xs text-zinc-500 mt-1">{Math.round(percentage)}%</p>
      )}
    </div>
  );
}

export function CircularProgress({ value, max = 100, size = 48, strokeWidth = 4 }) {
  const percentage = Math.min((value / max) * 100, 100);
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (percentage / 100) * circumference;

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg className="transform -rotate-90" width={size} height={size}>
        <circle
          className="text-zinc-800"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          fill="none"
          r={radius}
          cx={size / 2}
          cy={size / 2}
        />
        <motion.circle
          className="text-lime"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          fill="none"
          r={radius}
          cx={size / 2}
          cy={size / 2}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          style={{
            strokeDasharray: circumference,
          }}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-xs font-mono text-white">{Math.round(percentage)}</span>
      </div>
    </div>
  );
}

// ============ EMPTY STATE ============

export function EmptyState({ 
  icon: Icon, 
  title, 
  description, 
  action,
  actionLabel,
  className = '' 
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`text-center py-12 px-6 ${className}`}
    >
      {Icon && (
        <div className="w-16 h-16 bg-white/5 rounded-2xl flex items-center justify-center mx-auto mb-4">
          <Icon size={28} className="text-zinc-600" />
        </div>
      )}
      <h3 className="text-lg font-semibold text-white mb-2">{title}</h3>
      {description && (
        <p className="text-sm text-zinc-500 max-w-sm mx-auto mb-6">{description}</p>
      )}
      {action && actionLabel && (
        <button onClick={action} className="btn-primary text-sm">
          {actionLabel}
        </button>
      )}
    </motion.div>
  );
}

// ============ BADGE ============

export function Badge({ children, variant = 'default', size = 'sm', className = '' }) {
  const variants = {
    default: 'bg-white/5 text-zinc-400 border-white/10',
    lime: 'bg-lime/10 text-lime border-lime/20',
    violet: 'bg-violet/10 text-violet border-violet/20',
    success: 'bg-green-400/10 text-green-400 border-green-400/20',
    warning: 'bg-yellow-400/10 text-yellow-400 border-yellow-400/20',
    error: 'bg-red-400/10 text-red-400 border-red-400/20',
  };

  const sizes = {
    sm: 'text-xs px-2 py-0.5',
    md: 'text-sm px-2.5 py-1',
  };

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border font-medium ${variants[variant]} ${sizes[size]} ${className}`}
    >
      {children}
    </span>
  );
}

// ============ TOOLTIP ============

export function Tooltip({ children, content, position = 'top' }) {
  const positions = {
    top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
    left: 'right-full top-1/2 -translate-y-1/2 mr-2',
    right: 'left-full top-1/2 -translate-y-1/2 ml-2',
  };

  return (
    <div className="relative group">
      {children}
      <div
        className={`absolute ${positions[position]} px-2 py-1 bg-zinc-800 text-white text-xs rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50`}
      >
        {content}
      </div>
    </div>
  );
}

// ============ CONFIRMATION MODAL ============

export function ConfirmModal({ 
  isOpen, 
  onClose, 
  onConfirm, 
  title, 
  message, 
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'danger' 
}) {
  if (!isOpen) return null;

  const variants = {
    danger: 'bg-red-500 hover:bg-red-600',
    warning: 'bg-yellow-500 hover:bg-yellow-600 text-black',
    primary: 'bg-lime hover:bg-lime/90 text-black',
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          className="bg-[#0F0F0F] border border-white/10 rounded-2xl p-6 max-w-md w-full shadow-modal"
          onClick={e => e.stopPropagation()}
        >
          <h3 className="font-display font-bold text-xl text-white mb-2">{title}</h3>
          <p className="text-zinc-400 text-sm mb-6">{message}</p>
          <div className="flex gap-3">
            <button onClick={onClose} className="flex-1 btn-ghost py-2.5">
              {cancelLabel}
            </button>
            <button
              onClick={() => { onConfirm(); onClose(); }}
              className={`flex-1 py-2.5 rounded-full font-semibold transition-colors ${variants[variant]}`}
            >
              {confirmLabel}
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
