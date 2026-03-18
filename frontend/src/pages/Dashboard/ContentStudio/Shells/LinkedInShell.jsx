import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { MoreHorizontal, Image, Calendar, Smile, Globe2 } from "lucide-react";

const MAX_CHARS = 3000;
const WARNING_THRESHOLD = 2700;

export default function LinkedInShell({ content, onContentChange, isEditing, readOnly = false }) {
  const [text, setText] = useState(content || "");
  
  useEffect(() => {
    setText(content || "");
  }, [content]);

  const handleChange = (e) => {
    const newText = e.target.value;
    if (newText.length <= MAX_CHARS) {
      setText(newText);
      onContentChange?.(newText);
    }
  };

  const charCount = text.length;
  const isOverWarning = charCount >= WARNING_THRESHOLD;
  const isAtLimit = charCount >= MAX_CHARS;

  // Highlight hashtags and mentions
  const renderHighlightedText = (text) => {
    if (!text) return null;
    const parts = text.split(/(#\w+|@\w+)/g);
    return parts.map((part, i) => {
      if (part.startsWith('#')) {
        return <span key={i} className="text-[#0A66C2] font-medium">{part}</span>;
      }
      if (part.startsWith('@')) {
        return <span key={i} className="text-[#0A66C2] font-medium">{part}</span>;
      }
      return <span key={i}>{part}</span>;
    });
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-lg shadow-lg overflow-hidden max-w-[555px] mx-auto"
      data-testid="linkedin-shell"
    >
      {/* LinkedIn Header */}
      <div className="p-4 border-b border-gray-100">
        <div className="flex items-start gap-3">
          {/* Avatar */}
          <div className="w-12 h-12 rounded-full bg-gradient-to-br from-[#0A66C2] to-[#004182] flex items-center justify-center text-white font-bold text-lg">
            TC
          </div>
          
          {/* User Info */}
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-gray-900 text-sm">Test Creator</span>
              <span className="text-[10px] bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">• 1st</span>
            </div>
            <p className="text-xs text-gray-500 mt-0.5">Content Creator | Building in Public</p>
            <div className="flex items-center gap-1 mt-1">
              <span className="text-[11px] text-gray-400">Just now</span>
              <span className="text-gray-300">•</span>
              <Globe2 size={12} className="text-gray-400" />
            </div>
          </div>
          
          {/* More Button */}
          <button className="p-1.5 hover:bg-gray-100 rounded-full transition-colors">
            <MoreHorizontal size={18} className="text-gray-500" />
          </button>
        </div>
      </div>

      {/* Content Area */}
      <div className="px-4 py-3">
        {isEditing && !readOnly ? (
          <textarea
            value={text}
            onChange={handleChange}
            className="w-full min-h-[200px] text-sm text-gray-800 bg-transparent outline-none resize-none leading-relaxed placeholder:text-gray-400"
            placeholder="What do you want to talk about?"
            autoFocus
          />
        ) : (
          <div className="text-sm text-gray-800 leading-relaxed whitespace-pre-wrap min-h-[100px]">
            {renderHighlightedText(text)}
          </div>
        )}
      </div>

      {/* Character Counter */}
      <div className="px-4 pb-2">
        <div className="flex items-center justify-between">
          <span className={`text-xs font-mono ${
            isAtLimit ? 'text-red-500 font-bold' : 
            isOverWarning ? 'text-yellow-600' : 
            'text-gray-400'
          }`}>
            {charCount.toLocaleString()} / {MAX_CHARS.toLocaleString()}
          </span>
          {isOverWarning && !isAtLimit && (
            <span className="text-[10px] text-yellow-600">Approaching limit</span>
          )}
          {isAtLimit && (
            <span className="text-[10px] text-red-500">Character limit reached</span>
          )}
        </div>
      </div>

      {/* Attachment Bar */}
      <div className="px-4 py-3 border-t border-gray-100 flex items-center gap-1">
        <button className="p-2 hover:bg-gray-100 rounded-lg transition-colors flex items-center gap-2 text-gray-600">
          <Image size={18} />
          <span className="text-xs">Photo</span>
        </button>
        <button className="p-2 hover:bg-gray-100 rounded-lg transition-colors flex items-center gap-2 text-gray-600">
          <Calendar size={18} />
          <span className="text-xs">Event</span>
        </button>
        <button className="p-2 hover:bg-gray-100 rounded-lg transition-colors flex items-center gap-2 text-gray-600">
          <Smile size={18} />
          <span className="text-xs">Celebrate</span>
        </button>
      </div>

      {/* Post Button */}
      {!readOnly && (
        <div className="px-4 pb-4">
          <div className="flex items-center justify-between pt-3 border-t border-gray-100">
            <div className="flex items-center gap-2">
              <Globe2 size={14} className="text-gray-500" />
              <span className="text-xs text-gray-500">Anyone</span>
            </div>
            <button
              className="px-5 py-2 bg-[#D4FF00] text-black text-sm font-semibold rounded-full hover:bg-[#c4ef00] transition-colors"
              onClick={() => onContentChange?.(text)}
            >
              Post
            </button>
          </div>
        </div>
      )}
    </motion.div>
  );
}
