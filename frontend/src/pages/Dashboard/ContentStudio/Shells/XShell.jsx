import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { MessageCircle, Repeat2, Heart, BarChart2, Share, MoreHorizontal, Verified } from "lucide-react";

const MAX_CHARS_PER_TWEET = 280;

export default function XShell({ content, onContentChange, isEditing, readOnly = false }) {
  const [tweets, setTweets] = useState([]);
  
  useEffect(() => {
    // Parse content into tweets (split by 1/, 2/, 3/, etc.)
    if (!content) {
      setTweets([""]);
      return;
    }
    
    const tweetPattern = /(?:^|\n)(?:\d+[\/\)]\s*)/g;
    const parts = content.split(tweetPattern).filter(t => t.trim());
    
    if (parts.length > 1) {
      setTweets(parts.map(p => p.trim()));
    } else {
      // Check if it's a thread format with numbered lines
      const lines = content.split('\n');
      const threadTweets = [];
      let currentTweet = '';
      
      for (const line of lines) {
        const match = line.match(/^(\d+)[\/\)]\s*(.*)/);
        if (match) {
          if (currentTweet) threadTweets.push(currentTweet.trim());
          currentTweet = match[2];
        } else {
          currentTweet += (currentTweet ? '\n' : '') + line;
        }
      }
      if (currentTweet) threadTweets.push(currentTweet.trim());
      
      setTweets(threadTweets.length > 1 ? threadTweets : [content]);
    }
  }, [content]);

  const handleTweetChange = (index, newText) => {
    if (newText.length > MAX_CHARS_PER_TWEET) return;
    const newTweets = [...tweets];
    newTweets[index] = newText;
    setTweets(newTweets);
    
    // Reconstruct full content
    if (newTweets.length > 1) {
      const fullContent = newTweets.map((t, i) => `${i + 1}/ ${t}`).join('\n\n');
      onContentChange?.(fullContent);
    } else {
      onContentChange?.(newTweets[0]);
    }
  };

  const addTweet = () => {
    setTweets([...tweets, ""]);
  };

  const CharCircle = ({ count, max }) => {
    const pct = (count / max) * 100;
    const radius = 10;
    const circumference = 2 * Math.PI * radius;
    const strokeDashoffset = circumference - (pct / 100) * circumference;
    const isWarning = count > max * 0.8;
    const isOver = count >= max;
    
    return (
      <div className="relative w-6 h-6">
        <svg className="w-6 h-6 -rotate-90">
          <circle
            cx="12"
            cy="12"
            r={radius}
            fill="none"
            stroke="#2F3336"
            strokeWidth="2"
          />
          <circle
            cx="12"
            cy="12"
            r={radius}
            fill="none"
            stroke={isOver ? '#F4212E' : isWarning ? '#FFD400' : '#1D9BF0'}
            strokeWidth="2"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
          />
        </svg>
        {isOver && (
          <span className="absolute inset-0 flex items-center justify-center text-[8px] text-red-500 font-bold">
            {max - count}
          </span>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-3 max-w-[598px] mx-auto" data-testid="x-shell">
      {tweets.map((tweet, index) => (
        <motion.div
          key={index}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.1 }}
          className="bg-black border border-[#2F3336] rounded-2xl overflow-hidden"
        >
          {/* Tweet Header */}
          <div className="p-4 pb-0">
            <div className="flex items-start gap-3">
              {/* Avatar */}
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#1D9BF0] to-[#0A66C2] flex items-center justify-center text-white font-bold text-sm flex-shrink-0">
                TC
              </div>
              
              {/* Content */}
              <div className="flex-1 min-w-0">
                {/* User Info */}
                <div className="flex items-center gap-1 mb-1">
                  <span className="font-bold text-white text-[15px]">Test Creator</span>
                  <Verified size={16} className="text-[#1D9BF0] fill-current" />
                  <span className="text-[#71767B] text-[15px]">@testcreator</span>
                  <span className="text-[#71767B] text-[15px]">·</span>
                  <span className="text-[#71767B] text-[15px]">now</span>
                  {tweets.length > 1 && (
                    <span className="ml-auto text-[#1D9BF0] text-xs font-medium">
                      {index + 1}/{tweets.length}
                    </span>
                  )}
                </div>
                
                {/* Tweet Content */}
                {isEditing && !readOnly ? (
                  <textarea
                    value={tweet}
                    onChange={(e) => handleTweetChange(index, e.target.value)}
                    className="w-full min-h-[80px] text-[15px] text-white bg-transparent outline-none resize-none leading-relaxed placeholder:text-[#71767B]"
                    placeholder="What's happening?"
                    autoFocus={index === 0}
                  />
                ) : (
                  <div className="text-[15px] text-white leading-relaxed whitespace-pre-wrap">
                    {tweet}
                  </div>
                )}
              </div>
              
              {/* More */}
              <button className="p-1.5 hover:bg-[#1D9BF0]/10 rounded-full transition-colors">
                <MoreHorizontal size={18} className="text-[#71767B]" />
              </button>
            </div>
          </div>

          {/* Character Counter */}
          {isEditing && (
            <div className="px-4 py-2 flex items-center justify-end gap-3">
              <CharCircle count={tweet.length} max={MAX_CHARS_PER_TWEET} />
              <span className={`text-xs font-mono ${
                tweet.length >= MAX_CHARS_PER_TWEET ? 'text-red-500' :
                tweet.length > MAX_CHARS_PER_TWEET * 0.8 ? 'text-yellow-500' :
                'text-[#71767B]'
              }`}>
                {MAX_CHARS_PER_TWEET - tweet.length}
              </span>
            </div>
          )}

          {/* Action Bar */}
          <div className="px-4 py-3 flex items-center justify-between max-w-[425px]">
            <button className="flex items-center gap-2 text-[#71767B] hover:text-[#1D9BF0] transition-colors group">
              <div className="p-2 rounded-full group-hover:bg-[#1D9BF0]/10 transition-colors">
                <MessageCircle size={18} />
              </div>
              <span className="text-xs">12</span>
            </button>
            <button className="flex items-center gap-2 text-[#71767B] hover:text-[#00BA7C] transition-colors group">
              <div className="p-2 rounded-full group-hover:bg-[#00BA7C]/10 transition-colors">
                <Repeat2 size={18} />
              </div>
              <span className="text-xs">48</span>
            </button>
            <button className="flex items-center gap-2 text-[#71767B] hover:text-[#F91880] transition-colors group">
              <div className="p-2 rounded-full group-hover:bg-[#F91880]/10 transition-colors">
                <Heart size={18} />
              </div>
              <span className="text-xs">156</span>
            </button>
            <button className="flex items-center gap-2 text-[#71767B] hover:text-[#1D9BF0] transition-colors group">
              <div className="p-2 rounded-full group-hover:bg-[#1D9BF0]/10 transition-colors">
                <BarChart2 size={18} />
              </div>
              <span className="text-xs">2.4K</span>
            </button>
            <button className="text-[#71767B] hover:text-[#1D9BF0] transition-colors group">
              <div className="p-2 rounded-full group-hover:bg-[#1D9BF0]/10 transition-colors">
                <Share size={18} />
              </div>
            </button>
          </div>
        </motion.div>
      ))}

      {/* Add Tweet Button */}
      {isEditing && !readOnly && (
        <motion.button
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          onClick={addTweet}
          className="w-full py-3 border border-dashed border-[#2F3336] rounded-2xl text-[#1D9BF0] text-sm font-medium hover:bg-[#1D9BF0]/5 transition-colors"
        >
          + Add another tweet to thread
        </motion.button>
      )}

      {/* Post Button */}
      {!readOnly && (
        <div className="flex justify-end pt-2">
          <button
            className="px-5 py-2.5 bg-[#D4FF00] text-black text-sm font-bold rounded-full hover:bg-[#c4ef00] transition-colors"
            onClick={() => {
              const fullContent = tweets.length > 1 
                ? tweets.map((t, i) => `${i + 1}/ ${t}`).join('\n\n')
                : tweets[0];
              onContentChange?.(fullContent);
            }}
          >
            {tweets.length > 1 ? 'Post Thread' : 'Post'}
          </button>
        </div>
      )}
    </div>
  );
}
