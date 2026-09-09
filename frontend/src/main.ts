import { JarvisOrb, OrbTheme, OrbAnimationStyle } from './orb';
import { IncomingMessage, AssistantStateType } from './protocol';
import { ChatPanel } from './panels/chat';
import { SettingsPanel } from './panels/settings';
import { TimerWidget } from './panels/timer';
import { OrbsGalleryModal } from './panels/orbs_modal';
import { ModelSelectModal } from './panels/model_modal';
import './style.css';

class JarvisHUD {
  private ws: WebSocket | null = null;
  private orb: JarvisOrb;
  private chatPanel: ChatPanel;
  private settingsPanel: SettingsPanel;
  private timerWidget: TimerWidget;
  private orbsModal: OrbsGalleryModal;
  private modelModal: ModelSelectModal;

  // Horloge & télémétrie
  private orbTimeEl: HTMLElement;
  private orbDateEl: HTMLElement;
  private cpuValueEl: HTMLElement;
  private ramValueEl: HTMLElement;
  private cpuHudEl: HTMLElement;
  private ramHudEl: HTMLElement;

  // Double affichage transcription
  private userSpeechHudEl: HTMLElement;
  private userSpeechTextEl: HTMLElement;
  private subtitleHudEl: HTMLElement;
  private subtitleTextEl: HTMLElement;
  private subtitleMetaEl: HTMLElement;
  private userSpeechTimeout: any = null;
  private subtitleTimeout: any = null;

  // Statut & badge
  private statusTextEl: HTMLElement;
  private connBadgeEl: HTMLElement;
  private connLabelEl: HTMLElement;

  // Contrôles inférieurs
  private micBtn: HTMLElement;
  private stopBtn: HTMLElement;
  private keyboardToggleBtn: HTMLElement;
  private keyboardHudEl: HTMLElement;
  private keyboardInputEl: HTMLInputElement;
  private keyboardCloseEl: HTMLElement;

  // Menu unifié & Répertoire commandes
  private menuBtn: HTMLElement;
  private menuDropdown: HTMLElement;
  private commandsPanel: HTMLElement;
  private commandsClose: HTMLElement;
  private commandsOverlay: HTMLElement;
  private commandsSearch: HTMLInputElement;

  private isMuted: boolean = false;
  private wsPort: number = 8765;

  constructor() {
    const orbContainer = document.getElementById('orb-container')!;
    this.orb = new JarvisOrb({ container: orbContainer });

    // 1. DOM Refs Télémétrie
    this.orbTimeEl = document.getElementById('orb-time-display')!;
    this.orbDateEl = document.getElementById('orb-date-display')!;
    this.cpuValueEl = document.getElementById('cpu-value')!;
    this.ramValueEl = document.getElementById('ram-value')!;
    this.cpuHudEl = document.getElementById('cpu-hud')!;
    this.ramHudEl = document.getElementById('ram-hud')!;

    // 2. Transcription
    this.userSpeechHudEl = document.getElementById('user-speech-hud')!;
    this.userSpeechTextEl = document.getElementById('user-speech-text')!;
    this.subtitleHudEl = document.getElementById('subtitle-hud')!;
    this.subtitleTextEl = document.getElementById('subtitle-text')!;
    this.subtitleMetaEl = document.getElementById('subtitle-meta')!;

    // 3. Statut & Connexion
    this.statusTextEl = document.getElementById('status-text')!;
    this.connBadgeEl = document.getElementById('connection-badge')!;
    this.connLabelEl = document.getElementById('connection-label')!;

    // 4. Contrôles
    this.micBtn = document.getElementById('mic-btn')!;
    this.stopBtn = document.getElementById('stop-speech-btn')!;
    this.keyboardToggleBtn = document.getElementById('keyboard-toggle-btn')!;
    this.keyboardHudEl = document.getElementById('keyboard-hud')!;
    this.keyboardInputEl = document.getElementById('keyboard-input') as HTMLInputElement;
    this.keyboardCloseEl = document.getElementById('keyboard-close')!;

    // 5. Menu & Commandes
    this.menuBtn = document.getElementById('jarvis-menu-btn')!;
    this.menuDropdown = document.getElementById('jarvis-menu-dropdown')!;
    this.commandsPanel = document.getElementById('commands-panel')!;
    this.commandsClose = document.getElementById('commands-close')!;
    this.commandsOverlay = document.getElementById('commands-overlay')!;
    this.commandsSearch = document.getElementById('commands-search') as HTMLInputElement;

    // 6. Panneaux et widgets
    this.chatPanel = new ChatPanel();
    this.orbsModal = new OrbsGalleryModal((preset) => {
      this.orb.setPreset(preset.id);
      this.send({
        type: 'update_settings',
        data: {
          orb_preset: preset.id,
          orb_theme: preset.id,
          orb_animation: preset.animation
        }
      });
      // Synchroniser les contrôles des réglages
      const settingPreset = document.getElementById('setting-orb-preset') as HTMLSelectElement;
      if (settingPreset) settingPreset.value = preset.id;
      const settingAnim = document.getElementById('setting-orb-animation') as HTMLSelectElement;
      if (settingAnim) settingAnim.value = preset.animation;
    });

    this.settingsPanel = new SettingsPanel((newSettings) => {
      if (newSettings.orb_preset) {
        const p = this.orb.setPreset(newSettings.orb_preset);
        this.orbsModal.setActivePreset(newSettings.orb_preset);
        newSettings.orb_animation = p.animation;
        newSettings.orb_theme = p.id;
      } else {
        if (newSettings.orb_theme) {
          this.orb.setTheme(newSettings.orb_theme as OrbTheme);
        }
        if (newSettings.orb_animation) {
          this.orb.setAnimationStyle(newSettings.orb_animation as OrbAnimationStyle);
        }
      }
      if (newSettings.orb_quality) {
        this.orb.setQuality(newSettings.orb_quality as 'low' | 'medium' | 'high');
      }
      this.send({ type: 'update_settings', data: newSettings });
    }, (payload) => this.send(payload));

    this.timerWidget = new TimerWidget(() => {
      this.sendUserInput('annule le minuteur');
    });

    this.modelModal = new ModelSelectModal((payload) => {
      this.send(payload);
      this.chatPanel.addMessage('action',
        payload.model_id === 'auto' ? 'Choix du modèle : automatique' : `Modèle sélectionné : ${payload.model_id}`);
    });

    this.initClock();
    this.bindEvents();
    this.connectWebSocket();
  }

  /**
   * Horloge locale temps réel et date
   */
  private initClock() {
    const update = () => {
      const now = new Date();
      this.orbTimeEl.innerText = now.toLocaleTimeString('fr-FR', { hour12: false });
      this.orbDateEl.innerText = now.toLocaleDateString('fr-FR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
      });
    };
    update();
    setInterval(update, 1000);
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

    // Plein écran
    const fullscreenBtn = document.getElementById('fullscreen-btn');
    if (fullscreenBtn) {
      fullscreenBtn.addEventListener('click', () => {
        if (!document.fullscreenElement) {
          document.documentElement.requestFullscreen().catch(() => {});
        } else {
          document.exitFullscreen().catch(() => {});
        }
      });
    }

    // Menu Déroulant
    this.menuBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      this.menuDropdown.classList.toggle('hidden');
    });

    document.addEventListener('click', (e) => {
      if (!this.menuDropdown.contains(e.target as Node) && e.target !== this.menuBtn) {
        this.menuDropdown.classList.add('hidden');
      }
    });

    // Boutons internes du menu
    document.getElementById('menu-btn-orbs')?.addEventListener('click', () => {
      this.orbsModal.show();
      this.menuDropdown.classList.add('hidden');
    });
    document.getElementById('menu-btn-theme')?.addEventListener('click', () => {
      this.settingsPanel.show();
      this.menuDropdown.classList.add('hidden');
    });
    document.getElementById('menu-btn-commands')?.addEventListener('click', () => {
      this.commandsPanel.classList.remove('hidden');
      this.menuDropdown.classList.add('hidden');
    });
    document.getElementById('menu-btn-chat')?.addEventListener('click', () => {
      this.chatPanel.toggle();
      this.menuDropdown.classList.add('hidden');
    });
    document.getElementById('menu-btn-settings')?.addEventListener('click', () => {
      this.settingsPanel.toggle();
      this.menuDropdown.classList.add('hidden');
    });

    // Terminal Clavier Direct
    this.keyboardToggleBtn.addEventListener('click', () => {
      this.toggleKeyboard();
    });

    this.keyboardCloseEl.addEventListener('click', () => {
      this.keyboardHudEl.classList.add('hidden');
    });

    this.keyboardInputEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const text = this.keyboardInputEl.value.trim();
        if (text) {
          this.sendUserInput(text);
          this.keyboardInputEl.value = '';
          this.keyboardHudEl.classList.add('hidden');
        }
      } else if (e.key === 'Escape') {
        this.keyboardHudEl.classList.add('hidden');
      }
    });

    // Raccourci clavier global 'k' ou 'Entrée' pour ouvrir la saisie
    window.addEventListener('keydown', (e) => {
      if (e.key === 'k' && document.activeElement !== this.keyboardInputEl && document.activeElement?.tagName !== 'INPUT') {
        e.preventDefault();
        this.toggleKeyboard();
      }
    });

    // Répertoire des commandes (modal)
    const closeCommands = () => this.commandsPanel.classList.add('hidden');
    this.commandsClose.addEventListener('click', closeCommands);
    this.commandsOverlay.addEventListener('click', closeCommands);

    // Filtrage instantané des commandes
    this.commandsSearch.addEventListener('input', () => {
      const q = this.commandsSearch.value.toLowerCase().trim();
      const items = document.querySelectorAll('.cmd-item');
      items.forEach((item) => {
        const el = item as HTMLElement;
        const text = el.innerText.toLowerCase();
        el.style.display = text.includes(q) ? 'flex' : 'none';
      });
    });

    // Clic sur une commande de la liste
    document.querySelectorAll('.cmd-item').forEach((item) => {
      item.addEventListener('click', () => {
        const cmd = item.getAttribute('data-cmd') || (item as HTMLElement).innerText;
        this.sendUserInput(cmd);
        closeCommands();
      });
    });

    // Fermer les bulles de transcription au clic
    this.userSpeechHudEl.addEventListener('click', () => {
      this.userSpeechHudEl.classList.add('hidden');
    });
    this.subtitleHudEl.addEventListener('click', () => {
      this.subtitleHudEl.classList.add('hidden');
    });
  }

  private toggleKeyboard() {
    this.keyboardHudEl.classList.toggle('hidden');
    if (!this.keyboardHudEl.classList.contains('hidden')) {
      setTimeout(() => this.keyboardInputEl.focus(), 100);
    }
  }

  private sendUserInput(text: string) {
    this.showUserSpeech(text);
    this.chatPanel.addMessage('user', text);
    this.send({ type: 'user_input', text });
  }

  private showUserSpeech(text: string) {
    if (this.userSpeechTimeout) clearTimeout(this.userSpeechTimeout);
    this.userSpeechTextEl.innerText = text;
    this.userSpeechHudEl.classList.remove('hidden');

    // Masquage automatique après 8 secondes sans parole
    this.userSpeechTimeout = setTimeout(() => {
      this.userSpeechHudEl.classList.add('hidden');
    }, 8000);
  }

  private showSubtitle(text: string) {
    if (this.subtitleTimeout) clearTimeout(this.subtitleTimeout);
    this.subtitleTextEl.innerText = text;
    this.subtitleHudEl.classList.remove('hidden');
    this.subtitleMetaEl.innerText = 'TRANSMITTING_VOICE_STREAM...';

    this.subtitleTimeout = setTimeout(() => {
      this.subtitleHudEl.classList.add('hidden');
    }, 9000);
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
      this.connBadgeEl.className = 'connected';
      this.connLabelEl.innerText = 'ONLINE';
      // Récupérer le catalogue des modèles pour les réglages
      this.send({ type: 'get_models' });
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
      this.connBadgeEl.className = 'disconnected';
      this.connLabelEl.innerText = 'RECONNEXION';
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

      case 'system_stats':
        this.cpuValueEl.innerText = `${Math.round(msg.cpu)}%`;
        this.ramValueEl.innerText = `${Math.round(msg.ram)}%`;
        this.cpuHudEl.classList.toggle('stat-critical', msg.cpu > 90);
        this.ramHudEl.classList.toggle('stat-critical', msg.ram > 90);
        break;

      case 'user_speech':
        this.showUserSpeech(msg.text);
        this.chatPanel.addMessage('user', msg.text);
        break;

      case 'subtitle':
        this.showSubtitle(msg.text);
        if (msg.text) {
          this.chatPanel.addMessage('assistant', msg.text);
        }
        break;

      case 'mic_state':
        this.isMuted = msg.muted;
        if (this.isMuted) {
          this.micBtn.classList.add('muted');
          this.micBtn.classList.remove('active');
          this.micBtn.title = 'Microphone coupé (Muet)';
        } else {
          this.micBtn.classList.remove('muted');
          this.micBtn.classList.add('active');
          this.micBtn.title = 'Microphone actif (Cliquez pour couper)';
        }
        break;

      case 'action':
        this.chatPanel.addMessage('action', `Exécution de [${msg.action}]`);
        if (msg.action === 'timer_start' && msg.params) {
          this.timerWidget.start(msg.params.id, msg.params.label, msg.params.duration, msg.params.end_time);
        } else if (msg.action === 'timer_end') {
          this.timerWidget.triggerEnd(msg.params?.label);
        } else if (msg.action === 'timer_cancel') {
          this.timerWidget.hide();
        } else if (msg.action === 'open_panel' && msg.params) {
          if (msg.params.panel === 'settings') this.settingsPanel.show();
          else if (msg.params.panel === 'chat') this.chatPanel.show();
          else if (msg.params.panel === 'commands') this.commandsPanel.classList.remove('hidden');
          else if (msg.params.panel === 'orbs') this.orbsModal.show();
        } else if (msg.action === 'close_panel' && msg.params) {
          if (msg.params.panel === 'settings') this.settingsPanel.hide();
          else if (msg.params.panel === 'chat') this.chatPanel.hide();
          else if (msg.params.panel === 'commands') this.commandsPanel.classList.add('hidden');
          else if (msg.params.panel === 'orbs') this.orbsModal.hide();
          else {
            this.settingsPanel.hide();
            this.chatPanel.hide();
            this.commandsPanel.classList.add('hidden');
            this.orbsModal.hide();
          }
        } else if (msg.action === 'set_orb' && msg.params?.preset_id) {
          this.orb.setPreset(msg.params.preset_id);
          this.orbsModal.setActivePreset(msg.params.preset_id);
          const settingPreset = document.getElementById('setting-orb-preset') as HTMLSelectElement;
          if (settingPreset) settingPreset.value = msg.params.preset_id;
        }
        break;

      case 'model_select':
        this.modelModal.show({
          task: msg.task,
          tier: msg.tier,
          tier_label: msg.tier_label,
          suggested: msg.suggested,
          options: msg.options,
        });
        break;

      case 'model_select_closed':
        this.modelModal.close();
        break;

      case 'model_used':
        this.chatPanel.addMessage('action', `Modèle actif : ${msg.label} (${msg.tier})`);
        break;

      case 'api_key_result':
        this.settingsPanel.handleKeyResult(msg as any);
        break;

      case 'models_catalog':
        this.settingsPanel.setCatalog(msg.options, msg.tiers);
        break;

      case 'long_response':
        this.chatPanel.addMessage('assistant', msg.text);
        this.chatPanel.show();
        break;

      case 'settings':
        this.settingsPanel.populate(msg.data);
        const presetKey = msg.data.orb_preset || msg.data.orb_theme;
        if (presetKey) {
          this.orb.setPreset(presetKey);
          this.orbsModal.setActivePreset(presetKey);
        } else {
          if (msg.data.orb_theme) {
            this.orb.setTheme(msg.data.orb_theme as OrbTheme);
          }
          if (msg.data.orb_animation) {
            this.orb.setAnimationStyle(msg.data.orb_animation as OrbAnimationStyle);
          }
        }
        if (msg.data.orb_quality) {
          this.orb.setQuality(msg.data.orb_quality as 'low' | 'medium' | 'high');
        }
        break;
    }
  }

  private applyState(state: AssistantStateType) {
    this.orb.setState(state);
    const labels: Record<AssistantStateType, string> = {
      idle: 'en veille',
      listening: 'écoute active...',
      thinking: 'réflexion...',
      speaking: 'synthèse vocale'
    };
    this.statusTextEl.innerText = labels[state] || state.toLowerCase();
  }
}

// Initialisation au chargement du DOM
window.addEventListener('DOMContentLoaded', () => {
  new JarvisHUD();
});
