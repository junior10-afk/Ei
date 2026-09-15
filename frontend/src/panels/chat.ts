export class ChatPanel {
  private element: HTMLElement;
  private messagesContainer: HTMLElement;
  private currentStreamMsg: HTMLElement | null = null;
  private currentStreamBody: HTMLElement | null = null;
  private streamText: string = '';

  constructor() {
    this.element = document.getElementById('chat-panel') || document.createElement('div');
    this.messagesContainer = document.getElementById('chat-messages') || document.createElement('div');

    const closeBtn = document.getElementById('close-chat-btn');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => this.hide());
    }
  }

  public toggle() {
    this.element.classList.toggle('hidden');
  }

  public show() {
    this.element.classList.remove('hidden');
  }

  public hide() {
    this.element.classList.add('hidden');
  }

  private escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  private renderMarkdown(raw: string): string {
    // 1. Protection des blocs de code
    const codeBlocks: string[] = [];
    let text = raw.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (_, lang, code) => {
      const idx = codeBlocks.length;
      const safeCode = this.escapeHtml(code.trim());
      const langLabel = lang ? `<span class="code-lang">${lang}</span>` : '';
      codeBlocks.push(`<pre class="code-block">${langLabel}<code>${safeCode}</code></pre>`);
      return `@@CODE_BLOCK_${idx}@@`;
    });

    // 2. Échapper le HTML restant
    text = this.escapeHtml(text);

    // 3. Code inline `code`
    text = text.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');

    // 4. Titres ###, ##, #
    text = text.replace(/^### (.*$)/gim, '<h4 class="md-h4">$1</h4>');
    text = text.replace(/^## (.*$)/gim, '<h3 class="md-h3">$1</h3>');
    text = text.replace(/^# (.*$)/gim, '<h2 class="md-h2">$1</h2>');

    // 5. Gras & Italique
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');

    // 6. Listes à puces
    text = text.replace(/^\s*[-*]\s+(.*$)/gim, '<li class="md-li">$1</li>');

    // 7. Retours à la ligne
    text = text.replace(/\n/g, '<br>');

    // 8. Restauration des blocs de code
    text = text.replace(/@@CODE_BLOCK_(\d+)@@/g, (_, idx) => codeBlocks[parseInt(idx)] || '');

    return text;
  }

  public addMessage(sender: 'user' | 'assistant' | 'action', text: string) {
    const msg = document.createElement('div');
    msg.className = `chat-msg ${sender}`;

    const label = sender === 'user' ? 'Vous' : (sender === 'assistant' ? 'EI' : 'Action Système');
    const strong = document.createElement('strong');
    strong.textContent = `${label}: `;
    msg.appendChild(strong);

    const body = document.createElement('div');
    body.className = 'msg-body';
    if (sender === 'assistant' || sender === 'action') {
      body.innerHTML = this.renderMarkdown(text);
    } else {
      body.textContent = text;
    }
    msg.appendChild(body);

    this.messagesContainer.appendChild(msg);
    this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
  }

  public appendStreamingToken(token: string, isFinal?: boolean) {
    if (!this.currentStreamMsg) {
      this.currentStreamMsg = document.createElement('div');
      this.currentStreamMsg.className = 'chat-msg assistant streaming';

      const strong = document.createElement('strong');
      strong.textContent = 'EI: ';
      this.currentStreamMsg.appendChild(strong);

      this.currentStreamBody = document.createElement('div');
      this.currentStreamBody.className = 'msg-body';
      this.currentStreamMsg.appendChild(this.currentStreamBody);

      this.messagesContainer.appendChild(this.currentStreamMsg);
      this.streamText = '';
    }

    this.streamText += token;
    if (this.currentStreamBody) {
      this.currentStreamBody.innerHTML = this.renderMarkdown(this.streamText);
    }
    this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;

    if (isFinal) {
      this.currentStreamMsg.classList.remove('streaming');
      this.currentStreamMsg = null;
      this.currentStreamBody = null;
      this.streamText = '';
    }
  }
}

