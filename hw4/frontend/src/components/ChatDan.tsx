import { FormEvent, useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import HandsomeDan from "./HandsomeDan";
import { ChatProduct, claimChat, clearChatHistory, fetchChatHistory, formatPrice, sendChat } from "../api";
import { useAuth } from "../AuthContext";
import { usePicks } from "../PicksContext";

interface Message {
  role: "user" | "dan";
  text: string;
  products?: ChatProduct[];
  signupInvite?: boolean;
  factsChecked?: number;
  corrected?: boolean;
}

const GREETING = "What can I help you with?";

export default function ChatDan() {
  const { user, ready } = useAuth();
  const { showPicks, clearPicks } = usePicks();
  const { pathname } = useLocation();
  const viewingProductId = pathname.match(/^\/products\/([^/]+)/)?.[1] ?? null;
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [ended, setEnded] = useState(false);
  const conversationId = useRef<string | null>(null);
  const previousUserId = useRef<number | null | undefined>(undefined);
  const inputRef = useRef<HTMLInputElement>(null);
  const logRef = useRef<HTMLDivElement>(null);

  // Logging in loads the shopper's saved chat (saving any guest chat first);
  // logging out clears the window.
  useEffect(() => {
    if (!ready) return;
    const prev = previousUserId.current;
    const now = user?.id ?? null;
    previousUserId.current = now;
    if (prev === now) return;

    let cancelled = false;
    (async () => {
      if (now === null) {
        conversationId.current = null;
        setMessages([]);
        setEnded(false);
        if (prev !== undefined) clearPicks(); // logged out: don't leave their searches on screen
        return;
      }
      const wasGuestChatting = prev === null && conversationId.current !== null;
      const claimed = wasGuestChatting
        ? await claimChat(conversationId.current!).then((r) => r.saved).catch(() => false)
        : false;
      if (!claimed) conversationId.current = null; // the server keeps the claimed conversation going
      const saved = await fetchChatHistory().catch(() => []);
      if (cancelled) return;
      setMessages(
        saved.map((m) => ({ role: m.role === "user" ? "user" : "dan", text: m.content, products: m.products })),
      );
      setEnded(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [user?.id, ready]); // eslint-disable-line react-hooks/exhaustive-deps

  // "J." + "." would read "J.."; drop a trailing period before punctuation follows.
  const firstName = user?.first_name.replace(/\.$/, "") ?? "";

  async function handleClearHistory() {
    if (!window.confirm("Delete your saved chat history with Handsome Dan? This can't be undone.")) return;
    try {
      await clearChatHistory();
      conversationId.current = null;
      setMessages([]);
    } catch {
      setMessages((m) => [...m, { role: "dan", text: "Ruff. I couldn't clear your history just now. Please try again." }]);
    }
  }

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, sending]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const text = draft.trim();
    if (!text || sending || ended) return;
    setMessages((m) => [...m, { role: "user", text }]);
    setDraft("");
    setSending(true);
    try {
      const res = await sendChat(text, conversationId.current, viewingProductId);
      conversationId.current = res.conversation_id;
      setMessages((m) => [
        ...m,
        {
          role: "dan",
          text: res.reply,
          products: res.products,
          signupInvite: res.signup_invite,
          factsChecked: res.facts_checked,
          corrected: res.corrected,
        },
      ]);
      if (res.picks && res.picks.products.length > 0) showPicks(res.picks);
      if (res.ended) setEnded(true);
    } catch {
      setMessages((m) => [
        ...m,
        { role: "dan", text: "Ruff. I couldn't reach the back room just now. Please try again in a moment." },
      ]);
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
  }

  if (!open) {
    return (
      <button className="dan-launcher" onClick={() => setOpen(true)} aria-label="Chat with Handsome Dan">
        <span className="dan-teaser" aria-hidden="true">{GREETING}</span>
        <span className="dan-avatar">
          <HandsomeDan title="" />
        </span>
      </button>
    );
  }

  return (
    <section className="dan-panel" aria-label="Chat with Handsome Dan">
      <header className="dan-head">
        <HandsomeDan className="dan-head-portrait" thinking={sending} />
        <div>
          <p className="dan-name">Handsome Dan</p>
          <p className="dan-role">Head of Customer Relations, Woof Division</p>
        </div>
        <button className="dan-close" onClick={() => setOpen(false)} aria-label="Close chat">×</button>
      </header>

      <div className="dan-status">
        {user ? (
          <>
            <span>Saved to your account</span>
            {messages.length > 0 && (
              <button type="button" className="link-btn" onClick={handleClearHistory}>
                Clear my chat history
              </button>
            )}
          </>
        ) : (
          <>
            <span>Guest chat · not saved</span>
            <Link to="/create-account" className="dan-status-link">Create account to save</Link>
          </>
        )}
      </div>

      <div className="dan-log" ref={logRef} aria-live="polite">
        <div className="bubble bubble-dan bubble-greeting">
          {user
            ? messages.length > 0
              ? `Welcome back, ${firstName}. Woof!`
              : `Woof, ${firstName}. ${GREETING}`
            : GREETING}
        </div>
        {messages.map((m, i) => (
          <div key={i} className={`dan-turn dan-turn-${m.role}`}>
            <div className={`bubble ${m.role === "user" ? "bubble-user" : "bubble-dan"}`}>{m.text}</div>
            {m.role === "dan" && (m.factsChecked ?? 0) > 0 && (
              <span
                className={`fact-badge${m.corrected ? " is-corrected" : ""}`}
                title="Prices, stock and colors in this reply were checked against the store's database before sending."
              >
                ✓ {m.corrected ? "Corrected & checked against the stockroom" : "Checked against the stockroom"}
              </span>
            )}
            {m.signupInvite && !user && (
              <Link to="/create-account" className="dan-invite" onClick={() => setOpen(false)}>
                <span aria-hidden="true">✦</span> Create a free account
                <span className="dan-invite-sub">Saves this chat. Takes a minute.</span>
              </Link>
            )}
            {m.products && m.products.length > 0 && (
              <ul className="dan-cards" aria-label="Suggested products">
                {m.products.map((p) => (
                  <li key={p.product_id}>
                    <Link to={`/products/${p.product_id}`} className="dan-card">
                      <img src={p.image_url} alt="" />
                      <span className="dan-card-name">{p.name}</span>
                      <span className="dan-card-price">{formatPrice(p.price)}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
        {sending && (
          <div className="bubble bubble-dan bubble-typing" role="status">
            <span className="typing-dots" aria-hidden="true">
              <span /><span /><span />
            </span>
            <span className="typing-text">Sniffing through the stockroom&hellip;</span>
          </div>
        )}
      </div>

      {ended ? (
        <p className="dan-ended" role="status">This chat has ended.</p>
      ) : (
        <form className="dan-form" onSubmit={handleSubmit}>
          <label htmlFor="dan-input" className="sr-only">Message Handsome Dan</label>
          <input
            id="dan-input"
            ref={inputRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Ask about a hoodie, a size, a gift..."
            autoComplete="off"
            maxLength={1000}
            disabled={sending}
          />
          <button type="submit" disabled={!draft.trim() || sending}>Send</button>
        </form>
      )}
    </section>
  );
}
