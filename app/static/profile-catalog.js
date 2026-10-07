(() => {
  const scheme = document.querySelector('#specialty-classification');
  const specialty = document.querySelector('select[name="specialty"]');
  const year = document.querySelector('input[name="graduation_year"]');
  const birth = document.querySelector('input[name="birth_date"]');
  const admission = document.querySelector('input[name="admission_year"]');
  if (!scheme || !specialty || !year) return;
  let manuallyChosen = false;
  function filter() {
    for (const option of specialty.options) {
      const excluded = Boolean(scheme.value && option.dataset.classification &&
        option.dataset.classification !== scheme.value && !option.selected);
      option.hidden = excluded;
      option.disabled = excluded;
    }
  }
  function suggest() {
    if (manuallyChosen) return;
    const value = Number(year.value);
    if (!specialty.value && value >= 1900) {
      scheme.value = value < 2015 ? 'legacy' : value <= 2024 ? '2015' : '2025';
    }
    filter();
  }
  scheme.addEventListener('change', () => { manuallyChosen = true; filter(); });
  specialty.addEventListener('change', filter);
  year.addEventListener('change', suggest);
  function dateLimits() {
    const birthYear = birth && birth.value ? Number(birth.value.split('-')[0]) : 0;
    const entryYear = admission && admission.value ? Number(admission.value) : 0;
    if (admission) admission.min = String(Math.max(1900, birthYear));
    year.min = String(Math.max(1965, birthYear ? birthYear + 15 : 1965, entryYear));
  }
  if (birth) birth.addEventListener('change', dateLimits);
  if (admission) admission.addEventListener('input', dateLimits);
  dateLimits();
  suggest();
})();
