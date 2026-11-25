import React, {useEffect, useRef, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {ArrowUp, Plus, MessageSquare, Sparkles, ArrowUpRight, SlidersHorizontal, X, ChevronDown, Check, Copy, ShieldCheck, Zap, PanelLeftClose, PanelLeftOpen, RefreshCw, Activity, Code2, Lightbulb, Feather} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './styles.css';

const API = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const newSession = () => ({id: crypto.randomUUID(), title:'New conversation', messages:[], prompt:''});
const ideas = [
  {icon:Lightbulb, title:'Make the complex simple', text:'Explain response caching like I’m new to AI.', category:'Understand'},
  {icon:Code2, title:'Build something better', text:'What makes a Python API resilient?', category:'Create'},
  {icon:Feather, title:'Find the right words', text:'Write a friendly introduction for a new teammate.', category:'Write'},
];

function Metadata({meta}) {
  return <div className="metadata"><span data-testid="meta-source" className={'source '+(meta.resolution_source==='LLM_CACHE'?'cached':'live')}><Zap size={11}/>{meta.resolution_source}</span><span data-testid="meta-model">{meta.model}</span><span data-testid="meta-latency">{meta.latency_ms} ms</span><span className="tokens"><span data-testid="meta-input-tokens">{meta.input_tokens}</span> in <span className="dot">·</span> <span data-testid="meta-output-tokens">{meta.output_tokens}</span> out</span><span title="Successful API key and failed attempts">{meta.key_id || 'cache'} · {meta.fallback_attempts} retries</span></div>;
}

function App() {
  const [sessions,setSessions] = useState(()=>[newSession()]);
  const [active,setActive]=useState(null);
  const session = sessions.find(s=>s.id===active)||sessions[0];
  const [input,setInput]=useState(''); const [busy,setBusy]=useState(false);
  const [settings,setSettings]=useState(false); const [sidebar,setSidebar]=useState(true);
  const [health,setHealth]=useState(null); const [failure,setFailure]=useState('');
  const [copied,setCopied]=useState(null); const end=useRef(null); const textarea=useRef(null);
  useEffect(()=>{let alive=true; const check=()=>fetch(API+'/health').then(async r=>{if(alive)setHealth(r.ok?await r.json():false)}).catch(()=>{if(alive)setHealth(false)}); check(); const interval=setInterval(check,30000); return()=>{alive=false;clearInterval(interval)}},[]);
  useEffect(()=>{end.current?.scrollIntoView({behavior:'smooth'})},[session.messages,busy]);
  const update=(id,fn)=>setSessions(s=>s.map(x=>x.id===id?fn(x):x));
  function fresh(){if(busy)return;const s=newSession();setSessions(xs=>[s,...xs]);setActive(s.id);setInput('');setFailure('')}
  async function send(event) {
    event?.preventDefault(); const message=input.trim(); if(!message||busy)return;
    const id=session.id; setInput('');setBusy(true);
    update(id,s=>({...s,title:s.messages.length?s.title:message.slice(0,34),messages:[...s.messages,{role:'user',content:message}]}));
    try {
      const response=await fetch(API+'/chat',{method:'POST',headers:{'Content-Type':'application/json',...(failure?{'X-Simulate-Failure':failure}:{})},body:JSON.stringify({session_id:id,message,...(session.prompt?{system_prompt:session.prompt}:{})}),signal:AbortSignal.timeout(120000)});
      const body=await response.json();
      if(!response.ok)throw new Error(response.status===503?'All providers are temporarily unavailable. Your message was not saved. Please try again.':typeof body.detail==='string'?body.detail:'Please check your message and try again.');
      update(id,s=>({...s,messages:[...s.messages,{role:'assistant',content:body.reply,metadata:body.metadata}]}));
    }catch(error){update(id,s=>({...s,messages:[...s.messages,{role:'error',content:error.name==='TimeoutError'?'The request timed out. Check the conversation history before retrying.':error.message==='Failed to fetch'?'Unable to reach the backend. Check the connection and try again.':error.message,retry:message}]}));}
    finally{setBusy(false);textarea.current?.focus()}
  }
  async function loadHistory(){try{const r=await fetch(`${API}/sessions/${session.id}/messages`);if(!r.ok)throw Error('No saved messages yet.');const body=await r.json();update(session.id,s=>({...s,messages:body.messages}));}catch(e){update(session.id,s=>({...s,messages:[...s.messages,{role:'error',content:e.message}]}));}}
  return <div className={'app '+(!sidebar?'collapsed':'')}>
    {sidebar&&<aside className="sidebar"><a className="brand" href="/" aria-label="Lyftr home"><span className="brand-icon"><Sparkles size={21}/></span>lyftr<span className="brand-period">.</span><span className="brand-tag">CHAT</span></a>
      <button className="new-chat" onClick={fresh} disabled={busy}><Plus size={17}/>New conversation<span>↗</span></button>
      <div className="section-label">YOUR WORKSPACE <span>{sessions.length.toString().padStart(2,'0')}</span></div>
      <nav aria-label="Conversations">{sessions.map(s=><button disabled={busy} key={s.id} className={'conversation '+(session.id===s.id?'selected':'')} onClick={()=>{setActive(s.id);setInput('')}}><MessageSquare size={15}/><span>{s.title}</span>{s.id===session.id&&<span className="selected-dot"/>}</button>)}</nav>
      <div className="sidebar-bottom"><div className="resilience"><span className="shield"><ShieldCheck size={18}/></span><strong>Built to keep going.</strong><p>Smart caching. Automatic failover.<br/>One uninterrupted conversation.</p><span className="mini-label">POWERED BY LITELLM <ArrowUpRight size={12}/></span></div><div className="profile"><span className="avatar">Y</span><div><strong>Your workspace</strong><small>Personal session</small></div><button aria-label="Open settings" onClick={()=>setSettings(true)}><SlidersHorizontal size={16}/></button></div></div>
    </aside>}
    <main><header><div className="header-left"><button className="icon-button" aria-label="Toggle sidebar" onClick={()=>setSidebar(!sidebar)}>{sidebar?<PanelLeftClose size={19}/>:<PanelLeftOpen size={19}/>}</button><span>Workspace</span><span className="slash">/</span><strong>Chat</strong></div><div className="header-right"><span className={'connection '+(health?'connected':'')}><i/>{health?'Systems operational':health===false?'Backend not ready':'Connecting'}</span><button className="settings-button" onClick={()=>setSettings(true)}><SlidersHorizontal size={15}/><span>Session settings</span></button></div></header>
      <div className="chat-area"><div className="model-bar"><span className="model-pill"><Sparkles size={14}/>Lyftr Assistant</span><span className="model-sub">A little more clarity.</span><span className="session-id">SESSION {session.id.slice(0,8)}</span></div>
      <section className={'conversation-body '+(!session.messages.length?'empty':'')} aria-label="Chat messages" aria-live="polite">
        {!session.messages.length?<div className="welcome"><div className="welcome-symbol"><Sparkles size={29}/><span className="orbit-dot"/></div><div className="eyebrow">SPACE FOR YOUR NEXT BIG IDEA</div><h1>Good conversations.<br/><span>Great possibilities.</span></h1><p>A thought, a question, a spark of an idea.<br/>Let’s see where it takes you.</p><div className="suggestions">{ideas.map(({icon:Icon,title,text,category})=><button key={title} onClick={()=>{setInput(text);textarea.current?.focus()}}><div className="card-top"><Icon size={19}/><ArrowUpRight size={16}/></div><strong>{title}</strong><span>{text}</span><small>{category}</small></button>)}</div></div>:<div className="messages">{session.messages.map((m,i)=>m.role==='user'?<div key={i} className="user-message"><div>{m.content}</div><span className="user-icon">Y</span></div>:m.role==='error'?<div key={i} className="error-message" role="alert"><Activity size={18}/><div><strong>Let’s try that again</strong><p>{m.content}</p>{m.retry&&<button onClick={()=>{setInput(m.retry);textarea.current?.focus()}}>Edit and retry ↗</button>}</div></div>:<article key={i} className="assistant-row"><div className="assistant-icon"><Sparkles size={17}/></div><div className="assistant-content" data-testid="assistant-message"><div className="assistant-label">Lyftr <span>ASSISTANT</span></div><div className="markdown"><ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown></div><Metadata meta={m.metadata}/><button className="copy-button" aria-label="Copy reply" onClick={async()=>{try{await navigator.clipboard.writeText(m.content);setCopied(i)}catch{setCopied(null)}}}>{copied===i?<Check size={13}/>:<Copy size={13}/>} {copied===i?'Copied':'Copy'}</button></div></article>)}{busy&&<div className="assistant-row"><div className="assistant-icon"><Sparkles size={17}/></div><div className="thinking"><span/><span/><span/><small>Making room for an answer</small></div></div>}<div ref={end}/></div>}
      </section><div className="composer-wrap"><form className="composer" onSubmit={send}><textarea ref={textarea} data-testid="chat-input" aria-label="Message Lyftr" placeholder="Ask anything, or start with an idea…" rows={2} maxLength={4000} value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()}}}/><div className="composer-bottom"><div className="composer-hints"><span><ShieldCheck size={13}/>Context stays with your session</span>{failure&&<span className="test-active">Failure test on</span>}</div><span className="character-count">{input.length?`${input.length}/4000`:''}</span><button data-testid="send-button" className="send" type="submit" aria-label="Send message" disabled={busy||!input.trim()}><ArrowUp size={19}/></button></div></form><div className="composer-foot"><span>AI can make mistakes. A little human judgment goes a long way.</span><span><kbd>↵</kbd> to send <span className="foot-divider">·</span> <kbd>shift ↵</kbd> for a new line</span></div></div></div>
      <footer><span><span className="footer-dot"/>REACT <b>·</b> FASTAPI <b>·</b> SQLITE</span><span>Thoughtfully connected.</span><span>Lyftr AI <b>©</b> {new Date().getFullYear()}</span></footer>
    </main>
    {settings&&<div className="modal-backdrop" onClick={()=>setSettings(false)}><section className="settings-modal" role="dialog" aria-modal="true" aria-labelledby="settings-title" onClick={e=>e.stopPropagation()}><div className="modal-heading"><div><span className="eyebrow">MAKE IT YOURS</span><h2 id="settings-title">Session settings</h2></div><button className="icon-button" autoFocus aria-label="Close settings" onClick={()=>setSettings(false)}><X size={19}/></button></div><label htmlFor="prompt">System prompt</label><p>Guide the assistant’s tone and behavior for this conversation.</p><textarea id="prompt" data-testid="system-prompt-input" placeholder="You are a helpful, clear and concise assistant." maxLength={8000} disabled={busy} value={session.prompt} onChange={e=>update(session.id,s=>({...s,prompt:e.target.value}))}/><label htmlFor="failure">Resilience testing</label><p>Applies to the next request while enabled. Use a new question to avoid an existing cache hit.</p><select id="failure" value={failure} onChange={e=>setFailure(e.target.value)}><option value="">Normal operation</option><option value="key_1=429">Key 1 → HTTP 429 · use fallback</option><option value="key_1=500">Key 1 → HTTP 500 · use fallback</option><option value="*=429">All keys → HTTP 429 · graceful error</option></select><div className="settings-status"><span>Configured keys</span><strong>{health?health.keys_configured:'Unavailable'}</strong><span>Response cache</span><strong>{health?.cache_enabled?'Enabled':'Unavailable'}</strong><span>Backend</span><a href={API+'/health'} target="_blank" rel="noreferrer">View health <ArrowUpRight size={12}/></a></div><button className="history-button" disabled={busy} onClick={loadHistory}><RefreshCw size={14}/>Reload saved session history</button><button className="done-button" onClick={()=>setSettings(false)}>Done <Check size={15}/></button></section></div>}
  </div>;
}
createRoot(document.getElementById('root')).render(<App/>);
