import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Heart, MessageCircle, Send, Bookmark, MoreHorizontal, Image as ImageIcon } from "lucide-react";

const MAX_CHARS = 2200;
const RECOMMENDED_HASHTAGS_MIN = 10;
const RECOMMENDED_HASHTAGS_MAX = 15;

export default function InstagramShell({ content, onContentChange, isEditing, readOnly = false }) {
  const [caption, setCaption] = useState(content || "");
  const [hashtags, setHashtags] = useState([]);
  
  useEffect(() => {
    setCaption(content || "");
    // Extract hashtags from content
    const hashtagMatches = (content || "").match(/#\w+/g) || [];
    setHashtags(hashtagMatches);
  }, [content]);

  const handleChange = (e) => {
    const newText = e.target.value;
    if (newText.length <= MAX_CHARS) {
      setCaption(newText);
      onContentChange?.(newText);
      // Update hashtag extraction
      const newHashtags = newText.match(/#\w+/g) || [];
      setHashtags(newHashtags);
    }
  };

  const charCount = caption.length;
  const hashtagCount = hashtags.length;
  const isHashtagsGood = hashtagCount >= RECOMMENDED_HASHTAGS_MIN && hashtagCount <= RECOMMENDED_HASHTAGS_MAX;
  const isHashtagsLow = hashtagCount < RECOMMENDED_HASHTAGS_MIN;

  // Render caption with highlighted hashtags
  const renderCaption = (text) => {
    if (!text) return null;
    const parts = text.split(/(#\w+|@\w+)/g);
    return parts.map((part, i) => {
      if (part.startsWith('#') || part.startsWith('@')) {
        return <span key={i} className="text-[#00376B]">{part}</span>;
      }
      return <span key={i}>{part}</span>;
    });
  };

  // Suggest common hashtags based on content
  const suggestedHashtags = ['#content', '#creator', '#marketing', '#business', '#growth', '#mindset', '#success', '#entrepreneurship', '#motivation', '#leadership'];
  const unusedSuggestions = suggestedHashtags.filter(h => !hashtags.includes(h)).slice(0, 5);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-lg shadow-lg overflow-hidden max-w-[470px] mx-auto"
      data-testid="instagram-shell"
    >
      {/* Instagram Header */}
      <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {/* Avatar with gradient ring */}
          <div className="p-0.5 rounded-full bg-gradient-to-br from-[#FCAF45] via-[#E1306C] to-[#5B51D8]">
            <div className="w-8 h-8 rounded-full bg-white p-0.5">
              <div className="w-full h-full rounded-full bg-gradient-to-br from-[#E1306C] to-[#5B51D8] flex items-center justify-center text-white font-bold text-xs">
                TC
              </div>
            </div>
          </div>
          <div>
            <span className="font-semibold text-sm text-gray-900">testcreator</span>
            <p className="text-[11px] text-gray-500">Original Audio</p>
          </div>
        </div>
        <button className="p-1">
          <MoreHorizontal size={20} className="text-gray-900" />
        </button>
      </div>

      {/* Image Placeholder */}
      <div className="aspect-square bg-gradient-to-br from-gray-100 to-gray-200 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 rounded-full bg-gray-300 flex items-center justify-center mx-auto mb-3">
            <ImageIcon size={28} className="text-gray-500" />
          </div>
          <p className="text-sm text-gray-500">Image/Video Preview</p>
          <p className="text-xs text-gray-400 mt-1">Your visual content here</p>
        </div>
      </div>

      {/* Action Bar */}
      <div className="px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button className="hover:opacity-60 transition-opacity">
            <Heart size={24} className="text-gray-900" />
          </button>
          <button className="hover:opacity-60 transition-opacity">
            <MessageCircle size={24} className="text-gray-900" />
          </button>
          <button className="hover:opacity-60 transition-opacity">
            <Send size={24} className="text-gray-900" />
          </button>
        </div>
        <button className="hover:opacity-60 transition-opacity">
          <Bookmark size={24} className="text-gray-900" />
        </button>
      </div>

      {/* Likes */}
      <div className="px-4 pb-2">
        <p className="text-sm font-semibold text-gray-900">1,234 likes</p>
      </div>

      {/* Caption Area */}
      <div className="px-4 pb-3">
        {isEditing && !readOnly ? (
          <div>
            <div className="flex items-start gap-1">
              <span className="font-semibold text-sm text-gray-900">testcreator</span>
              <textarea
                value={caption}
                onChange={handleChange}
                className="flex-1 text-sm text-gray-900 bg-transparent outline-none resize-none leading-relaxed placeholder:text-gray-400 min-h-[100px]"
                placeholder="Write a caption..."
                autoFocus
              />
            </div>
          </div>
        ) : (
          <div className="text-sm text-gray-900 leading-relaxed">
            <span className="font-semibold mr-1">testcreator</span>
            <span className="whitespace-pre-wrap">{renderCaption(caption)}</span>
          </div>
        )}
      </div>

      {/* Character & Hashtag Counter */}
      <div className="px-4 pb-3 space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className={charCount >= MAX_CHARS ? 'text-red-500' : 'text-gray-400'}>
            {charCount.toLocaleString()} / {MAX_CHARS.toLocaleString()} characters
          </span>
        </div>
        
        {/* Hashtag Indicator */}
        <div className="flex items-center gap-2">
          <span className={`text-xs font-medium ${
            isHashtagsGood ? 'text-green-600' : 
            isHashtagsLow ? 'text-yellow-600' : 
            'text-gray-500'
          }`}>
            {hashtagCount} hashtags
          </span>
          <span className="text-[10px] text-gray-400">
            (Recommended: {RECOMMENDED_HASHTAGS_MIN}-{RECOMMENDED_HASHTAGS_MAX})
          </span>
          {isHashtagsGood && (
            <span className="text-[10px] text-green-600">✓ Perfect!</span>
          )}
        </div>

        {/* Hashtag Chips */}
        {hashtags.length > 0 && (
          <div className="flex flex-wrap gap-1 pt-1">
            {hashtags.slice(0, 10).map((tag, i) => (
              <span
                key={i}
                className="text-[10px] bg-gray-100 text-[#00376B] px-2 py-0.5 rounded-full"
              >
                {tag}
              </span>
            ))}
            {hashtags.length > 10 && (
              <span className="text-[10px] text-gray-400 px-2 py-0.5">
                +{hashtags.length - 10} more
              </span>
            )}
          </div>
        )}

        {/* Hashtag Suggestions */}
        {isEditing && isHashtagsLow && unusedSuggestions.length > 0 && (
          <div className="pt-2 border-t border-gray-100">
            <p className="text-[10px] text-gray-500 mb-1.5">Suggested hashtags:</p>
            <div className="flex flex-wrap gap-1">
              {unusedSuggestions.map((tag, i) => (
                <button
                  key={i}
                  onClick={() => {
                    const newCaption = caption + (caption.endsWith(' ') || caption.endsWith('\n') ? '' : ' ') + tag;
                    if (newCaption.length <= MAX_CHARS) {
                      setCaption(newCaption);
                      onContentChange?.(newCaption);
                    }
                  }}
                  className="text-[10px] bg-[#E1306C]/10 text-[#E1306C] px-2 py-0.5 rounded-full hover:bg-[#E1306C]/20 transition-colors"
                >
                  + {tag}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Timestamp */}
      <div className="px-4 pb-3">
        <p className="text-[10px] text-gray-400 uppercase tracking-wide">Just now</p>
      </div>

      {/* Post Button */}
      {!readOnly && (
        <div className="px-4 pb-4 border-t border-gray-100 pt-3">
          <button
            className="w-full py-2.5 bg-[#D4FF00] text-black text-sm font-semibold rounded-lg hover:bg-[#c4ef00] transition-colors"
            onClick={() => onContentChange?.(caption)}
          >
            Share
          </button>
        </div>
      )}
    </motion.div>
  );
}
