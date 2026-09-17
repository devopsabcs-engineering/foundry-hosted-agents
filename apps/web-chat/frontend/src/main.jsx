import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { PublicClientApplication, InteractionRequiredAuthError } from '@azure/msal-browser';
import { ArrowUp, Check, Copy, LogIn, LogOut, MessageSquare, Plus, ShieldCheck, Square, Trash2 } from 'lucide-react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import '@fontsource-variable/dm-sans';
import '@fontsource-variable/newsreader';
import './style.css';
import { consumeResponse } from './stream';
import { messageRequest } from './request';
import { queriesForLanguage } from './samples';
import { errorText, storedLanguage, STORAGE_KEY, translate } from './i18n';

function useLanguage() {
  const [language, setLanguage] = useState(() => storedLanguage());
  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, language); } catch {}
    document.documentElement.lang = language;
    document.title = `${translate(language, 'Threat assessment')} | Foundry`;
  }, [language]);
  return { language, setLanguage, t: text => translate(language, text) };
}

function LanguageToggle({ language, setLanguage }) {
  const label = language === 'en-CA' ? 'Passer au fran\u00e7ais' : 'Switch to English';
  return <button type="button" className="language-toggle" title={label} aria-label={label}
    lang={language === 'en-CA' ? 'fr-CA' : 'en-CA'}
    onClick={() => setLanguage(language === 'en-CA' ? 'fr-CA' : 'en-CA')}>
    {language === 'en-CA' ? 'FR' : 'EN'}
  </button>;
}

function ToolButton({ label, children, ...props }) {
  return <button className="tool" title={label} aria-label={label} {...props}>{children}</button>;
}

function CopyAnswer({ text, t }) {
  const [copied, setCopied] = useState(false);
  return <ToolButton label={t(copied ? 'Copied' : 'Copy answer')} onClick={async () => {
    try { await navigator.clipboard.writeText(text); setCopied(true); }
    catch { setCopied(false); }
  }}>{copied ? <Check size={16} /> : <Copy size={16} />}</ToolButton>;
}

function Chat({ auth, config, initialAccount }) {
  const { language, setLanguage, t } = useLanguage();
  const [account, setAccount] = useState(initialAccount);
  const [allowed, setAllowed] = useState(false);
  const [checking, setChecking] = useState(Boolean(initialAccount));
  const [error, setError] = useState('');
  const [sessions, setSessions] = useState([]);
  const [active, setActive] = useState(null);
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const abort = useRef(null);
  const pendingRequest = useRef(null);
  const composer = useRef(null);
  const end = useRef(null);
  const current = sessions.find(session => session.id === active);
  const messages = current?.messages ?? [];

  async function token() {
    try {
      return (await auth.acquireTokenSilent({ account, scopes: [config.scope] })).accessToken;
    } catch (failure) {
      if (failure instanceof InteractionRequiredAuthError) {
        throw new Error('Your sign-in needs attention. Sign out and sign in again.');
      }
      throw failure;
    }
  }

  async function api(path, options = {}) {
    const accessToken = await token();
    const response = await fetch(path, { ...options, headers: {
      ...options.headers,
      'Content-Type': 'application/json', Authorization: `Bearer ${accessToken}`,
    } });
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}));
      throw new Error(typeof detail.detail === 'string' ? detail.detail : `Request failed (${response.status}).`);
    }
    return response;
  }

  useEffect(() => {
    if (!account) return;
    let cancelled = false;
    api('/api/me').then(() => { if (!cancelled) setAllowed(true); })
      .catch(failure => { if (!cancelled) setError(failure.message); })
      .finally(() => { if (!cancelled) setChecking(false); });
    return () => { cancelled = true; };
  }, [account]);

  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }); }, [messages.length, busy]);
  useEffect(() => () => abort.current?.abort(), []);

  async function signIn() {
    setError('');
    try {
      await auth.loginRedirect({ scopes: [config.scope], prompt: 'select_account' });
    } catch (failure) { setError(failure.message); }
  }

  async function signOut() {
    abort.current?.abort();
    pendingRequest.current = null;
    setSessions([]); setActive(null); setAllowed(false); setAccount(null);
    await auth.logoutRedirect({ account, postLogoutRedirectUri: window.location.origin });
  }

  async function removeSession(identifier) {
    setError('');
    try {
      await api(`/api/conversations/${identifier}`, { method: 'DELETE' });
      setSessions(previous => previous.filter(session => session.id !== identifier));
      if (active === identifier) setActive(null);
    } catch (failure) { setError(failure.message); }
  }

  async function send(event) {
    event.preventDefault();
    if (!draft.trim() || busy || !allowed) return;
    const text = draft.trim();
    setBusy(true); setError(''); setDraft('');
    const controller = new AbortController();
    abort.current = controller;
    let identifier = active;
    let appended = false;
    let answered = false;
    try {
      if (!identifier) {
        const response = await api('/api/conversations', { method: 'POST', signal: controller.signal });
        identifier = (await response.json()).id;
        setSessions(previous => [...previous, { id: identifier, title: text.slice(0, 52), messages: [] }]);
        setActive(identifier);
      }
      setSessions(previous => previous.map(session => session.id === identifier
        ? { ...session, messages: [...session.messages, { role: 'user', text }] } : session));
      appended = true;
      pendingRequest.current = messageRequest(pendingRequest.current, identifier, text, language);
      const response = await api(`/api/conversations/${identifier}/messages`, {
        method: 'POST', body: JSON.stringify({ text, language }), signal: controller.signal,
        headers: { 'Idempotency-Key': pendingRequest.current.key },
      });
      await consumeResponse(response.body, payload => {
        if (payload.type === 'answer') {
          answered = true;
          pendingRequest.current = null;
          setSessions(previous => previous.map(session => session.id === identifier
            ? { ...session, messages: [...session.messages, { role: 'assistant', text: payload.text }] } : session));
        }
      });
    } catch (failure) {
      setError(failure.name === 'AbortError' ? 'Response stopped.' : failure.message);
      if (!answered) {
        setDraft(text);
        if (appended) setSessions(previous => previous.map(session => session.id === identifier
          ? { ...session, messages: session.messages.slice(0, -1) } : session));
      }
    } finally { setBusy(false); abort.current = null; }
  }

  return <div className="workspace">
    <aside className="sidebar">
      <div className="brand"><ShieldCheck size={28} /><span>Foundry<span className="brand-sub">{t('ASSESSMENT WORKSPACE')}</span></span></div>
      <button className="new-chat" disabled={!allowed || busy} onClick={() => { setActive(null); setDraft(''); setError(''); }}><Plus size={18} />{t('New assessment')}</button>
      <div className="section-label">{t('THIS SESSION')}</div>
      <nav aria-label={t('Conversations')} className="conversations">
        {sessions.map(session => <div className={`session ${session.id === active ? 'selected' : ''}`} key={session.id}>
          <button className="session-select" disabled={busy} onClick={() => { setActive(session.id); setDraft(''); setError(''); }}><MessageSquare size={16} /><span>{session.title}</span></button>
          <ToolButton label={t('Delete conversation')} disabled={busy} onClick={() => removeSession(session.id)}><Trash2 size={15} /></ToolButton>
        </div>)}
      </nav>
      <div className="identity"><span className="identity-label">{account?.name ?? t('Not signed in')}</span>{account && <ToolButton label={t('Sign out')} disabled={busy} onClick={signOut}><LogOut size={18} /></ToolButton>}</div>
    </aside>
    <main>
      <header className="topbar"><div><span className="overline">{t('AIR CANADA / SECURITY OPERATIONS')}</span><h1>{t('Threat assessment')}</h1></div><div className="topbar-actions"><span className="environment"><span />{t('Staging pilot')}</span><LanguageToggle language={language} setLanguage={setLanguage} /></div></header>
      <div className="chat-scroll">
        {!messages.length && <section className="empty">
          <div className="agent-mark"><ShieldCheck size={38} strokeWidth={1.4} /></div>
          <span className="overline">{t('THREAT ASSESSMENT AGENT')}</span>
          <h2>{t(allowed ? 'A new assessment.' : 'Security starts with access.')}</h2>
          <div className="status-label">{t(checking ? 'Verifying pilot access...' : allowed ? 'Ready' : 'Internal pilot / authorized members only')}</div>
          {!account && <button className="primary sign-in" onClick={signIn}><LogIn size={18} />{t('Sign in with Microsoft')}</button>}
        </section>}
        <div className="messages" role="log" aria-label={t('Conversation')} aria-live="polite" aria-relevant="additions">
          {messages.map((message, index) => <article className={`message ${message.role}`} key={index}>
            <div className="message-heading"><span>{t(message.role === 'user' ? 'YOU' : 'ASSESSMENT AGENT')}</span>{message.role === 'assistant' && <CopyAnswer text={message.text} t={t} />}</div>
            {message.role === 'assistant' ? <Markdown remarkPlugins={[remarkGfm]} skipHtml components={{
              a: ({ children, href }) => <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>,
              img: () => null,
            }}>{message.text}</Markdown> : <p className="user-text">{message.text}</p>}
          </article>)}
          {busy && <div className="pending" role="status"><span className="pulse" />{t('Assessment in progress')}</div>}
          <div ref={end} />
        </div>
      </div>
      <footer className="composer-area">
        {error && <div className="error" role="alert">{errorText(language, error)}</div>}
        {allowed && <details className="demo-queries" open={!messages.length}>
          <summary>{t('Synthetic demo queries')}</summary>
          <div className="demo-query-list">
            {queriesForLanguage(language).map(sample => <button key={sample.id} type="button" disabled={busy || Boolean(draft)}
              title={sample.prompt} onClick={() => { setDraft(sample.prompt); composer.current?.focus(); }}>
              <MessageSquare size={16} aria-hidden="true" /><span>{sample.title}</span>
            </button>)}
          </div>
        </details>}
        <form className="composer" onSubmit={send}>
          <textarea ref={composer} aria-label={t('Assessment message')} placeholder={t('Describe the incident or ask a follow-up...')} value={draft} maxLength={8000} rows={3} disabled={!allowed || busy}
            onChange={event => setDraft(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); send(event); } }} />
          <div className="composer-bottom"><span>{draft.length.toLocaleString(language)} / {(8000).toLocaleString(language)}</span>{busy
            ? <ToolButton label={t('Stop response')} onClick={() => abort.current?.abort()} type="button"><Square size={18} /></ToolButton>
            : <button className="send" title={t('Send message')} aria-label={t('Send message')} disabled={!allowed || !draft.trim()} type="submit"><ArrowUp size={21} /></button>}</div>
        </form>
        <div className="disclaimer">{t('Synthetic or approved pilot data only. Verify recommendations before action.')} <span aria-label={t('Application version')}>v{import.meta.env.VITE_APP_VERSION || '0.0.0-dev'}</span></div>
      </footer>
    </main>
  </div>;
}

async function start() {
  const response = await fetch('/api/config');
  if (!response.ok) throw new Error('Configuration is unavailable.');
  const config = await response.json();
  const auth = new PublicClientApplication({
    auth: { clientId: config.clientId, authority: `https://login.microsoftonline.com/${config.tenantId}`, redirectUri: window.location.origin },
    cache: { cacheLocation: 'sessionStorage' },
  });
  await auth.initialize();
  const result = await auth.handleRedirectPromise();
  const account = result?.account ?? auth.getAllAccounts()[0] ?? null;
  if (account) auth.setActiveAccount(account);
  createRoot(document.getElementById('root')).render(<Chat auth={auth} config={config} initialAccount={account} />);
}

function StartupError() {
  const { language, setLanguage, t } = useLanguage();
  return <div className="startup-error"><LanguageToggle language={language} setLanguage={setLanguage} />
    <p role="alert">{t('The assessment workspace could not load. Refresh to try again.')}</p></div>;
}

start().catch(() => {
  createRoot(document.getElementById('root')).render(<StartupError />);
});