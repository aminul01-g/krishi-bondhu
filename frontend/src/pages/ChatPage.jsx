import { useState, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { postChat, postUploadAudio, postUploadImage } from '../services/api';
import { useGeolocation } from '../hooks/useGeolocation';
import { Spinner } from '../components/shared/LoadingStates';

export default function ChatPage() {
  const { t } = useTranslation();
  const { lat, lon } = useGeolocation();
  const [messages, setMessages] = useState([
    { role: 'assistant', content: t('chat.welcome'), ts: Date.now() },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [recording, setRecording] = useState(false);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const fileInputRef = useRef(null);
  const bottomRef = useRef(null);

  const scrollToBottom = () => bottomRef.current?.scrollIntoView({ behavior: 'smooth' });

  const sendText = async () => {
    if (!input.trim() || loading) return;
    const text = input.trim();
    setInput('');
    setMessages((m) => [...m, { role: 'user', content: text, ts: Date.now() }]);
    setLoading(true);
    try {
      const res = await postChat(text, lat, lon);
      setMessages((m) => [...m, { role: 'assistant', content: res.reply_text, ts: Date.now() }]);
    } catch (err) {
      setMessages((m) => [...m, { role: 'assistant', content: `❌ ${err.message}`, ts: Date.now(), error: true }]);
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
          setMessages((m) => [...m, { role: 'assistant', content: res.reply_text, ts: Date.now() }]);
        } catch (err) {
          setMessages((m) => [...m, { role: 'assistant', content: `❌ ${err.message}`, ts: Date.now(), error: true }]);
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
      setMessages((m) => [...m, { role: 'assistant', content: res.reply_text, ts: Date.now() }]);
    } catch (err) {
      setMessages((m) => [...m, { role: 'assistant', content: `❌ ${err.message}`, ts: Date.now(), error: true }]);
    } finally {
      setLoading(false);
      setTimeout(scrollToBottom, 100);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-3 pb-4 -mx-4 px-4">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed
              ${msg.role === 'user'
                ? 'bg-primary text-white rounded-br-md'
                : msg.error
                  ? 'bg-danger-light text-danger rounded-bl-md'
                  : 'bg-surface shadow-card text-text-primary rounded-bl-md'
              }`}>
              {msg.role === 'assistant' && <span className="text-xs text-text-secondary block mb-1">🤖 {t('app.name')}</span>}
              <p className="whitespace-pre-wrap">{msg.content}</p>
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

      {/* Input bar */}
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
          <button onClick={sendText} disabled={loading}
            className="w-10 h-10 flex items-center justify-center rounded-full bg-primary text-white
                       shadow-card hover:bg-primary-light transition-all flex-shrink-0">
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
