export class ChatPanel {
  private element: HTMLElement;
  private messagesContainer: HTMLElement;

  constructor() {
    this.element = document.getElementById('chat-panel')!;
    this.messagesContainer = document.getElementById('chat-messages')!;

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

  public addMessage(sender: 'user' | 'assistant' | 'action', text: string) {
    const msg = document.createElement('div');
    msg.className = `chat-msg ${sender}`;

    const label = sender === 'user' ? 'Vous' : (sender === 'assistant' ? 'EI' : 'Action Système');
    const strong = document.createElement('strong');
    strong.textContent = `${label}:`;
    const span = document.createElement('span');
    span.textContent = text;
    msg.appendChild(strong);
    msg.appendChild(document.createTextNode(' '));
    msg.appendChild(span);

    this.messagesContainer.appendChild(msg);
    this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
  }
}
