// Chrome exposes installation only when the app is eligible. Keep the control
// hidden otherwise; the browser menu remains available for manual installation.
(() => {
  const button = document.getElementById('install-app');
  const status = document.getElementById('install-status');
  const standalone = matchMedia('(display-mode: standalone)');
  let pendingPrompt;

  window.addEventListener('beforeinstallprompt', event => {
    if (standalone.matches) return;
    event.preventDefault();
    pendingPrompt = event;
    button.hidden = false;
  });

  button.addEventListener('click', async () => {
    if (!pendingPrompt) return;
    const prompt = pendingPrompt;
    pendingPrompt = null;
    button.hidden = true;
    status.textContent = '';
    try {
      await prompt.prompt();
      await prompt.userChoice;
    } catch (_) {
      status.textContent = 'To install, open your browser menu and choose Add to home screen.';
    }
  });

  window.addEventListener('appinstalled', () => {
    pendingPrompt = null;
    button.hidden = true;
    status.textContent = 'App installed.';
  });
  standalone.addEventListener('change', () => {
    if (standalone.matches) button.hidden = true;
  });
})();
