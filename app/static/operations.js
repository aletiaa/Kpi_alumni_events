(() => {
  const script = document.currentScript;
  const translate = () => {
    const en = document.documentElement.lang === 'en';
    document.querySelectorAll('[data-ops-uk][data-ops-en]').forEach(el => {
      el.textContent = en ? el.dataset.opsEn : el.dataset.opsUk;
    });
  };
  document.addEventListener('DOMContentLoaded', () => {
    translate();
    new MutationObserver(translate).observe(document.documentElement, {attributes:true, attributeFilter:['lang']});
    document.querySelectorAll('form[action^="/admin/"]').forEach(form => {
      if (!form.action.endsWith('/delete')) return;
      form.addEventListener('submit', event => {
        if (event.defaultPrevented) return;
        const en = document.documentElement.lang === 'en';
        if (!form.onsubmit && !confirm(en ? 'Delete this record and its dependent data?' : 'Видалити цей запис і пов’язані дані?')) {
          event.preventDefault(); return;
        }
        for (const [name, value] of [['confirm','yes'], ['csrf',script.dataset.csrf]]) {
          if (!form.querySelector('[name="'+name+'"]')) {
            const input = document.createElement('input'); input.type='hidden'; input.name=name; input.value=value;
            form.append(input);
          }
        }
      });
    });
  });
})();
