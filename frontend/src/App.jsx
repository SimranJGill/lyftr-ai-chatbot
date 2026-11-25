import { useEffect, useRef, useState } from "react";
import { Activity, ArrowUp, Bot, Check, ChevronDown, CircleHelp, Command, Cpu, Menu, Plus, Settings2, ShieldCheck, Sparkles, Wifi, X } from "lucide-react";

const API = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");
const newSession = () => `s-${crypto.randomUUID().slice(0, 8)}`;

function Meta({ metadata }) {
  const cache = metadata.resolution_source === "LLM_CACHE";
  return <div className="meta-panel">
    <div className="meta-top"><span className="meta-label">REQUEST DETAILS</span><span data-testid="meta-source" className={`source ${cache ? "cached" : "live"}`}><i />{metadata.resolution_source}</span></div>
    <div className="meta-grid">
      <div><span>MODEL</span><strong data-testid="meta-model">{metadata.model}</strong></div>
      <div><span>LATENCY</span><strong data-testid="meta-latency">{metadata.latency_ms} ms</strong></div>
      <div><span>INPUT TOKENS</span><strong data-testid="meta-input-tokens">{metadata.input_tokens}</strong></div>
      <div><span>OUTPUT TOKENS</span><strong data-testid="meta-output-tokens">{metadata.output_tokens}</strong></div>
      <div><span>KEY</span><strong>{metadata.key_id || "Cache"}</strong></div>
      <div><span>FALLBACKS</span><strong>{metadata.fallback_attempts}</strong></div>
    </div>
  </div>;
}

export default function App() {
  const [sessionId, setSessionId] = useState(newSession);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [showSettings, setShowSettings] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [apiStatus, setApiStatus] = useState("checking");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    fetch(`${API}/health`).then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then(() => setApiStatus("online")).catch(() => setApiStatus("offline"));
  }, []);
  useEffect(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), [messages, busy]);

  const startNew = () => {
    setSessionId(newSession()); setMessages([]); setError(""); setInput(""); setSidebarOpen(false);
  };

  async function sendMessage(e) {
    e?.preventDefault();
    const message = input.trim();
    if (!message || busy) return;
    setInput(""); setError(""); setMessages(prev => [...prev, { role: "user", content: message }]);
    setBusy(true);
    try {
      const response = await fetch(`${API}/chat`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, message, ...(systemPrompt.trim() ? { system_prompt: systemPrompt.trim() } : {}) })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Something went wrong. Please try again.");
      setMessages(prev => [...prev, { role: "assistant", content: data.reply, metadata: data.metadata }]);
    } catch (err) {
      setError(err.message || "Unable to reach the server. Check your connection and try again.");
    } finally { setBusy(false); inputRef.current?.focus(); }
  }

  return <div className="app-shell">
    <aside className={`sidebar ${sidebarOpen ? "open" : ""}`}>
      <div className="brand"><div className="brand-mark"><Sparkles size={18}/></div><div><b>lyftr<span>.</span></b><small>AI WORKSPACE</small></div><button className="icon-btn mobile-close" onClick={() => setSidebarOpen(false)}><X size={17}/></button></div>
      <button className="new-chat" onClick={startNew}><Plus size={17}/> New conversation <span>⌘ K</span></button>
      <div className="side-section"><span className="side-label">WORKSPACE</span><div className="side-item active"><Command size={16}/> AI Assistant</div><button className="side-item" onClick={() => setShowSettings(v => !v)}><Settings2 size={16}/> Session settings</button></div>
      <div className="sidebar-bottom">
        <div className="system-card"><div className="system-card-head"><span className="pulse-dot"/><b>System status</b><span className="status-text">{apiStatus === "online" ? "Operational" : apiStatus === "checking" ? "Checking" : "Offline"}</span></div><p>{apiStatus === "online" ? "Your workspace is connected and ready." : "The API could not be reached."}</p><div className="system-foot"><span><Wifi size={13}/> API connection</span><span className={apiStatus === "online" ? "good" : "bad"}>{apiStatus === "online" ? "Healthy" : "Unavailable"}</span></div></div>
        <div className="profile"><div className="avatar">L</div><div><b>Personal workspace</b><small>Local session</small></div><button className="icon-btn"><CircleHelp size={17}/></button></div>
      </div>
    </aside>

    <main className="main-area">
      <header className="topbar"><div className="top-left"><button className="icon-btn mobile-menu" onClick={() => setSidebarOpen(true)}><Menu size={19}/></button><span className="crumb">Workspace</span><span className="slash">/</span><b>AI Assistant</b></div><div className="top-right"><span className={`connection ${apiStatus}`}><i/>{apiStatus === "online" ? "Connected" : apiStatus === "checking" ? "Connecting" : "Disconnected"}</span><button className="icon-btn settings-trigger" title="Session settings" onClick={() => setShowSettings(v => !v)}><Settings2 size={18}/></button></div></header>

      {showSettings && <div className="settings-popover"><div className="settings-title"><div><b>Session settings</b><small>Customize how the assistant responds.</small></div><button className="icon-btn" onClick={() => setShowSettings(false)}><X size={16}/></button></div><label htmlFor="system-prompt-input">SYSTEM PROMPT</label><textarea id="system-prompt-input" data-testid="system-prompt-input" value={systemPrompt} onChange={e => setSystemPrompt(e.target.value)} placeholder="e.g. Keep answers concise and use examples..." rows={4}/><small>Applies to messages sent in this session.</small></div>}

      <section className={`conversation ${messages.length ? "has-messages" : ""}`}>
        {messages.length === 0 ? <div className="welcome">
          <div className="welcome-icon"><Sparkles size={22}/></div><div className="eyebrow">YOUR AI WORKSPACE</div>
          <h1>A little clarity<br/>goes a long way.</h1><p>Ask a question, explore an idea, or work through something complex. We'll take it one step at a time.</p>
          <div className="suggestions"><button onClick={() => setInput("Explain how API caching works and why it matters.")}><span className="suggestion-icon"><Cpu size={16}/></span><span><b>Explain a concept</b><small>Break down something technical</small></span><span className="suggestion-arrow">↗</span></button><button onClick={() => setInput("Help me plan a project from idea to launch.")}><span className="suggestion-icon"><Activity size={16}/></span><span><b>Plan something</b><small>Turn an idea into clear next steps</small></span><span className="suggestion-arrow">↗</span></button><button onClick={() => setInput("Review this approach and suggest improvements.")}><span className="suggestion-icon"><ShieldCheck size={16}/></span><span><b>Think it through</b><small>Review an approach or decision</small></span><span className="suggestion-arrow">↗</span></button></div>
        </div> : <div className="message-list">{messages.map((msg, i) => <article key={i} data-testid={msg.role === "assistant" ? "assistant-message" : undefined} className={`message ${msg.role}`}><div className={`message-avatar ${msg.role}`}>{msg.role === "assistant" ? <Sparkles size={15}/> : "S"}</div><div className="message-body"><div className="message-author">{msg.role === "assistant" ? "Lyftr AI" : "You"}<span>{msg.role === "assistant" ? "ASSISTANT" : "YOU"}</span></div><div className="message-content">{msg.content}</div>{msg.metadata && <Meta metadata={msg.metadata}/>}</div></article>)}{busy && <article className="message assistant"><div className="message-avatar assistant"><Sparkles size={15}/></div><div className="message-body"><div className="message-author">Lyftr AI <span>ASSISTANT</span></div><div className="typing"><i/><i/><i/><span>Thinking through your message</span></div></div></article>}</div>}
        {error && <div className="error-banner"><span>{error}</span><button onClick={() => setError("")}>Dismiss</button></div>}
        <div ref={bottomRef}/>
      </section>

      <div className="composer-wrap"><form className="composer" onSubmit={sendMessage}><textarea ref={inputRef} data-testid="chat-input" value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }} placeholder="Message your assistant..." rows={1} disabled={busy}/><div className="composer-bottom"><span><span className="composer-hint">↵</span> to send <span className="hint-divider">·</span> Shift + ↵ for new line</span><button type="submit" data-testid="send-button" disabled={!input.trim() || busy} className="send-btn" aria-label="Send message">{busy ? <span className="button-spinner"/> : <ArrowUp size={18}/>}</button></div></form><div className="disclaimer">AI can make mistakes. Check important information before relying on it.</div></div>
    </main>
  </div>;
}
