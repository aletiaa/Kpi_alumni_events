const fs = require('node:fs');
const vm = require('node:vm');
const root = require('node:path').resolve(__dirname, '..');
const base = fs.readFileSync(root+'/app/templates/base.html','utf8');
const code = base.slice(base.indexOf('const I18N ='),base.indexOf('function applyLanguage'));
const context = vm.createContext({window:{}});
vm.runInContext(fs.readFileSync(root+'/app/static/ui-en.js','utf8'),context);
vm.runInContext(code+'; this.dictionary = CONTENT_TRANSLATIONS.en; this.keyed = I18N;',context);
const known = new Set([...Object.keys(context.dictionary),...Object.values(context.keyed.uk),...Object.keys(context.window.ALUMNIX_UI_EN)]);
const missing = new Set();
function walk(dir){for(const e of fs.readdirSync(dir,{withFileTypes:true})){const p=dir+'/'+e.name;if(e.isDirectory()){walk(p);continue;}if(!p.endsWith('.html')||p.endsWith('/base.html'))continue;
const html=fs.readFileSync(p,'utf8').replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi,'');
const plain=html.replace(/\{[{%][\s\S]*?[%}]\}/g,'|');
for(const m of plain.matchAll(/>([^<>]+)</g)){for(const s of m[1].split('|')){const t=s.trim();if(/[А-Яа-яІіЇїЄєҐґ]/.test(t)&&!known.has(t)) missing.add(t);}}
for(const m of html.matchAll(/(?:placeholder|title|aria-label)="([^"{}]+)"/g)){if(/[А-Яа-яІіЇїЄєҐґ]/.test(m[1])&&!known.has(m[1]))missing.add(m[1]);}
for(const block of html.matchAll(/\{[{%]([\s\S]*?)[%}]\}/g)){for(const m of block[1].matchAll(/'([^']+)'/g)){if(/[А-Яа-яІіЇїЄєҐґ]/.test(m[1])&&!known.has(m[1]))missing.add(m[1]);}}
}}
walk(root+'/app/templates');
if (missing.size) { console.error(JSON.stringify([...missing].sort(),null,2)); process.exitCode = 1; }
else { console.log('PASS: static template translation catalogue coverage'); }
vm.runInContext('Object.assign(CONTENT_TRANSLATIONS.en, window.ALUMNIX_UI_EN);', context);
const assert = require('node:assert/strict');
assert.equal(vm.runInContext('translatedText("Зберегти питання", "en")',context), 'Save question');
assert.equal(vm.runInContext('translatedText("121 - Інженерія програмного забезпечення", "en")',context), '121 - Software engineering');
assert.equal(vm.runInContext('translatedText("Це нове повідомлення від користувача", "en")',context), 'Це нове повідомлення від користувача');
console.log('PASS: complete phrases, specialties, no partial replacements');
for (const [source, expected] of [
  ['12 майбутніх', '12 upcoming'],
  ['57 переглядів', '57 views'],
  ['Місця: 8/180', 'Seats: 8/180'],
  ['Середній час відповіді сервера: 29.62 мс', 'Average server response time: 29.62 ms'],
  ['Подія 1: баланс 1, останній запис 2026-06-25 09:54', 'Event 1: balance 1, last recorded 2026-06-25 09:54']
]) assert.equal(vm.runInContext(`translatedText(${JSON.stringify(source)}, "en")`, context), expected);
console.log('PASS: dynamic counts, event seats, analytics and IoT labels');
for (const [source, expected] of [
  ['ФІОТ', 'FIOT'], ['Чехія, Прага', 'Prague, Czechia'],
  ["Комп'ютерні науки", 'Computer science'], ['Україна, Львів', 'Lviv, Ukraine']
]) assert.equal(vm.runInContext(`translatedText(${JSON.stringify(source)}, "en")`, context), expected);
console.log('PASS: mentor faculty, specialty and location translations');
