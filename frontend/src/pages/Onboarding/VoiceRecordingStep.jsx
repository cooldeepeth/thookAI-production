import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Mic, Square, AlertCircle, Check } from 'lucide-react';

export default function VoiceRecordingStep({ onComplete, onSkip }) {
  // States: 'idle' | 'recording' | 'recorded' | 'error'
  const [recordingState, setRecordingState] = useState('idle');
  const [audioUrl, setAudioUrl] = useState(null);
  const [audioBlob, setAudioBlob] = useState(null); // kept for potential future upload
  const [secondsLeft, setSecondsLeft] = useState(30);
  const [errorMsg, setErrorMsg] = useState('');
  const recorderRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);

  // Cleanup: revoke object URL on unmount (Pitfall 2 — memory leak prevention)
  useEffect(() => {
    return () => {
      if (audioUrl) URL.revokeObjectURL(audioUrl);
      clearInterval(timerRef.current);
      // Stop any active recording on unmount (prevent phantom capture after navigation)
      if (recorderRef.current && recorderRef.current.state === 'recording') {
        recorderRef.current.stop();
      }
    };
  }, [audioUrl]);

  const startRecording = async () => {
    setErrorMsg('');
    // HTTPS / secure context guard (Pitfall 1 — navigator.mediaDevices unavailable on HTTP)
    if (!navigator.mediaDevices?.getUserMedia) {
      setErrorMsg('Voice recording requires a secure connection (HTTPS). Continue without a voice sample.');
      setRecordingState('error');
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      // Safari fallback: audio/mp4 — always check isTypeSupported first
      const mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4';
      const recorder = new MediaRecorder(stream, { mimeType });
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: mimeType });
        setAudioBlob(blob);
        const url = URL.createObjectURL(blob);
        setAudioUrl(url);
        // Release mic track — stop all tracks from the stream
        stream.getTracks().forEach(t => t.stop());
        setRecordingState('recorded');
      };

      recorderRef.current = recorder;
      recorder.start(100); // collect data every 100ms for smooth blob accumulation
      setRecordingState('recording');
      setSecondsLeft(30);

      let s = 30;
      timerRef.current = setInterval(() => {
        s -= 1;
        setSecondsLeft(s);
        if (s <= 0) {
          clearInterval(timerRef.current);
          if (recorder.state === 'recording') recorder.stop();
        }
      }, 1000);
    } catch {
      setErrorMsg('Microphone access was denied. Please allow microphone permissions in your browser settings and try again.');
      setRecordingState('error');
    }
  };

  const stopEarly = () => {
    clearInterval(timerRef.current);
    if (recorderRef.current?.state === 'recording') {
      recorderRef.current.stop();
    }
  };

  const resetRecording = () => {
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    setAudioUrl(null);
    setAudioBlob(null);
    setRecordingState('idle');
    setSecondsLeft(30);
    setErrorMsg('');
  };

  // Format seconds as M:SS (e.g. 0:28)
  const formatTime = (s) => `0:${String(s).padStart(2, '0')}`;

  return (
    <div
      className="flex items-center justify-center min-h-full p-8"
      data-testid="voice-recording-step"
    >
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="max-w-lg w-full text-center"
      >
        <p className="text-lime text-xs font-bold uppercase tracking-widest mb-3">
          Step 2 of 5
        </p>

        {/* IDLE STATE */}
        {recordingState === 'idle' && (
          <>
            <h2 className="font-display font-bold text-3xl text-white mb-3">
              Let's hear your voice
            </h2>
            <p className="text-zinc-500 text-sm max-w-md mx-auto text-center mb-10">
              Read any sentence aloud for 15–30 seconds. We use voice patterns to calibrate your Persona Engine.
            </p>
            <div className="flex flex-col items-center gap-4">
              <button
                onClick={startRecording}
                data-testid="start-recording-btn"
                aria-label="Start voice recording"
                className="w-20 h-20 rounded-full bg-lime/10 border-2 border-lime/20 hover:border-lime/50 hover:bg-lime/20 flex items-center justify-center transition-all focus-ring"
              >
                <Mic size={32} className="text-lime" />
              </button>
              <p className="text-zinc-500 text-xs">Click to start recording</p>
            </div>
            <button
              onClick={() => onSkip ? onSkip() : onComplete(null)}
              data-testid="voice-skip-link"
              className="mt-8 text-zinc-600 text-xs underline cursor-pointer hover:text-zinc-400 transition-colors"
            >
              Skip voice sample
            </button>
          </>
        )}

        {/* RECORDING STATE */}
        {recordingState === 'recording' && (
          <>
            <h2 className="font-display font-bold text-3xl text-white mb-3">
              Recording...
            </h2>
            <p className="text-zinc-500 text-sm mb-10">
              Speak naturally. Recording stops automatically.
            </p>
            <div className="flex flex-col items-center gap-4">
              {/* Outer pulse ring */}
              <div className="relative flex items-center justify-center">
                <div className="absolute w-24 h-24 rounded-full border border-lime/20 animate-pulse-lime" />
                <button
                  onClick={stopEarly}
                  data-testid="stop-recording-btn"
                  aria-label="Stop recording"
                  className="w-20 h-20 rounded-full bg-red-500/10 border-2 border-red-400/40 flex items-center justify-center transition-all focus-ring z-10"
                >
                  <Square size={28} className="text-red-400" fill="#f87171" />
                </button>
              </div>
              {/* Timer with aria-live for screen reader countdown announcements */}
              <div aria-live="polite" className="flex items-center gap-2">
                <div className="w-2 h-2 bg-red-400 rounded-full animate-pulse" />
                <span className="font-mono text-lime text-xs font-bold">
                  {formatTime(secondsLeft)} remaining
                </span>
              </div>
            </div>
          </>
        )}

        {/* RECORDED STATE */}
        {recordingState === 'recorded' && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
          >
            <div className="w-12 h-12 bg-lime/15 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Check size={24} className="text-lime" />
            </div>
            <h2 className="font-display font-bold text-3xl text-white mb-6">
              Voice sample recorded
            </h2>
            {audioUrl && (
              <audio
                controls
                src={audioUrl}
                data-testid="voice-playback-audio"
                className="w-full rounded-xl mb-6"
              />
            )}
            <div className="flex gap-3">
              <button
                onClick={resetRecording}
                data-testid="voice-retry-btn"
                className="btn-ghost flex-1 text-sm"
              >
                Record again
              </button>
              <button
                onClick={() => onComplete(null)}
                data-testid="voice-confirm-btn"
                className="btn-primary flex-1 text-sm"
              >
                Sounds good, continue
              </button>
            </div>
          </motion.div>
        )}

        {/* ERROR STATE */}
        {recordingState === 'error' && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="flex flex-col items-center gap-4"
          >
            <AlertCircle size={24} className="text-red-400" />
            <p className="text-red-400 text-sm text-center max-w-sm">
              {errorMsg || 'Microphone access was denied. Please allow microphone permissions in your browser settings and try again.'}
            </p>
            <button
              onClick={() => onComplete(null)}
              className="btn-ghost text-sm"
            >
              Continue without voice sample
            </button>
          </motion.div>
        )}
      </motion.div>
    </div>
  );
}
