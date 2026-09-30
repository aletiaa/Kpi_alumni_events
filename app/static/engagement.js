(() => {
  const script = document.currentScript;
  const label = text => translatedText(text, document.documentElement.lang);
  if (script.dataset.role === 'admin') {
    document.querySelectorAll('form').forEach(form => {
      const body = form.querySelector('[name="description"], [name="content"]');
      const title = form.querySelector('[name="title"]');
      if (!body || !title) return;
      let summary = form.querySelector('[name="short_description"]');
      const group = document.createElement('div'); group.className = 'col-12 my-3';
      if (!summary) {
        const caption = document.createElement('label'); caption.textContent = label('Короткий опис');
        summary = document.createElement('textarea'); summary.name = 'short_description';
        summary.className = 'form-control'; summary.rows = 2; summary.maxLength = 500;
        summary.id = 'generated-summary'; caption.htmlFor = summary.id;
        summary.value = document.getElementById('saved-short-description')?.value || '';
        group.append(caption, summary);
      }
      const button = document.createElement('button'); button.type = 'button';
      button.className = 'btn btn-outline-primary mt-2'; button.textContent = label('Згенерувати короткий опис');
      const status = document.createElement('p'); status.setAttribute('role', 'status');
      group.append(button, status); form.append(group);
      button.addEventListener('click', async () => {
        button.disabled = true; status.textContent = '';
        try {
          const data = new FormData(); data.set('title', title.value); data.set('body', body.value);
          const response = await fetch('/admin/description-preview', {method:'POST', body:data});
          if (!response.ok) throw new Error();
          summary.value = (await response.json()).summary;
          status.textContent = label('Опис готовий. Збережіть зміни.');
        } catch { status.textContent = label('Не вдалося згенерувати опис. Перевірте текст.'); }
        finally { button.disabled = false; }
      });
    });
    return;
  }
  const section = location.pathname === '/events' ? 'event' : location.pathname === '/news' ? 'news' : null;
  if (!section) return;
  const key = 'suggestions:' + script.dataset.user + ':' + section;
  try { if (sessionStorage.getItem(key)) return; } catch {}
  setTimeout(async () => {
    try {
      const response = await fetch('/api/personal-suggestions?section=' + section);
      if (!response.ok) return;
      const {items} = await response.json(); if (!items.length) return;
      const dialog = document.createElement('dialog');
      dialog.style.cssText='width:min(520px,calc(100% - 32px));max-height:80vh;overflow:auto;border:1px solid #b8cce0;border-radius:6px;padding:20px';
      const title = document.createElement('h2'); title.className='h4'; title.id='suggestion-title'; title.textContent=label('Для вас');
      dialog.setAttribute('aria-labelledby', title.id);
      const close = document.createElement('button'); close.className='btn-close float-end'; close.setAttribute('aria-label',label('Закрити'));
      close.addEventListener('click',()=>dialog.close()); dialog.append(close,title);
      for (const item of items) {
        const link=document.createElement('a'); link.href=item.url; link.className='d-flex align-items-center gap-3 py-3 border-bottom';
        const img=document.createElement('img'); img.src=item.image; img.alt=''; img.width=80; img.height=60; img.style.objectFit='cover';
        const name=document.createElement('span'); name.textContent=item.title;
        name.dataset.contentKind=item.kind; name.dataset.contentId=item.id; name.dataset.contentField='title';
        link.append(img,name); dialog.append(link);
      }
      document.body.append(dialog);
      try { sessionStorage.setItem(key,'1'); } catch {}
      dialog.showModal();
    } catch { /* Suggestions must not prevent browsing. */ }
  }, 4000);
})();
