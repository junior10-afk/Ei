export class TimerWidget {
  private timerHudEl: HTMLElement | null = null;
  private timerDisplayEl: HTMLElement | null = null;
  private timerProgressEl: HTMLElement | null = null;
  private timerCancelBtnEl: HTMLElement | null = null;

  private timerInterval: any = null;
  private totalDuration: number = 0;
  private targetEndTime: number = 0;
  private onCancelCallback: () => void;

  constructor(onCancel: () => void) {
    this.onCancelCallback = onCancel;
    this.timerHudEl = document.getElementById('timer-hud');
    this.timerDisplayEl = document.getElementById('timer-display');
    this.timerProgressEl = document.getElementById('timer-progress');
    this.timerCancelBtnEl = document.getElementById('timer-hud-cancel');

    if (this.timerCancelBtnEl) {
      this.timerCancelBtnEl.addEventListener('click', () => {
        this.onCancelCallback();
        this.hide();
      });
    }
  }

  public start(id: string, label: string, durationSeconds: number, endTime?: number) {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
    }

    this.totalDuration = durationSeconds > 0 ? durationSeconds : 60;
    this.targetEndTime = endTime ? endTime * 1000 : Date.now() + durationSeconds * 1000;

    if (this.timerHudEl) {
      this.timerHudEl.classList.remove('hidden');
    }

    this.updateDisplay();

    this.timerInterval = setInterval(() => {
      const remaining = Math.max(0, Math.ceil((this.targetEndTime - Date.now()) / 1000));
      if (remaining <= 0) {
        this.triggerEnd(label);
      } else {
        this.updateDisplay();
      }
    }, 250);
  }

  private updateDisplay() {
    const remaining = Math.max(0, Math.ceil((this.targetEndTime - Date.now()) / 1000));
    const mins = Math.floor(remaining / 60);
    const secs = remaining % 60;
    const timeStr = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;

    if (this.timerDisplayEl) {
      this.timerDisplayEl.innerText = timeStr;
      if (remaining <= 10) {
        this.timerDisplayEl.style.color = remaining % 2 === 0 ? '#ff3366' : '#00e5ff';
      } else {
        this.timerDisplayEl.style.color = '#00e5ff';
      }
    }

    if (this.timerProgressEl && this.totalDuration > 0) {
      const pct = Math.min(100, Math.max(0, (remaining / this.totalDuration) * 100));
      this.timerProgressEl.style.width = `${pct}%`;
    }
  }

  public triggerEnd(label?: string) {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }

    if (this.timerDisplayEl) {
      this.timerDisplayEl.innerText = 'FINISH';
      this.timerDisplayEl.style.color = '#ff3366';
    }

    if (this.timerProgressEl) {
      this.timerProgressEl.style.width = '0%';
    }

    setTimeout(() => {
      this.hide();
    }, 4000);
  }

  public hide() {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
    if (this.timerHudEl) {
      this.timerHudEl.classList.add('hidden');
    }
  }
}
