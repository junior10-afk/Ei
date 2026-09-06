export class SettingsPanel {
  private element: HTMLElement;
  private onSaveCallback: (settings: Record<string, any>) => void;

  constructor(onSave: (settings: Record<string, any>) => void) {
    this.element = document.getElementById('settings-panel')!;
    this.onSaveCallback = onSave;

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
    const nameInput = document.getElementById('setting-user-name') as HTMLInputElement;
    const cityInput = document.getElementById('setting-city') as HTMLInputElement;
    const voiceSelect = document.getElementById('setting-voice') as HTMLSelectElement;
    const presetSelect = document.getElementById('setting-orb-preset') as HTMLSelectElement;
    const themeSelect = document.getElementById('setting-orb-theme') as HTMLSelectElement;
    const animSelect = document.getElementById('setting-orb-animation') as HTMLSelectElement;
    const qualitySelect = document.getElementById('setting-orb-quality') as HTMLSelectElement;
    const wakeWordsInput = document.getElementById('setting-wake-words') as HTMLInputElement;

    if (nameInput && data.user_name) nameInput.value = data.user_name;
    if (cityInput && data.user_city) cityInput.value = data.user_city;
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

    this.onSaveCallback(newSettings);
    this.hide();
  }
}
