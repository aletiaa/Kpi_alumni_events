const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../app/static/profile-catalog.js'), 'utf8');

function field(value) {
  const handlers = {};
  return { value, addEventListener: (event, fn) => { handlers[event] = fn; },
    emit: event => handlers[event]() };
}
function fixture(graduation = '', selected = '') {
  const scheme = field('');
  const specialty = field(selected);
  specialty.options = ['', 'legacy', '2015', '2025'].map(classification => ({
    dataset: { classification }, selected: classification === selected,
  }));
  const year = field(graduation), birth = field(''), admission = field('');
  const fields = {
    '#specialty-classification': scheme, 'select[name="specialty"]': specialty,
    'input[name="graduation_year"]': year, 'input[name="birth_date"]': birth,
    'input[name="admission_year"]': admission,
  };
  vm.runInNewContext(source, { document: { querySelector: selector => fields[selector] } });
  return { scheme, specialty, year, birth, admission };
}

for (const [year, classification] of [['2014', 'legacy'], ['2015', '2015'],
    ['2024', '2015'], ['2025', '2025']]) {
  const f = fixture(year);
  assert.equal(f.scheme.value, classification);
}
const f = fixture();
assert.equal(f.year.min, '1965');
assert.equal(f.admission.min, '1900');
f.birth.value = '2000-01-01'; f.birth.emit('change');
assert.equal(f.year.min, '2015');
assert.equal(f.admission.min, '2000');
f.birth.value = '2002-12-05'; f.birth.emit('change');
f.admission.value = '1940'; f.admission.emit('input');
assert.equal(f.admission.min, '2002');
assert.equal(f.year.min, '2017');
f.admission.value = '2020'; f.admission.emit('input');
assert.equal(f.year.min, '2020');
f.birth.value = ''; f.birth.emit('change');
f.admission.value = ''; f.admission.emit('input');
assert.equal(f.year.min, '1965');
assert.equal(f.admission.min, '1900');
f.scheme.value = 'legacy'; f.scheme.emit('change');
f.year.value = '2025'; f.year.emit('change');
assert.equal(f.scheme.value, 'legacy');
assert.equal(f.specialty.options[3].disabled, true);
f.scheme.value = ''; f.scheme.emit('change');
assert.equal(f.specialty.options[3].disabled, false);
const existing = fixture('2025', 'legacy');
assert.equal(existing.specialty.value, 'legacy');
assert.equal(existing.scheme.value, '');
console.log('Profile catalog frontend checks passed.');
