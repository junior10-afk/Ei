import {
  getAllOrbPresets,
  getPresetsByCategory,
  OrbPreset,
  OrbCategory
} from '../orb_presets';

export class OrbsGalleryModal {
  private panelEl: HTMLElement;
  private overlayEl: HTMLElement;
  private closeBtn: HTMLElement;
  private searchInput: HTMLInputElement;
  private gridEl: HTMLElement;
  private filterButtons: NodeListOf<HTMLButtonElement>;

  private activePresetId: string = 'cyber_blue';
  private currentFilter: string = 'all';
  private currentSearch: string = '';
  private onSelectCallback: (preset: OrbPreset) => void;

  constructor(onSelect: (preset: OrbPreset) => void) {
    this.onSelectCallback = onSelect;

    this.panelEl = document.getElementById('orbs-panel')!;
    this.overlayEl = document.getElementById('orbs-overlay')!;
    this.closeBtn = document.getElementById('orbs-close')!;
    this.searchInput = document.getElementById('orbs-search') as HTMLInputElement;
    this.gridEl = document.getElementById('orbs-grid')!;
    this.filterButtons = document.querySelectorAll<HTMLButtonElement>('.orbs-filter-btn');

    this.bindEvents();
    this.render();
  }

  private bindEvents() {
    // Fermeture
    const close = () => this.hide();
    this.closeBtn?.addEventListener('click', close);
    this.overlayEl?.addEventListener('click', close);

    // Raccourci Échap
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !this.panelEl.classList.contains('hidden')) {
        this.hide();
      }
    });

    // Recherche en temps réel
    this.searchInput?.addEventListener('input', () => {
      this.currentSearch = this.searchInput.value.toLowerCase().trim();
      this.render();
    });

    // Filtres par catégorie
    this.filterButtons.forEach((btn) => {
      btn.addEventListener('click', () => {
        this.filterButtons.forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        this.currentFilter = btn.getAttribute('data-filter') || 'all';
        this.render();
      });
    });
  }

  public show() {
    this.panelEl.classList.remove('hidden');
    if (this.searchInput) {
      setTimeout(() => this.searchInput.focus(), 150);
    }
  }

  public hide() {
    this.panelEl.classList.add('hidden');
  }

  public toggle() {
    if (this.panelEl.classList.contains('hidden')) {
      this.show();
    } else {
      this.hide();
    }
  }

  public setActivePreset(presetId: string) {
    this.activePresetId = presetId;
    this.updateActiveCards();
  }

  private updateActiveCards() {
    const cards = this.gridEl.querySelectorAll('.orb-card');
    cards.forEach((card) => {
      const id = card.getAttribute('data-preset-id');
      if (id === this.activePresetId) {
        card.classList.add('active-orb');
        const badge = card.querySelector('.orb-status-badge');
        if (badge) badge.textContent = 'ACTIF';
      } else {
        card.classList.remove('active-orb');
        const badge = card.querySelector('.orb-status-badge');
        if (badge) badge.textContent = 'CHOISIR';
      }
    });
  }

  private hexToCss(hex: number): string {
    return `#${hex.toString(16).padStart(6, '0')}`;
  }

  public render() {
    if (!this.gridEl) return;
    this.gridEl.innerHTML = '';

    const allPresets = getAllOrbPresets();

    const filtered = allPresets.filter((preset) => {
      // Filtre catégorie
      if (this.currentFilter !== 'all' && preset.category !== this.currentFilter) {
        return false;
      }
      // Filtre recherche texte
      if (this.currentSearch) {
        const fullText = `${preset.name} ${preset.category} ${preset.description} ${preset.animation}`.toLowerCase();
        if (!fullText.includes(this.currentSearch)) {
          return false;
        }
      }
      return true;
    });

    if (filtered.length === 0) {
      this.gridEl.innerHTML = `
        <div class="orbs-empty-state">
          <span>◈ AUCUN ORBE NE CORRESPOND À « ${this.currentSearch} »</span>
        </div>
      `;
      return;
    }

    filtered.forEach((preset) => {
      const card = document.createElement('div');
      card.className = `orb-card ${preset.id === this.activePresetId ? 'active-orb' : ''}`;
      card.setAttribute('data-preset-id', preset.id);

      const idleColor = this.hexToCss(preset.palette.idle);
      const listenColor = this.hexToCss(preset.palette.listening);
      const thinkColor = this.hexToCss(preset.palette.thinking);
      const speakColor = this.hexToCss(preset.palette.speaking);

      card.innerHTML = `
        <div class="orb-card-glow" style="background: radial-gradient(circle at center, ${idleColor}22 0%, transparent 70%);"></div>
        <div class="orb-card-header">
          <div class="orb-card-identity">
            <span class="orb-icon">${preset.icon}</span>
            <div class="orb-titles">
              <div class="orb-name">${preset.name}</div>
              <span class="orb-cat-badge">${preset.category}</span>
            </div>
          </div>
          <span class="orb-status-badge">${preset.id === this.activePresetId ? 'ACTIF' : 'CHOISIR'}</span>
        </div>
        <p class="orb-desc">${preset.description}</p>
        <div class="orb-card-footer">
          <div class="orb-palette-preview" title="Palette: Veille / Écoute / Réflexion / Parole">
            <span class="palette-label">SPECTRE</span>
            <div class="orb-dots">
              <span class="orb-dot" style="background: ${idleColor};" title="Veille"></span>
              <span class="orb-dot" style="background: ${listenColor};" title="Écoute"></span>
              <span class="orb-dot" style="background: ${thinkColor};" title="Réflexion"></span>
              <span class="orb-dot" style="background: ${speakColor};" title="Parole"></span>
            </div>
          </div>
          <span class="orb-anim-tag">PHYSIQUE: ${preset.animation.toUpperCase()}</span>
        </div>
      `;

      card.addEventListener('click', () => {
        this.setActivePreset(preset.id);
        this.onSelectCallback(preset);
      });

      this.gridEl.appendChild(card);
    });
  }
}
