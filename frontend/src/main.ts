import { JarvisOrb } from './orb';
import { IncomingMessage, AssistantStateType } from './protocol';
import { ChatPanel } from './panels/chat';
import { SettingsPanel } from './panels/settings';
import { ActionsBar } from './panels/actions';
import './style.css';

class JarvisHUD {
  private ws: WebSocket | null = null;
  private orb: JarvisOrb;
  private chatPanel: ChatPanel;
  private settingsPanel: SettingsPanel;
  private actionsBar: ActionsBar;

  private stateBadge: HTMLElement;
  private transcriptEl: HTMLElement;
  private subtitleEl: HTMLElement;
  private micBtn: HTMLElement;
  private stopBtn: HTMLElement;
  private inputEl: HTMLInputElement;

  private isMuted: boolean = false;
  private wsPort: number = 8765;

  constructor() {
    const orbContainer = document.getElementById('orb-container')!;
    this.orb = new JarvisOrb({ container: orbContainer });

    this.stateBadge = document.getElementById('status-text')!;
    this.transcriptEl = document.getElementById('speech-transcript')!;
    this.subtitleEl = document.getElementById('speech-subtitle')!;
    this.micBtn = document.getElementById('mic-toggle-btn')!;
    this.stopBtn = document.getElementById('stop-speech-btn')!;
    this.inputEl = document.getElementById('user-text-input') as HTMLInputElement;

    this.chatPanel = new ChatPanel();
    this.settingsPanel = new SettingsPanel((newSettings) => {
      this.send({ type: 'update_settings', data: newSettings });
    });
    this.actionsBar = new ActionsBar((cmd) => {
      this.sendUserInput(cmd);
    });

    this.bindEvents();
    this.connectWebSocket();
  }

  private bindEvents() {
    // Bouton Microphone (Mute / Unmute)
    this.micBtn.addEventListener('click', () => {
      this.send({ type: 'toggle_mic' });
    });

    // Bouton Arrêt Audio (Stop TTS)
    this.stopBtn.addEventListener('click', () => {
      this.send({ type: 'stop_audio' });
    });

    // Bouton Panneau Chat
    const chatToggle = document.getElementById('toggle-chat-btn');
    if (chatToggle) {
      chatToggle.addEventListener('click', () => this.chatPanel.toggle());
    }

    // Bouton Panneau Settings
    const settingsToggle = document.getElementById('toggle-settings-btn');
    if (settingsToggle) {
      settingsToggle.addEventListener('click', () => this.settingsPanel.toggle());
    }

    // Saisie clavier (même pipeline que la voix)
    this.inputEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const text = this.inputEl.value.trim();
        if (text) {
          this.sendUserInput(text);
          this.inputEl.value = '';
        }
      }
    });
  }

  private sendUserInput(text: string) {
    this.chatPanel.addMessage('user', text);
    this.transcriptEl.innerText = `« ${text} »`;
    this.send({ type: 'user_input', text });
  }

  private send(data: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  private connectWebSocket() {
    const wsUrl = `ws://${window.location.hostname || '127.0.0.1'}:${this.wsPort}`;
    console.log(`[HUD] Connexion WebSocket vers ${wsUrl}...`);

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('[HUD] Connecté au Runtime vocal.');
      this.stateBadge.innerText = 'Prêt';
    };

    this.ws.onmessage = (event) => {
      try {
        const msg: IncomingMessage = JSON.parse(event.data);
        this.handleMessage(msg);
      } catch (e) {
        console.error('[HUD] Erreur parsing message:', e);
      }
    };

    this.ws.onclose = () => {
      console.warn('[HUD] Connexion perdue. Reconnexion dans 2s...');
      this.stateBadge.innerText = 'Déconnecté';
      setTimeout(() => this.connectWebSocket(), 2000);
    };
  }

  private handleMessage(msg: IncomingMessage) {
    switch (msg.type) {
      case 'set_state':
        this.applyState(msg.state);
        break;

      case 'volume':
        this.orb.setVolume(msg.value);
        break;

      case 'user_speech':
        this.transcriptEl.innerText = `« ${msg.text} »`;
        this.chatPanel.addMessage('user', msg.text);
        break;

      case 'subtitle':
        this.subtitleEl.innerText = msg.text;
        if (msg.text) {
          this.chatPanel.addMessage('assistant', msg.text);
        }
        break;

      case 'mic_state':
        this.isMuted = msg.muted;
        if (this.isMuted) {
          this.micBtn.classList.add('muted');
          this.micBtn.classList.remove('active');
          this.micBtn.innerText = '🔇 Micro Muet';
        } else {
          this.micBtn.classList.remove('muted');
          this.micBtn.classList.add('active');
          this.micBtn.innerText = '🎤 Micro Actif';
        }
        break;

      case 'action':
        this.chatPanel.addMessage('action', `Exécution de [${msg.action}]`);
        break;

      case 'settings':
        this.settingsPanel.populate(msg.data);
        break;
    }
  }

  private applyState(state: AssistantStateType) {
    this.orb.setState(state);
    const labels: Record<AssistantStateType, string> = {
      idle: 'En veille',
      listening: 'Écoute active...',
      thinking: 'Traitement...',
      speaking: 'Synthèse vocale'
    };
    this.stateBadge.innerText = labels[state] || state.toUpperCase();

    // Mettre à jour la couleur du voyant de statut
    const dot = document.querySelector('.status-dot') as HTMLElement;
    if (dot) {
      if (state === 'thinking') dot.style.background = '#b300ff';
      else if (state === 'speaking') dot.style.background = '#00ffff';
      else if (state === 'listening') dot.style.background = '#00b0ff';
      else dot.style.background = '#00e5ff';
    }
  }
}

// Initialisation au chargement du DOM
window.addEventListener('DOMContentLoaded', () => {
  new JarvisHUD();
});
