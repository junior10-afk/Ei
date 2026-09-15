export interface ModelOption {
  id: string;
  label: string;
  provider: string;
  model: string;
  cost: string;
  latency: string;
  description: string;
  tiers: string[];
}

/**
 * Fenêtre HUD de sélection du modèle LLM.
 * Diffusée quand le runtime demande {"type":"model_select", ...} ;
 * répond {"type":"model_select_response", model_id} au runtime.
 */
export class ModelSelectModal {
  private panelEl: HTMLElement;
  private overlayEl: HTMLElement;
  private titleEl: HTMLElement;
  private taskEl: HTMLElement;
  private tierEl: HTMLElement;
  private gridEl: HTMLElement;
  private timerEl: HTMLElement;
  private onSend: (payload: any) => void;
  private countdown: number = 0;
  private intervalId: any = null;
  private pending: boolean = false;

  constructor(onSend: (payload: any) => void) {
    this.onSend = onSend;
    this.panelEl = document.getElementById('model-select-panel')!;
    this.overlayEl = document.getElementById('model-select-overlay')!;
    this.titleEl = document.getElementById('model-select-title')!;
    this.taskEl = document.getElementById('model-select-task')!;
    this.tierEl = document.getElementById('model-select-tier')!;
    this.gridEl = document.getElementById('model-select-grid')!;
    this.timerEl = document.getElementById('model-select-timer')!;

    document.getElementById('model-select-close')?.addEventListener('click', () => this.choose('auto'));
    this.overlayEl?.addEventListener('click', () => this.choose('auto'));
    document.getElementById('model-select-auto')?.addEventListener('click', () => this.choose('auto'));

    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.pending) this.choose('auto');
    });
  }

  public show(data: {
    task: string;
    tier: string;
    tier_label?: string;
    suggested?: string | null;
    options: ModelOption[];
  }) {
    this.pending = true;
    this.titleEl.innerText = `◈ EI // QUEL MODÈLE VEUX-TU POUR CETTE TÂCHE ?`;
    this.taskEl.innerText = data.task || '';
    this.tierEl.innerText = `TÂCHE ÉVALUÉE : ${data.tier_label || data.tier}`;

    this.gridEl.innerHTML = '';
    (data.options || []).forEach((opt) => {
      const card = document.createElement('div');
      card.className = 'model-card';
      const isSuggested = opt.id === data.suggested;
      if (isSuggested) card.classList.add('suggested');
      card.innerHTML = `
        <div class="model-card-head">
          <span class="model-card-name">${this.esc(opt.label)}</span>
          ${isSuggested ? '<span class="model-card-badge">RECOMMANDÉ</span>' : ''}
        </div>
        <div class="model-card-meta">
          <span class="model-chip">${this.esc(opt.provider)}</span>
          <span class="model-chip">💰 ${this.esc(opt.cost || '-')}</span>
          <span class="model-chip">⚡ ${this.esc(opt.latency || '-')}</span>
        </div>
        <div class="model-card-desc">${this.esc(opt.description || '')}</div>
      `;
      card.addEventListener('click', () => this.choose(opt.id));
      this.gridEl.appendChild(card);
    });

    this.panelEl.classList.remove('hidden');

    // Compte à rebours de 120 s -> choix automatique par défaut
    this.countdown = 120;
    this.updateTimer();
    if (this.intervalId) clearInterval(this.intervalId);
    this.intervalId = setInterval(() => {
      this.countdown -= 1;
      this.updateTimer();
      if (this.countdown <= 0) this.choose('auto');
    }, 1000);
  }

  private updateTimer() {
    this.timerEl.innerText = `RÉPONSE AUTO DANS ${this.countdown}s`;
  }

  public close() {
    this.pending = false;
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
    this.panelEl.classList.add('hidden');
  }

  private choose(modelId: string) {
    if (!this.pending) return;
    this.close();
    this.onSend({ type: 'model_select_response', model_id: modelId });
  }

  private esc(s: string): string {
    const div = document.createElement('div');
    div.textContent = s ?? '';
    return div.innerHTML;
  }
}
