(() => {
  const area = document.querySelector('[data-telegram-status]');
  if (!area) return;
  const text = value => typeof translatedText === 'function' ? translatedText(value, document.documentElement.lang) : value;
  let checks = 0;
  async function refresh() {
    if (document.hidden) return;
    try {
      const response = await fetch(area.dataset.telegramStatus, {cache: 'no-store'});
      if (!response.ok) return;
      const status = await response.json();
      area.querySelector('[data-bot-status]').textContent = text(status.online ? 'Бот працює' : 'Бот тимчасово недоступний');
      area.querySelector('[data-link-status]').textContent = text(status.linked ? 'Ваш акаунт підключено' : 'Ваш акаунт ще не підключено');
      if (status.linked) document.querySelectorAll('[data-telegram-link]').forEach(link => { link.hidden = true; });
    } catch { area.querySelector('[data-bot-status]').textContent = text('Не вдалося перевірити стан бота'); }
  }
  refresh();
  const timer = setInterval(() => { if (++checks >= 60) clearInterval(timer); refresh(); }, 5000);
})();
