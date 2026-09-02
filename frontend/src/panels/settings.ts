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

    if (nameInput && data.user_name) nameInput.value = data.user_name;
    if (cityInput && data.user_city) cityInput.value = data.user_city;
    if (voiceSelect && data.voice) voiceSelect.value = data.voice;
  }

  private save() {
    const nameInput = document.getElementById('setting-user-name') as HTMLInputElement;
    const cityInput = document.getElementById('setting-city') as HTMLInputElement;
    const voiceSelect = document.getElementById('setting-voice') as HTMLSelectElement;

    const newSettings: Record<string, any> = {};
    if (nameInput) newSettings.user_name = nameInput.value.trim();
    if (cityInput) newSettings.user_city = cityInput.value.trim();
    if (voiceSelect) newSettings.voice = voiceSelect.value;

    this.onSaveCallback(newSettings);
    this.hide();
  }
}
