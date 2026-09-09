export interface ApiKeyProvider {
  var: string;
  provider: string;
  label: string;
  help: string;
}

const API_PROVIDERS: ApiKeyProvider[] = [
  { var: 'GEMINI_API_KEY', provider: 'gemini', label: 'Google Gemini', help: 'aistudio.google.com/apikey' },
  { var: 'GROQ_API_KEY', provider: 'groq', label: 'Groq (Llama)', help: 'console.groq.com/keys' },
  { var: 'OPENAI_API_KEY', provider: 'openai', label: 'OpenAI', help: 'platform.openai.com/api-keys' },
  { var: 'MISTRAL_API_KEY', provider: 'mistral', label: 'Mistral', help: 'console.mistral.ai/api-keys' },
];

export class SettingsPanel {
  private element: HTMLElement;
  private onSaveCallback: (settings: Record<string, any>) => void;
  private send: (payload: any) => void;
  private apiSectionEl: HTMLElement | null;
  private lastKeyStatus: Record<string, string> = {};

  constructor(onSave: (settings: Record<string, any>) => void, send: (payload: any) => void) {
    this.element = document.getElementById('settings-panel')!;
    this.onSaveCallback = onSave;
    this.send = send;
    this.apiSectionEl = document.getElementById('api-keys-section');
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
  }
}
