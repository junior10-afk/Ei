export interface ApiKeyProvider {
  var: string;
  provider: string;
  label: string;
  help: string;
}

interface ModelOptionPublic {
  id: string;
  label: string;
  provider: string;
  model: string;
  cost: string;
  latency: string;
  description: string;
  tiers: string[];
}

const API_PROVIDERS: ApiKeyProvider[] = [
  { var: 'GEMINI_API_KEY', provider: 'gemini', label: 'Google Gemini', help: 'aistudio.google.com/apikey' },
  { var: 'GROQ_API_KEY', provider: 'groq', label: 'Groq (Llama)', help: 'console.groq.com/keys' },
  { var: 'OPENAI_API_KEY', provider: 'openai', label: 'OpenAI', help: 'platform.openai.com/api-keys' },
  { var: 'MISTRAL_API_KEY', provider: 'mistral', label: 'Mistral', help: 'console.mistral.ai/api-keys' },
];

const TIERS: { id: string; label: string }[] = [
  { id: 'chat', label: '💬 Conversation' },
  { id: 'light', label: '⚡ Tâche légère' },
  { id: 'heavy', label: '🧠 Tâche complexe' },
];

export class SettingsPanel {
  private element: HTMLElement;
  private onSaveCallback: (settings: Record<string, any>) => void;
  private send: (payload: any) => void;
  private apiSectionEl: HTMLElement | null;
  private tiersSectionEl: HTMLElement | null;
  private lastKeyStatus: Record<string, string> = {};
  private catalog: ModelOptionPublic[] = [];
  private tierSelection: Record<string, string> = {};

  constructor(onSave: (settings: Record<string, any>) => void, send: (payload: any) => void) {
    this.element = document.getElementById('settings-panel')!;
    this.onSaveCallback = onSave;
    this.send = send;
    this.apiSectionEl = document.getElementById('api-keys-section');
    this.tiersSectionEl = document.getElementById('model-tiers-section');
    this.renderApiKeys();

    const closeBtn = document.getElementById('close-settings-btn');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => this.hide());
    }

    const saveBtn = document.getElementById('save-settings-btn');
    if (saveBtn) {
      saveBtn.addEventListener('click', () => this.save());
    }

    // Aperçu dynamique en direct lors des changements de sélection
    const presetSelect = document.getElementById('setting-orb-preset') as HTMLSelectElement;
    const themeSelect = document.getElementById('setting-orb-theme') as HTMLSelectElement;
    const animSelect = document.getElementById('setting-orb-animation') as HTMLSelectElement;
    const qualitySelect = document.getElementById('setting-orb-quality') as HTMLSelectElement;

    if (presetSelect) {
      presetSelect.addEventListener('change', () => {
        this.onSaveCallback({ orb_preset: presetSelect.value });
      });
    }
    if (themeSelect) {
      themeSelect.addEventListener('change', () => {
        this.onSaveCallback({ orb_theme: themeSelect.value });
      });
    }
    if (animSelect) {
      animSelect.addEventListener('change', () => {
        this.onSaveCallback({ orb_animation: animSelect.value });
      });
    }
    if (qualitySelect) {
      qualitySelect.addEventListener('change', () => {
        this.onSaveCallback({ orb_quality: qualitySelect.value });
      });
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

  public populate(data: Record<string, any>) {
    if (data.api_keys_status) {
      this.lastKeyStatus = data.api_keys_status;
      this.renderApiKeys();
      // Griser/dégriser les options de modèle selon les clés présentes
      if (this.catalog.length) this.renderTiers();
    }
    if (data.models && data.models.tiers) {
      this.tierSelection = { ...this.tierSelection, ...data.models.tiers };
      this.renderTiers();
    }
    const nameInput = document.getElementById('setting-user-name') as HTMLInputElement;
    const cityInput = document.getElementById('setting-city') as HTMLInputElement;
    const voiceSelect = document.getElementById('setting-voice') as HTMLSelectElement;
    const presetSelect = document.getElementById('setting-orb-preset') as HTMLSelectElement;
    const themeSelect = document.getElementById('setting-orb-theme') as HTMLSelectElement;
    const animSelect = document.getElementById('setting-orb-animation') as HTMLSelectElement;
    const qualitySelect = document.getElementById('setting-orb-quality') as HTMLSelectElement;
    const wakeWordsInput = document.getElementById('setting-wake-words') as HTMLInputElement;
    const modelChoiceSelect = document.getElementById('setting-model-choice-mode') as HTMLSelectElement;

    if (nameInput && data.user_name) nameInput.value = data.user_name;
    if (cityInput && data.user_city) cityInput.value = data.user_city;
    if (modelChoiceSelect && data.model_choice_mode) modelChoiceSelect.value = data.model_choice_mode;
    if (voiceSelect && data.voice) voiceSelect.value = data.voice;
    if (presetSelect && (data.orb_preset || data.orb_theme)) {
      presetSelect.value = data.orb_preset || data.orb_theme;
    }
    if (themeSelect && data.orb_theme) themeSelect.value = data.orb_theme;
    if (animSelect && data.orb_animation) animSelect.value = data.orb_animation;
    if (qualitySelect && data.orb_quality) qualitySelect.value = data.orb_quality;
    if (wakeWordsInput && data.wake_words) {
      wakeWordsInput.value = Array.isArray(data.wake_words) ? data.wake_words.join(', ') : data.wake_words;
    }
  }

  private save() {
    const nameInput = document.getElementById('setting-user-name') as HTMLInputElement;
    const cityInput = document.getElementById('setting-city') as HTMLInputElement;
    const voiceSelect = document.getElementById('setting-voice') as HTMLSelectElement;
    const presetSelect = document.getElementById('setting-orb-preset') as HTMLSelectElement;
    const themeSelect = document.getElementById('setting-orb-theme') as HTMLSelectElement;
    const animSelect = document.getElementById('setting-orb-animation') as HTMLSelectElement;
    const qualitySelect = document.getElementById('setting-orb-quality') as HTMLSelectElement;
    const wakeWordsInput = document.getElementById('setting-wake-words') as HTMLInputElement;

    const newSettings: Record<string, any> = {};
    if (nameInput) newSettings.user_name = nameInput.value.trim();
    if (cityInput) newSettings.user_city = cityInput.value.trim();
    if (voiceSelect) newSettings.voice = voiceSelect.value;
    if (presetSelect) newSettings.orb_preset = presetSelect.value;
    if (themeSelect) newSettings.orb_theme = themeSelect.value;
    if (animSelect) newSettings.orb_animation = animSelect.value;
    if (qualitySelect) newSettings.orb_quality = qualitySelect.value;
    if (wakeWordsInput) {
      newSettings.wake_words = wakeWordsInput.value.split(',').map((w) => w.trim().toLowerCase()).filter((w) => w.length > 0);
    }
    const modelChoiceSelect = document.getElementById('setting-model-choice-mode') as HTMLSelectElement;
    if (modelChoiceSelect) newSettings.model_choice_mode = modelChoiceSelect.value;

    this.onSaveCallback(newSettings);
    this.hide();
  }

  /* ── Clés API ─────────────────────────────────────────────────────────── */

  private renderApiKeys() {
    if (!this.apiSectionEl) return;
    this.apiSectionEl.innerHTML = '';

    API_PROVIDERS.forEach((p) => {
      const status = this.lastKeyStatus[p.var] || '';
      const row = document.createElement('div');
      row.className = 'api-key-row';
      row.dataset.var = p.var;

      const label = document.createElement('div');
      label.className = 'api-key-label';
      label.innerHTML = `<span class="api-key-name">${p.label}</span>
        <span class="api-key-help">${p.help}</span>`;
      row.appendChild(label);

      const input = document.createElement('input');
      input.type = 'password';
      input.className = 'setting-input api-key-input';
      input.placeholder = status ? `Clé actuelle : ${status} (coller pour remplacer)` : 'Coller la clé ici…';
      input.autocomplete = 'off';
      row.appendChild(input);

      const saveBtn = document.createElement('button');
      saveBtn.className = 'hud-btn api-key-btn';
      saveBtn.textContent = 'OK';
      saveBtn.title = 'Enregistrer dans .env';
      row.appendChild(saveBtn);

      const testBtn = document.createElement('button');
      testBtn.className = 'hud-btn api-key-btn test-btn';
      testBtn.textContent = '⚡ TESTER';
      row.appendChild(testBtn);

      const state = document.createElement('span');
      state.className = 'api-key-state' + (status ? ' has-key' : '');
      state.textContent = status ? '✔ enregistrée' : '—';
      row.appendChild(state);

      saveBtn.addEventListener('click', () => {
        const value = input.value.trim();
        if (!value) return;
        this.send({ type: 'set_api_key', var: p.var, value });
        input.value = '';
        input.placeholder = 'Enregistrement…';
        // Tester la clé tout de suite : si elle est valide, les modèles du
        // fournisseur seront automatiquement proposés pour chaque usage.
        state.className = 'api-key-state';
        state.textContent = 'test…';
        this.send({ type: 'test_api_key', provider: p.provider });
      });
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { e.preventDefault(); saveBtn.click(); }
      });
      testBtn.addEventListener('click', () => {
        state.className = 'api-key-state';
        state.textContent = 'test…';
        this.send({ type: 'test_api_key', provider: p.provider });
      });

      this.apiSectionEl.appendChild(row);
    });
  }

  public handleKeyResult(data: { provider?: string; var?: string; ok?: boolean; message?: string }) {
    if (!this.apiSectionEl) return;
    let targetVar = data.var;
    if (!targetVar && data.provider) {
      const p = API_PROVIDERS.find((x) => x.provider === data.provider);
      targetVar = p ? p.var : undefined;
    }
    if (!targetVar) return;
    const row = this.apiSectionEl.querySelector(`.api-key-row[data-var="${targetVar}"]`);
    if (!row) return;
    const state = row.querySelector('.api-key-state');
    if (state) {
      state.textContent = data.ok ? '✔ connectée' : `✘ ${data.message || 'échec'}`;
      state.className = 'api-key-state ' + (data.ok ? 'ok' : 'ko');
    }
    // Clé validée : proposer immédiatement les modèles du fournisseur
    if (data.ok && data.provider) {
      this.autoSelectProviderModels(data.provider);
    }
  }

  /* ── Modèles par usage ────────────────────────────────────────────────── */

  public setCatalog(options: ModelOptionPublic[], tiers?: Record<string, string>) {
    this.catalog = options || [];
    if (tiers) this.tierSelection = { ...this.tierSelection, ...tiers };
    this.renderTiers();
  }

  private hasProviderKey(provider: string): boolean {
    if (provider === 'ollama') return true; // local, pas de clé
    const p = API_PROVIDERS.find((x) => x.provider === provider);
    return p ? Boolean(this.lastKeyStatus[p.var]) : false;
  }

  /** Quand une clé fournisseur est newly validée, basculer les tiers dont le
   *  modèle actuel n'a pas de clé sur un modèle de ce fournisseur. */
  private autoSelectProviderModels(provider: string) {
    if (!this.catalog.length) return;
    let changed = false;
    TIERS.forEach((t) => {
      const currentId = this.tierSelection[t.id];
      const current = this.catalog.find((m) => m.id === currentId);
      const currentOk = current && this.hasProviderKey(current.provider);
      if (!currentOk) {
        const candidate = this.catalog.find((m) => m.provider === provider && (m.tiers || []).includes(t.id));
        if (candidate) {
          this.tierSelection[t.id] = candidate.id;
          changed = true;
        }
      }
    });
    this.renderTiers();
    if (changed) this.pushTierSelection();
  }

  private pushTierSelection() {
    this.send({
      type: 'update_settings',
      data: { models: { tiers: { ...this.tierSelection } } },
    });
  }

  private renderTiers() {
    if (!this.tiersSectionEl) return;
    this.tiersSectionEl.innerHTML = '';

    if (!this.catalog.length) {
      const hint = document.createElement('div');
      hint.className = 'tier-row';
      hint.innerHTML = `<span class="api-key-help">Catalogue des modèles en attente (reconnexion au runtime)…</span>`;
      this.tiersSectionEl.appendChild(hint);
      return;
    }

    TIERS.forEach((t) => {
      const models = this.catalog.filter((m) => (m.tiers || []).includes(t.id));
      if (!models.length) return;

      const row = document.createElement('div');
      row.className = 'tier-row';

      const label = document.createElement('div');
      label.className = 'api-key-label';
      label.innerHTML = `<span class="api-key-name">${t.label}</span>`;
      row.appendChild(label);

      const select = document.createElement('select');
      select.className = 'setting-input tier-select';
      models.forEach((m) => {
        const opt = document.createElement('option');
        opt.value = m.id;
        const keyOk = this.hasProviderKey(m.provider);
        opt.textContent = `${m.label} — ${m.cost}${m.latency ? ' · ' + m.latency : ''}${keyOk ? '' : ' (clé manquante)'}`;
        if (!keyOk) opt.disabled = true;
        select.appendChild(opt);
      });
      const selected = this.tierSelection[t.id];
      if (selected && models.some((m) => m.id === selected)) select.value = selected;
      select.addEventListener('change', () => {
        this.tierSelection[t.id] = select.value;
        this.pushTierSelection();
      });
      row.appendChild(select);

      this.tiersSectionEl!.appendChild(row);
    });
  }
}
