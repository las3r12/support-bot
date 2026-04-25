const BOT_API = 'https://localhost:5000';

class BotWidget extends HTMLElement {
  constructor() {
    super();
    const shadow = this.attachShadow({ mode: 'open' });
    this.history = [];
    shadow.innerHTML = `
      <div class="chat-window">

        <div class="chat-header">
          <div class="header-avatar">🤖</div>
          <div class="header-info">
            <div class="header-name">Assistant</div>
            <div class="header-status">
              <span class="online-dot"></span>
              Online · ready to help
            </div>
          </div>
          <button class="hide-btn" id="hideBtn" title="Minimize">
            <svg viewBox="0 0 24 24"><path d="M19 13H5v-2h14v2z"/></svg>
          </button>
        </div>

        <div class="messages" id="messages">
          <div class="empty-state" id="emptyState">
            <div class="empty-icon">💬</div>
            <strong>Ask me anything</strong>
            <span>Type a question below to get started</span>
          </div>
          <div class="typing-indicator" id="typingIndicator">
            <div class="typing-bubble">
              <span class="typing-dot"></span>
              <span class="typing-dot"></span>
              <span class="typing-dot"></span>
            </div>
          </div>
        </div>

        <div class="chat-input-area">
          <div class="input-row">
            <input type="text" class="chat-input" id="chatInput" placeholder="Type your question…" />
            <button class="send-btn" id="sendBtn" disabled>
              <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
            </button>
          </div>
        </div>

      </div>

      <style>
        :host {
          --accent:      #22c55e;
          --accent-dk:   #16a34a;
          --border:      #bbf7d0;
          --bg:          #f0fdf4;
          --card:        #ffffff;
          --input-bg:    #f9fffb;
          --text:        #064e3b;
          --muted:       #6b9e85;
          --focus:       rgba(34,197,94,0.2);
          --font:        'DM Sans', system-ui, sans-serif;
          display: block;
          position: fixed;
          right: 20px;
          bottom: 20px;
          z-index: 9999;
          font-family: var(--font);
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }

        /* ── Window ── */
        .chat-window {
          width: 320px;
          height: 440px;
          background: var(--card);
          border-radius: 20px;
          border: 1px solid var(--border);
          box-shadow:
            0 20px 48px rgba(0,0,0,0.14),
            0 4px 12px rgba(34,197,94,0.1),
            inset 0 1px 0 rgba(255,255,255,0.9);
          display: flex;
          flex-direction: column;
          overflow: hidden;
        }

        /* ── Header ── */
        .chat-header {
          padding: 14px 16px 12px;
          border-bottom: 1px solid var(--border);
          background: linear-gradient(to bottom, #fff, #fafffe);
          display: flex;
          align-items: center;
          gap: 10px;
          flex-shrink: 0;
        }

        .header-avatar {
          width: 34px;
          height: 34px;
          border-radius: 10px;
          background: linear-gradient(135deg, var(--accent), #4ade80);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 16px;
          box-shadow: 0 3px 8px rgba(34,197,94,0.35);
          flex-shrink: 0;
        }

        .header-info { flex: 1; }

        .header-name {
          font-size: 0.88rem;
          font-weight: 600;
          color: var(--text);
          line-height: 1.2;
        }

        .header-status {
          font-size: 0.68rem;
          color: var(--muted);
          display: flex;
          align-items: center;
          gap: 4px;
          margin-top: 2px;
        }

        .online-dot {
          width: 5px;
          height: 5px;
          border-radius: 50%;
          background: var(--accent);
          animation: blink 2s ease-in-out infinite;
        }

        @keyframes blink {
          0%, 100% { opacity: 1; }
          50%       { opacity: 0.4; }
        }

        /* ── Messages ── */
        .messages {
          flex: 1;
          overflow-y: auto;
          padding: 14px 12px;
          display: flex;
          flex-direction: column;
          gap: 10px;
          scroll-behavior: smooth;
          scrollbar-width: thin;
          scrollbar-color: var(--border) transparent;
        }

        .messages::-webkit-scrollbar { width: 4px; }
        .messages::-webkit-scrollbar-track { background: transparent; }
        .messages::-webkit-scrollbar-thumb {
          background: var(--border);
          border-radius: 99px;
        }
        .messages::-webkit-scrollbar-thumb:hover { background: var(--accent); }

        .messages {
          overscroll-behavior: contain;
        }

        /* ── Bubbles ── */
        .msg {
          display: flex;
          flex-direction: column;
          max-width: 84%;
          animation: popIn 0.18s ease-out;
        }

        @keyframes popIn {
          from { opacity: 0; transform: translateY(6px) scale(0.97); }
          to   { opacity: 1; transform: translateY(0) scale(1); }
        }

        .msg.user { align-self: flex-end; align-items: flex-end; }
        .msg.bot  { align-self: flex-start; align-items: flex-start; }

        .bubble {
          padding: 9px 13px;
          border-radius: 16px;
          font-size: 0.83rem;
          line-height: 1.5;
          white-space: pre-wrap;
          word-break: break-word;
        }

        .msg.user .bubble {
          background: linear-gradient(135deg, var(--accent), #34d569);
          color: #fff;
          border-bottom-right-radius: 4px;
          box-shadow: 0 3px 10px rgba(34,197,94,0.3);
        }

        .msg.bot .bubble {
          background: var(--bg);
          color: var(--text);
          border: 1px solid var(--border);
          border-bottom-left-radius: 4px;
          box-shadow: 0 2px 5px rgba(0,0,0,0.04);
        }

        .msg-time {
          font-size: 0.6rem;
          color: var(--muted);
          margin-top: 3px;
          padding: 0 3px;
        }

        /* ── Empty state ── */
        .empty-state {
          flex: 1;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 5px;
          color: var(--muted);
          font-size: 0.76rem;
          text-align: center;
          padding: 16px;
        }

        .empty-icon { font-size: 1.8rem; margin-bottom: 2px; opacity: 0.6; }

        /* ── Typing indicator ── */
        .typing-indicator { display: none; }
        .typing-indicator.visible { display: flex; }

        .typing-bubble {
          background: var(--bg);
          border: 1px solid var(--border);
          border-radius: 16px;
          border-bottom-left-radius: 4px;
          padding: 10px 14px;
          display: flex;
          gap: 4px;
          align-items: center;
          box-shadow: 0 2px 5px rgba(0,0,0,0.04);
        }

        .typing-dot {
          width: 5px;
          height: 5px;
          border-radius: 50%;
          background: var(--muted);
          animation: typingDot 1.2s ease-in-out infinite;
        }
        .typing-dot:nth-child(2) { animation-delay: 0.2s; }
        .typing-dot:nth-child(3) { animation-delay: 0.4s; }

        @keyframes typingDot {
          0%, 60%, 100% { transform: translateY(0); opacity: 0.35; }
          30%            { transform: translateY(-4px); opacity: 1; }
        }

        /* ── Input area ── */
        .chat-input-area {
          padding: 10px 12px;
          border-top: 1px solid var(--border);
          background: linear-gradient(to top, #fff, #fafffe);
          flex-shrink: 0;
        }

        .input-row {
          display: flex;
          align-items: center;
          gap: 8px;
          background: var(--input-bg);
          border: 1.5px solid var(--border);
          border-radius: 12px;
          padding: 8px 8px 8px 12px;
          transition: border 0.2s ease, box-shadow 0.2s ease;
        }

        .input-row:focus-within {
          border-color: var(--accent);
          box-shadow: 0 0 0 3px var(--focus);
          background: #fff;
        }

        .chat-input {
          flex: 1;
          border: none;
          background: transparent;
          font-family: var(--font);
          font-size: 0.85rem;
          color: var(--text);
          outline: none;
        }

        .chat-input::placeholder { color: var(--muted); opacity: 0.7; }

        .send-btn {
          width: 32px;
          height: 32px;
          border-radius: 9px;
          background: linear-gradient(135deg, var(--accent), #4ade80);
          border: none;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
          transition: transform 0.15s ease, box-shadow 0.15s ease, opacity 0.15s ease;
          box-shadow: 0 3px 8px rgba(34,197,94,0.4);
        }

        .send-btn:hover:not(:disabled) {
          transform: translateY(-1px);
          box-shadow: 0 5px 14px rgba(34,197,94,0.5);
        }

        .send-btn:disabled { opacity: 0.4; cursor: not-allowed; }

        .send-btn svg {
          width: 14px;
          height: 14px;
          fill: white;
          transform: translateX(1px);
        }

        .hide-btn {
          width: 28px;
          height: 28px;
          border-radius: 8px;
          background: transparent;
          border: 1px solid var(--border);
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
          transition: background 0.15s ease, border-color 0.15s ease;
          margin-left: auto;
        }
        .hide-btn:hover {
          background: var(--bg);
          border-color: var(--accent);
        }
        .hide-btn svg {
          width: 14px;
          height: 14px;
          fill: var(--muted);
        }

        /* ── Minimized state ── */
        :host(.minimized) .chat-window {
          height: auto;
        }
        :host(.minimized) .messages,
        :host(.minimized) .chat-input-area {
          display: none;
        }
        :host(.minimized) .hide-btn svg {
          transform: rotate(180deg);
        }
      </style>
    `;
  }

  
  connectedCallback() {
    const shadow      = this.shadowRoot;
    const sendBtn     = shadow.getElementById('sendBtn');
    const input       = shadow.getElementById('chatInput');
    const messages    = shadow.getElementById('messages');
    const typingEl    = shadow.getElementById('typingIndicator');

    fetch(`${BOT_API}/bot_info/${this.getAttribute('token')}`)
      .then(r => r.json())
      .then(data => {
        if (data.bot_name) shadow.querySelector('.header-name').textContent = data.bot_name;
        if (data.hello_msg) this.addMessage(data.hello_msg, 'bot', messages, typingEl);
      })
      .catch(() => {});


    const hideBtn = shadow.getElementById('hideBtn');
    hideBtn.addEventListener('click', () => {
      this.classList.toggle('minimized');
    });

    const chatWindow = shadow.querySelector('.chat-window');
    chatWindow.addEventListener('wheel', (e) => {
      e.stopPropagation();
      e.preventDefault();
      messages.scrollTop += e.deltaY;
    }, { passive: false });

    input.addEventListener('input', () => {
      sendBtn.disabled = !input.value.trim();
    });

    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !sendBtn.disabled) {
        e.preventDefault();
        this.sendMessage(input, messages, typingEl, sendBtn);
      }
    });

    sendBtn.addEventListener('click', () => {
      this.sendMessage(input, messages, typingEl, sendBtn);
    });
  }

  getTime() {
    return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  addMessage(text, role, messages, typingEl) {
    const empty = messages.querySelector('#emptyState');
    if (empty) empty.remove();

    const msg    = document.createElement('div');
    msg.className = `msg ${role}`;

    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.textContent = text;

    const time = document.createElement('div');
    time.className = 'msg-time';
    time.textContent = this.getTime();

    msg.appendChild(bubble);
    msg.appendChild(time);

    this.history.push({ user: role, text: text });
    messages.insertBefore(msg, typingEl);
    messages.scrollTop = messages.scrollHeight;
  }

  getLastHist(){
    if (this.history.length <= 10) return this.history;
    return this.history.slice(-10);
  }

  async sendMessage(input, messages, typingEl, sendBtn) {
    const question = input.value.trim();
    if (!question) return;

    this.addMessage(question, 'user', messages, typingEl);
    input.value = '';
    sendBtn.disabled = true;

    typingEl.classList.add('visible');
    messages.scrollTop = messages.scrollHeight;

    try {
      const res = await fetch(`${BOT_API}/ask_question`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question,
          token: this.getAttribute('token'),
          history: this.getLastHist()
        })
      });

      const data = await res.json();
      typingEl.classList.remove('visible');
      console.log(res.status);
      if (res.ok) {
        this.addMessage(data.answer, 'bot', messages, typingEl);
      } else if (res.status === 429) {
        this.addMessage(data.error || 'Too many requests. Please try again later.', 'bot', messages, typingEl);
      } else {
        this.addMessage(data.error || 'An error occurred.', 'bot', messages, typingEl);
      }
    } catch (err) {
      typingEl.classList.remove('visible');
      this.addMessage('Network error — please try again.', 'bot', messages, typingEl);
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  customElements.define('bot-widget', BotWidget);
});