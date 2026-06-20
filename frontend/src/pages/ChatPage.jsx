import { useState, useRef, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { postChat, postUploadAudio, postUploadImage } from '../services/api';
import { useGeolocation } from '../hooks/useGeolocation';
import { Spinner } from '../components/shared/LoadingStates';

/* ─────────────────────────────────────────────
   Sound-wave animation (3 CSS bars)
   Shown on the playing message bubble
───────────────────────────────────────────── */
function SoundWave() {
  return (
    <span className="sound-wave" aria-hidden="true">
      <span className="bar" style={{ '--delay': '0s' }} />
      <span className="bar" style={{ '--delay': '0.15s' }} />
      <span className="bar" style={{ '--delay': '0.3s' }} />
    </span>
  );
}

/* ─────────────────────────────────────────────
   One-time TTS onboarding banner
───────────────────────────────────────────── */
function TtsBanner({ onEnable, onDismiss }) {
  return (
    <div className="tts-banner" role="alert">
      <span className="tts-banner__icon">🔊</span>
      <span className="tts-banner__text">
        KrishiBondhu can read replies aloud. Tap to enable.
      </span>
      <div className="tts-banner__actions">
        <button
          id="tts-banner-enable"
          className="tts-banner__btn tts-banner__btn--enable"
          onClick={onEnable}
        >
          Enable
        </button>
        <button
          id="tts-banner-dismiss"
          className="tts-banner__btn tts-banner__btn--dismiss"
          onClick={onDismiss}
        >
          Dismiss
        </button>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────
   ChatPage
───────────────────────────────────────────── */
export default function ChatPage() {
  const { t } = useTranslation();
  const { lat, lon } = useGeolocation();

  // ── State ──────────────────────────────────
  const [messages, setMessages] = useState([
    { role: 'assistant', content: t('chat.welcome'), ts: Date.now(), tts_path: null },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [recording, setRecording] = useState(false);

  // TTS preference: read from localStorage, default true
  const [ttsEnabled, setTtsEnabled] = useState(() => {
    const stored = localStorage.getItem('kb_tts_enabled');
    return stored === null ? true : stored === 'true';
  });

  // Show onboarding banner only once (null = not shown yet, if key absent)
  const [showBanner, setShowBanner] = useState(
    () => localStorage.getItem('kb_tts_enabled') === null
  );

  // Which message index is currently playing
  const [playingIdx, setPlayingIdx] = useState(null);

  // ── Refs ───────────────────────────────────
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const fileInputRef = useRef(null);
  const bottomRef = useRef(null);
  const audioRef = useRef(null); // single Audio instance reused

  // ── Helpers ────────────────────────────────
  const scrollToBottom = () =>
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });

  const persistTts = (val) => {
    setTtsEnabled(val);
    localStorage.setItem('kb_tts_enabled', String(val));
  };

  /** Play the TTS file for a message. Stops any currently playing audio first. */
  const playTts = useCallback((tts_path, msgIdx) => {
    if (!tts_path) return;
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.onended = null;
      audioRef.current.onerror = null;
    }
    const audio = new Audio(`/api/get_tts?path=${encodeURIComponent(tts_path)}`);
    audioRef.current = audio;
    setPlayingIdx(msgIdx);
    audio.play().catch(() => {
      // Autoplay policy blocked it – silently ignore
      setPlayingIdx(null);
    });
    audio.onended = () => setPlayingIdx(null);
    audio.onerror = () => setPlayingIdx(null);
  }, []);

  /** Called after every API response with a tts_path */
  const maybeAutoPlay = useCallback(
    (tts_path, msgIdx) => {
      if (ttsEnabled && tts_path) {
        playTts(tts_path, msgIdx);
      }
    },
    [ttsEnabled, playTts]
  );

  // Cleanup audio on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
      }
    };
  }, []);

  // ── Banner handlers ─────────────────────────
  const handleBannerEnable = () => {
    persistTts(true);
    setShowBanner(false);
  };
  const handleBannerDismiss = () => {
    persistTts(false);
    setShowBanner(false);
  };

  // ── Chat handlers ───────────────────────────
  const sendText = async () => {
    if (!input.trim() || loading) return;
    const text = input.trim();
    setInput('');
    setMessages((m) => [...m, { role: 'user', content: text, ts: Date.now() }]);
    setLoading(true);
    try {
      const res = await postChat(text, lat, lon);
      const newIdx = messages.length + 1; // approximate; recalculate below
      setMessages((m) => {
        const updated = [
          ...m,
          { role: 'assistant', content: res.reply_text, ts: Date.now(), tts_path: res.tts_path ?? null },
        ];
        // auto-play after state update
        setTimeout(() => maybeAutoPlay(res.tts_path, updated.length - 1), 50);
        return updated;
      });
    } catch (err) {
      setMessages((m) => [
        ...m,
        { role: 'assistant', content: `❌ ${err.message}`, ts: Date.now(), error: true },
      ]);
    } finally {
      setLoading(false);
      setTimeout(scrollToBottom, 100);
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => chunksRef.current.push(e.data);
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        const file = new File([blob], 'voice.webm', { type: 'audio/webm' });
        setMessages((m) => [...m, { role: 'user', content: '🎙️ Voice message', ts: Date.now() }]);
        setLoading(true);
        try {
          const res = await postUploadAudio(file, lat, lon);
          setMessages((m) => {
            const updated = [
              ...m,
              { role: 'assistant', content: res.reply_text, ts: Date.now(), tts_path: res.tts_path ?? null },
            ];
            setTimeout(() => maybeAutoPlay(res.tts_path, updated.length - 1), 50);
            return updated;
          });
        } catch (err) {
          setMessages((m) => [
            ...m,
            { role: 'assistant', content: `❌ ${err.message}`, ts: Date.now(), error: true },
          ]);
        } finally {
          setLoading(false);
          setTimeout(scrollToBottom, 100);
        }
      };
      recorder.start();
      mediaRecorderRef.current = recorder;
      setRecording(true);
    } catch {
      alert('Microphone access denied');
    }
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    setRecording(false);
  };

  const handleImageUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setMessages((m) => [...m, { role: 'user', content: '📷 Image uploaded', ts: Date.now() }]);
    setLoading(true);
    try {
      const res = await postUploadImage(file, lat, lon, '');
      setMessages((m) => {
        const updated = [
          ...m,
          { role: 'assistant', content: res.reply_text, ts: Date.now(), tts_path: res.tts_path ?? null },
        ];
        setTimeout(() => maybeAutoPlay(res.tts_path, updated.length - 1), 50);
        return updated;
      });
    } catch (err) {
      setMessages((m) => [
        ...m,
        { role: 'assistant', content: `❌ ${err.message}`, ts: Date.now(), error: true },
      ]);
    } finally {
      setLoading(false);
      setTimeout(scrollToBottom, 100);
    }
  };

  // ── Render ──────────────────────────────────
  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">

      {/* ── TTS Onboarding Banner ── */}
      {showBanner && (
        <TtsBanner onEnable={handleBannerEnable} onDismiss={handleBannerDismiss} />
      )}

      {/* ── Top controls bar with TTS toggle ── */}
      <div className="flex items-center justify-end gap-2 pb-2">
        <button
          id="tts-toggle"
          onClick={() => persistTts(!ttsEnabled)}
          className={`tts-toggle ${ttsEnabled ? 'tts-toggle--on' : 'tts-toggle--off'}`}
          title={ttsEnabled ? 'Mute voice replies' : 'Enable voice replies'}
          aria-label={ttsEnabled ? 'Mute voice replies' : 'Enable voice replies'}
          aria-pressed={ttsEnabled}
        >
          {ttsEnabled ? '🔊' : '🔇'}
        </button>
      </div>

      {/* ── Messages ── */}
      <div className="flex-1 overflow-y-auto space-y-3 pb-4 -mx-4 px-4">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed relative
                ${msg.role === 'user'
                  ? 'bg-primary text-white rounded-br-md'
                  : msg.error
                    ? 'bg-danger-light text-danger rounded-bl-md'
                    : 'bg-surface shadow-card text-text-primary rounded-bl-md'
                }`}
            >
              {/* Bot label + sound-wave indicator */}
              {msg.role === 'assistant' && (
                <span className="text-xs text-text-secondary flex items-center gap-1.5 mb-1">
                  🤖 {t('app.name')}
                  {playingIdx === i && <SoundWave />}
                </span>
              )}

              <p className="whitespace-pre-wrap">{msg.content}</p>

              {/* Per-message replay button for assistant messages */}
              {msg.role === 'assistant' && !msg.error && msg.tts_path && (
                <button
                  id={`tts-replay-${i}`}
                  className={`tts-replay-btn ${playingIdx === i ? 'tts-replay-btn--playing' : ''}`}
                  onClick={() => playTts(msg.tts_path, i)}
                  title="Replay audio"
                  aria-label="Replay audio"
                >
                  {playingIdx === i ? '⏸' : '🔈'}
                </button>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-surface shadow-card rounded-2xl rounded-bl-md px-4 py-3 flex items-center gap-2">
              <Spinner size="sm" className="text-primary" />
              <span className="text-sm text-text-secondary">{t('chat.thinking')}</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* ── Input bar ── */}
      <div className="flex items-center gap-2 pt-3 border-t border-border -mx-4 px-4 bg-bg">
        <button
          onClick={() => fileInputRef.current?.click()}
          className="w-10 h-10 flex items-center justify-center rounded-full bg-surface shadow-card
                     text-lg hover:bg-primary/10 transition-all flex-shrink-0"
          title={t('chat.attach_image')}
        >
          📎
        </button>
        <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={handleImageUpload} />

        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && sendText()}
          placeholder={t('chat.placeholder')}
          className="input-field flex-1 !py-2.5"
          disabled={loading}
        />

        {input.trim() ? (
          <button
            onClick={sendText}
            disabled={loading}
            className="w-10 h-10 flex items-center justify-center rounded-full bg-primary text-white
                       shadow-card hover:bg-primary-light transition-all flex-shrink-0"
          >
            ➤
          </button>
        ) : (
          <button
            onClick={recording ? stopRecording : startRecording}
            className={`w-10 h-10 flex items-center justify-center rounded-full flex-shrink-0
              shadow-card transition-all
              ${recording ? 'bg-danger text-white animate-pulse-record' : 'bg-surface hover:bg-primary/10'}`}
            title={recording ? t('chat.stop') : t('chat.voice_input')}
          >
            {recording ? '⏹' : '🎙️'}
          </button>
        )}
      </div>
    </div>
  );
}
