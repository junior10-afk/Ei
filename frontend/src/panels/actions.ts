export class ActionsBar {
  constructor(private onActionTrigger: (text: string) => void) {
    const quickButtons = document.querySelectorAll('.quick-action-btn');
    quickButtons.forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const text = (e.currentTarget as HTMLElement).getAttribute('data-cmd');
        if (text) {
          this.onActionTrigger(text);
        }
      });
    });
  }
}
