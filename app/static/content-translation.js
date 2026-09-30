(() => {
  const originals = new WeakMap();
  const requests = new Map();
  let generation = 0;
  let queued = false;
  function notice(show) {
    let element = document.getElementById('translation-notice');
    if (!element && show) {
      element = document.createElement('p');
      element.id = 'translation-notice';
      element.className = 'alert alert-info';
      element.setAttribute('role', 'status');
      element.setAttribute('data-no-translate', '');
      element.textContent = 'Some English translations are unavailable. Original text is shown.';
      document.querySelector('main')?.prepend(element);
    }
    if (element) element.hidden = !show;
  }
  async function apply() {
    const revision = generation;
    const english = document.documentElement.lang === 'en';
    const groups = new Map();
    document.querySelectorAll('[data-content-field]').forEach(el => {
      if (!originals.has(el)) originals.set(el, el.textContent);
      const original = originals.get(el);
      const local = english ? translatedText(original, 'en') : original;
      if (!english || local !== original || !/[А-Яа-яІіЇїЄєҐґ]/.test(original)) {
        if (el.textContent !== local) el.textContent = local;
        return;
      }
      const key = el.dataset.contentKind + '/' + el.dataset.contentId;
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(el);
    });
    if (!english) { notice(false); return; }
    let failed = false;
    // Limit concurrent requests by processing one record at a time.
    for (const [key, elements] of groups) {
      if (revision !== generation) return;
      if (!requests.has(key)) {
        requests.set(key, fetch('/api/translations/' + key, {headers: {Accept: 'application/json'}})
          .then(async response => { if (!response.ok) return null; return (await response.json()).fields; })
          .catch(() => null));
      }
      const fields = await requests.get(key);
      if (!fields) requests.delete(key);
      if (revision !== generation || document.documentElement.lang !== 'en') return;
      for (const el of elements) {
        const value = fields?.[el.dataset.contentField];
        if (typeof value === 'string') {
          if (el.textContent !== value) el.textContent = value;
        } else { failed = true; }
      }
    }
    notice(failed);
  }
  function schedule() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => { queued = false; apply(); });
  }
  document.addEventListener('alumnix:language', () => { generation++; schedule(); });
  new MutationObserver(records => {
    if (records.some(record => [...record.addedNodes].some(node => node.nodeType === 1 &&
      (node.matches('[data-content-field]') || node.querySelector('[data-content-field]'))))) schedule();
  }).observe(document.body, {childList: true, subtree: true});
  schedule();
})();
