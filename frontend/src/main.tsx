import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

type Status = { status: string; services: Record<string, string> };
type Video = { id: string; filename: string; media_type: string; status: string; created_at: string };
type Job = { id: string; video_id: string; kind: string; status: string; result?: { model_status: string; message: string; timeline: unknown[] } | null; error?: string | null };
type Hit = { document_id: string; filename: string; score: number; excerpt: string };
type LlmConfig = { provider: string | null; model: string | null; configured: boolean; base_url: string | null };
type ChatMessage = { role: "user" | "assistant"; text: string; citations?: Hit[] };

async function api<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

function App() {
  const [health, setHealth] = useState<Status | null>(null);
  const [videos, setVideos] = useState<Video[]>([]);
  const [selectedVideo, setSelectedVideo] = useState<Video | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<Hit[]>([]);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatQuestion, setChatQuestion] = useState("");
  const [chatBusy, setChatBusy] = useState(false);
  const [llm, setLlm] = useState<LlmConfig | null>(null);
  const [provider, setProvider] = useState("openai");
  const [model, setModel] = useState("gpt-4.1-mini");
  const [apiKey, setApiKey] = useState("");
  const [notice, setNotice] = useState("");

  const refresh = () => {
    api<Status>("/api/v1/health").then(setHealth).catch(() => setHealth({ status: "offline", services: {} }));
    api<Video[]>("/api/v1/videos").then(setVideos).catch(() => undefined);
    api<LlmConfig>("/api/v1/settings/llm").then(setLlm).catch(() => undefined);
  };
  useEffect(refresh, []);
  useEffect(() => {
    if (!job || job.status === "completed" || job.status === "failed") return;
    const timer = window.setTimeout(() => api<Job>(`/api/v1/analyses/${job.id}`).then(setJob), 700);
    return () => window.clearTimeout(timer);
  }, [job]);

  async function upload(file: File) {
    const form = new FormData();
    form.append("file", file);
    try {
      const video = await api<Video>("/api/v1/videos/upload", { method: "POST", body: form });
      setSelectedVideo(video);
      setNotice(`${video.filename} uploaded successfully.`);
      refresh();
    } catch (error) { setNotice(error instanceof Error ? error.message : "Upload failed"); }
  }
  async function analyze() {
    if (!selectedVideo) return;
    try {
      const result = await api<Job>(`/api/v1/analyses/cctv/${selectedVideo.id}`, { method: "POST" });
      setJob(result);
      setNotice("Analysis queued. The status will update automatically.");
    } catch (error) { setNotice(error instanceof Error ? error.message : "Analysis failed"); }
  }
  async function search() {
    if (!query.trim()) return;
    try { setHits(await api<Hit[]>("/api/v1/retrieval/query", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query }) })); }
    catch (error) { setNotice(error instanceof Error ? error.message : "Retrieval failed"); }
  }
  async function askAssistant() {
    const question = chatQuestion.trim();
    if (!question || chatBusy) return;
    setChatMessages((messages) => [...messages, { role: "user", text: question }]);
    setChatQuestion("");
    setChatBusy(true);
    try {
      const response = await api<{ answer: string; citations: Hit[] }>("/api/v1/assistant/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, incident_id: selectedVideo?.id }),
      });
      setChatMessages((messages) => [...messages, { role: "assistant", text: response.answer, citations: response.citations }]);
    } catch (error) {
      setChatMessages((messages) => [...messages, { role: "assistant", text: error instanceof Error ? error.message : "The assistant request failed." }]);
    } finally { setChatBusy(false); }
  }
  async function saveLlm() {
    try {
      const config = await api<LlmConfig>("/api/v1/settings/llm", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ provider, model, api_key: apiKey }) });
      setLlm(config); setApiKey(""); setNotice("LLM configuration saved locally. The API key is never returned to the browser.");
      refresh();
    } catch (error) { setNotice(error instanceof Error ? error.message : "LLM configuration failed"); }
  }
  const serviceEntries = health ? Object.entries(health.services) : [];

  return <main>
    <header className="hero"><div><p className="eyebrow">TRAFFIC INTELLIGENCE WORKSPACE</p><h1>CrashScope <span>AI</span></h1><p>Evidence-first incident investigation for CCTV and dashcam footage.</p></div><div className="health-pill"><i className={health?.status === "ok" ? "online" : ""} /> {health?.status ?? "checking"}</div></header>
    <nav><a href="#overview">Overview</a><a href="#upload">Upload video</a><a href="#investigation">Investigation</a><a href="#knowledge">Knowledge & RAG</a><a href="#settings">LLM settings</a></nav>
    {notice && <div className="notice">{notice}<button onClick={() => setNotice("")}>Dismiss</button></div>}
    <section id="overview" className="section"><div className="section-heading"><div><p className="eyebrow">OVERVIEW</p><h2>System readiness</h2></div><button className="secondary" onClick={refresh}>Refresh</button></div><div className="status-grid"><div className="card status-card"><div className="metric">{videos.length}</div><span>Uploaded videos</span></div><div className="card status-card"><div className="metric">{job && ["queued", "processing"].includes(job.status) ? 1 : 0}</div><span>Active analysis jobs</span></div><div className="card status-card"><div className="metric">{llm?.configured ? "ON" : "OFF"}</div><span>LLM provider</span></div><div className="card status-card"><div className="metric">{health?.services.rag ?? "—"}</div><span>Retrieval engine</span></div></div><div className="card service-card"><h3>Service health</h3><div className="service-list">{serviceEntries.map(([name, value]) => <span key={name}><i className={value === "available" || value === "configured" || value === "local-keyword" ? "online" : ""} />{name}<b>{value}</b></span>)}</div></div></section>
    <section id="upload" className="section split"><div><p className="eyebrow">INGESTION</p><h2>Upload a video</h2><p className="muted">Add an MP4, MOV, AVI, or MKV file. Files remain in local development storage.</p><label className="dropzone"><strong>Choose video file</strong><span>Maximum size is configured by the backend.</span><input type="file" accept="video/mp4,video/quicktime,video/x-msvideo,video/x-matroska" onChange={(event) => event.target.files?.[0] && upload(event.target.files[0])} /></label></div><div className="card"><h3>Recent videos</h3>{videos.length ? <ul className="video-list">{videos.map((video) => <li key={video.id} className={selectedVideo?.id === video.id ? "selected" : ""} onClick={() => setSelectedVideo(video)}><span>{video.filename}</span><small>{video.status}</small></li>)}</ul> : <p className="muted">No videos uploaded yet.</p>}</div></section>
    <section id="investigation" className="section"><div className="section-heading"><div><p className="eyebrow">INVESTIGATION WORKSPACE</p><h2>Analyze and review</h2></div><button className="primary" disabled={!selectedVideo || !!job && job.status === "processing"} onClick={analyze}>Start CCTV analysis</button></div><div className="workspace-grid"><div className="card video-panel">{selectedVideo ? <><div className="video-placeholder"><span>VIDEO PREVIEW</span><strong>{selectedVideo.filename}</strong></div><video controls src={`/api/v1/videos/${selectedVideo.id}/file`} /></> : <div className="empty"><strong>Select a video to begin</strong><span>Upload or select a video from the ingestion panel.</span></div>}</div><div className="card"><h3>Analysis status</h3>{job ? <><div className="job-state"><span className={`state ${job.status}`}>{job.status}</span><span>{job.kind.toUpperCase()}</span></div>{job.result && <><p className="muted">{job.result.message}</p><div className="timeline"><h4>Timeline</h4><div className="timeline-line"><span /></div><p>No verified event timestamps available.</p></div></>}{job.error && <p className="error">{job.error}</p>}</> : <p className="muted">No analysis job selected.</p>}</div></div><div className="card report-card"><div><p className="eyebrow">REPORT</p><h3>Evidence-constrained report</h3><p className="muted">Reports keep visual observations, model predictions, hypotheses, and uncertainties separate.</p></div><div className="report-badge">Human review required</div></div></section>
    <section id="knowledge" className="section"><p className="eyebrow">KNOWLEDGE INTELLIGENCE</p><h2>AI investigation assistant</h2><p className="muted">Ask questions about the selected investigation. Answers are limited to indexed evidence and clearly identify uncertainty.</p><div className="chat-layout"><div className="card chat-panel"><div className="chat-messages">{chatMessages.length === 0 && <div className="chat-empty"><strong>Ask CrashScope Assistant</strong><span>Try: “Which observations support this classification?”</span></div>}{chatMessages.map((message, index) => <div className={`message ${message.role}`} key={`${message.role}-${index}`}><span className="message-label">{message.role === "user" ? "You" : "CrashScope Assistant"}</span><p>{message.text}</p>{message.citations?.map((citation) => <small className="citation" key={citation.document_id}>Source: {citation.filename} · {citation.excerpt}</small>)}</div>)}</div><div className="chat-input"><input value={chatQuestion} onChange={(event) => setChatQuestion(event.target.value)} onKeyDown={(event) => event.key === "Enter" && askAssistant()} placeholder="Ask an evidence-based question..." /><button className="primary" disabled={!chatQuestion.trim() || chatBusy} onClick={askAssistant}>{chatBusy ? "Thinking..." : "Send"}</button></div></div><div className="card results"><h3>Evidence search</h3><div className="search-row"><input value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => event.key === "Enter" && search()} placeholder="Search indexed documents..." /><button className="secondary" onClick={search}>Search</button></div>{hits.length ? hits.map((hit) => <article key={hit.document_id}><strong>{hit.filename}</strong><small>match score {hit.score}</small><p>{hit.excerpt}</p></article>) : <p className="muted">No retrieved sources yet.</p>}</div></div></section>
    <section id="settings" className="section"><div className="section-heading"><div><p className="eyebrow">INTEGRATIONS</p><h2>Configure your LLM</h2></div>{llm?.configured && <span className="configured">Configured · {llm.provider}</span>}</div><div className="settings-grid"><div className="card"><label>Provider<select value={provider} onChange={(event) => setProvider(event.target.value)}><option value="openai">OpenAI</option><option value="openrouter">OpenRouter</option></select></label><label>Model<input value={model} onChange={(event) => setModel(event.target.value)} placeholder="gpt-4.1-mini" /></label><label>API key<input type="password" value={apiKey} onChange={(event) => setApiKey(event.target.value)} placeholder={llm?.configured ? "Saved key (enter to replace)" : "sk-..."} /></label><button className="primary" disabled={apiKey.length < 10} onClick={saveLlm}>Save provider securely</button><p className="hint">Stored only in the local backend .env file. It is never shown in API responses.</p></div><div className="card integration-copy"><h3>Provider endpoints</h3><p><strong>OpenAI</strong><br />Uses the official OpenAI API with your selected model.</p><p><strong>OpenRouter</strong><br />Routes requests through OpenRouter. Use an OpenRouter model ID such as <code>openai/gpt-4.1-mini</code>.</p><p className="muted">This config enables the provider connection; report generation remains evidence-constrained and requires a valid key.</p></div></div></section>
    <footer>CrashScope AI · Experimental decision support · Never use automated output as a legal or safety determination.</footer>
  </main>;
}
createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);
