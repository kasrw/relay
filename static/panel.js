/* Small enhancements without changing existing form actions or API behavior. */
(() => {
  const panelBase = document.querySelector('meta[name="panel-base"]')?.content || '/relay';
  const mountedPath = location.pathname;
  const path = mountedPath === panelBase ? '/' : mountedPath.startsWith(panelBase + '/') ? mountedPath.slice(panelBase.length) : mountedPath;
  document.querySelectorAll('.topnav a.plain').forEach(link => {
    const rawTarget = link.getAttribute('href');
    const target = rawTarget === panelBase ? '/' : rawTarget.startsWith(panelBase + '/') ? rawTarget.slice(panelBase.length) : rawTarget;
    const active = target === '/' ? path === '/' || path.startsWith('/webhooks/') : path === target || path.startsWith(target + '/');
    if (active) link.setAttribute('aria-current', 'page');
  });
  if (path === '/settings') document.querySelector('.settings-link')?.setAttribute('aria-current', 'page');
  const themeButton = document.querySelector('#theme-toggle');
  if (themeButton) {
    const describeTheme = () => {
      const light = document.body.classList.contains('light');
      themeButton.textContent = light ? 'Use dark theme' : 'Use light theme';
      themeButton.setAttribute('aria-label', themeButton.textContent);
      const description = document.querySelector('#theme-description');
      if (description) description.textContent = light ? 'Light theme is enabled.' : 'Dark theme is enabled.';
    };
    describeTheme();
    themeButton.addEventListener('click', describeTheme);
  }
  function toast(message) {
    document.querySelector('.ui-toast')?.remove();
    const notice = document.createElement('div');
    notice.className = 'ui-toast'; notice.setAttribute('role', 'status');
    notice.textContent = message; document.body.append(notice);
    setTimeout(() => notice.remove(), 2600);
  }
  async function copy(value) {
    try {
      if (navigator.clipboard && window.isSecureContext) await navigator.clipboard.writeText(value);
      else {
        const input = document.createElement('textarea');
        input.value = value; input.style.position = 'fixed'; input.style.opacity = '0';
        document.body.append(input); input.select();
        const done = document.execCommand('copy'); input.remove();
        if (!done) throw new Error('Copy unavailable');
      }
      toast('Copied to clipboard');
    } catch { toast('Select the text and copy it manually.'); }
  }
  const escapeHtml = value => value.replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  function paintCodeLine(line, language) {
    const patterns = {
      python: /(#.*$|(?:[rRuUbBfF]{0,2})(?:"""[\s\S]*?"""|'''[\s\S]*?'''|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')|@[A-Za-z_]\w*|\b(?:and|as|assert|async|await|break|class|continue|def|del|elif|else|except|finally|for|from|global|if|import|in|is|lambda|nonlocal|not|or|pass|raise|return|try|while|with|yield|True|False|None)\b|\b\d+(?:\.\d+)?\b|\b[A-Za-z_]\w*(?=\s*\()|(?:==|!=|<=|>=|->|:=|[=+\-*\/%<>]))/g,
      json: /("(?:\\.|[^"\\])*"\s*:|"(?:\\.|[^"\\])*"|\b(?:true|false|null)\b|-?\b\d+(?:\.\d+)?\b)/g,
      shell: /(#.*$|"(?:\\.|[^"\\])*"|'[^']*'|\$[A-Za-z_]\w*|--?[A-Za-z][\w-]*|\b(?:sudo|python|pip|curl|cd|export|source)\b|\b\d+\b)/g,
    };
    const regex = patterns[language];
    if (!regex) return escapeHtml(line);
    let result = '', cursor = 0, match;
    while ((match = regex.exec(line))) {
      result += escapeHtml(line.slice(cursor, match.index));
      const token = match[0];
      let type = 'operator';
      if (token.startsWith('#')) type = 'comment';
      else if (language === 'json') {
        type = token.endsWith(':') ? 'property' : /^"/.test(token) ? 'string' : /^(?:true|false|null)$/.test(token) ? 'constant' : 'number';
      } else if (language === 'shell') {
        type = token.startsWith('#') ? 'comment' : /^['"]/.test(token) ? 'string' : token.startsWith('$') ? 'variable' : token.startsWith('-') ? 'flag' : /^\d/.test(token) ? 'number' : 'command';
      } else if (token.startsWith('@')) type = 'decorator';
      else if (/^(?:and|as|assert|async|await|break|class|continue|def|del|elif|else|except|finally|for|from|global|if|import|in|is|lambda|nonlocal|not|or|pass|raise|return|try|while|with|yield)$/.test(token)) type = 'keyword';
      else if (/^(?:True|False|None)$/.test(token)) type = 'constant';
      else if (/^(?:[rRuUbBfF]{0,2})(?:['"]|""")/.test(token)) type = 'string';
      else if (/^\d/.test(token)) type = 'number';
      else if (/^[A-Za-z_]/.test(token)) type = /^(?:print|len|str|int|float|bool|list|dict|set|tuple|range|open|super|type|isinstance|enumerate|zip|map|filter|Exception|ValueError)$/.test(token) ? 'builtin' : 'function';
      result += `<span class="tok-${type}">${escapeHtml(token)}</span>`;
      cursor = regex.lastIndex;
    }
    return result + escapeHtml(line.slice(cursor));
  }
  function highlightCode(code, language) {
    const source = code.textContent;
    code.innerHTML = source.split('\n').map(line => `<span class="code-line">${paintCodeLine(line, language)}</span>`).join('\n');
    code.closest('pre')?.classList.add('syntax-code');
  }
  document.querySelectorAll('.secret-key, pre code').forEach(code => {
    const button = document.createElement('button');
    button.type = 'button'; button.className = 'button copy-control';
    button.textContent = code.classList.contains('secret-key') ? 'Copy key' : 'Copy example';
    button.addEventListener('click', () => copy(code.textContent));
    const pre = code.closest('.docs-main pre');
    const language = [...code.classList].find(name => name.startsWith('language-'))?.slice(9);
    if (pre && language && ['python', 'shell', 'json'].includes(language)) {
      highlightCode(code, language);
      const toolbar = document.createElement('div');
      toolbar.className = 'code-toolbar';
      const label = document.createElement('span');
      label.className = `code-language lang-${language}`;
      label.textContent = language === 'shell' ? 'SHELL' : language.toUpperCase();
      toolbar.append(label, button);
      pre.before(toolbar);
    } else (code.closest('pre') || code).after(button);
  });
  const url = document.querySelector('#hook-url');
  const urlButton = url?.nextElementSibling;
  if (urlButton?.tagName === 'BUTTON') {
    urlButton.removeAttribute('onclick'); urlButton.addEventListener('click', () => copy(url.value));
  }
  document.querySelectorAll('[data-copy]').forEach(button => button.addEventListener('click', () => copy(button.dataset.copy)));
  document.querySelectorAll('.auth-user-card').forEach(card => {
    const heading = card.querySelector('strong');
    const hint = card.querySelector('.hint');
    if (heading && hint && !card.querySelector('.status-pill')) {
      const pill = document.createElement('span');
      const disabled = hint.textContent.includes('· disabled ·');
      pill.className = 'status-pill' + (disabled ? ' disabled' : '');
      pill.textContent = disabled ? 'Disabled' : 'Active'; heading.after(pill);
    }
    const forms = [...card.querySelectorAll(':scope > .auth-expiry')];
    if (forms.length) {
      const details = document.createElement('details');
      const summary = document.createElement('summary'); summary.textContent = 'Manage license and credentials';
      details.append(summary); forms.forEach(form => details.append(form)); card.append(details);
    }
  });
  const mode = document.querySelector('.auth-user-create select[name=auth_mode]');
  const password = document.querySelector('.auth-user-create input[name=password]');
  if (mode && password) {
    const update = () => {
      const needsPassword = mode.value !== 'product_key';
      password.disabled = !needsPassword; password.required = needsPassword;
      password.minLength = needsPassword ? 8 : 0;
      password.closest('label').hidden = !needsPassword;
    };
    mode.addEventListener('change', update); update();
  }
  const duration = document.querySelector('.auth-user-create select[name=duration_days]');
  const expiry = document.querySelector('.auth-user-create input[name=expires_at]');
  if (duration && expiry) {
    const update = () => { expiry.disabled = duration.value !== '0'; };
    duration.addEventListener('change', update); update();
  }
  const bulk = document.querySelector('#bulk-users');
  if (bulk) {
    const boxes = [...document.querySelectorAll('input[name=user_ids]')];
    const all = document.querySelector('#select-all-users');
    const actionSelect = bulk.querySelector('[name=action]');
    const daysLabel = bulk.querySelector('.bulk-days');
    if (daysLabel) {
      const showDays = () => { daysLabel.hidden = actionSelect.value !== 'extend'; };
      actionSelect.addEventListener('change', showDays); showDays();
    }
    const update = () => {
      const count = boxes.filter(box => box.checked).length;
      document.querySelector('#selected-count').textContent = `${count} selected`;
      all.checked = count > 0 && count === boxes.length;
      all.indeterminate = count > 0 && count < boxes.length;
    };
    all.addEventListener('change', () => { boxes.forEach(box => { box.checked = all.checked; }); update(); });
    boxes.forEach(box => box.addEventListener('change', update));
    bulk.addEventListener('submit', event => {
      const count = boxes.filter(box => box.checked).length;
      const action = bulk.querySelector('[name=action]').value;
      if (!count) { event.preventDefault(); toast('Select at least one user.'); return; }
      if (action === 'delete' && !confirm(`Permanently delete ${count} selected users?`)) event.preventDefault();
    });
  }
  const storageForm = document.querySelector(`form[action="${panelBase}/settings/storage"]`);
  storageForm?.addEventListener('submit', event => {
    const days = Number(storageForm.querySelector('[name=retention_days]').value);
    if (days > 0 && !confirm(`Automatically delete messages and files older than ${days} days across all webhooks?`)) event.preventDefault();
  });
  if (path === '/' || path.startsWith('/webhooks/')) {
    let baseline = null;
    let polling = false;
    let stopped = false;
    const activeHook = Number(path.match(/^\/webhooks\/(\d+)/)?.[1] || 0);
    const poll = async () => {
      if (polling || stopped || document.hidden) return;
      polling = true;
      try {
        const response = await fetch(`${panelBase}/panel/live`, {cache:'no-store', credentials:'same-origin'});
        if (response.status === 401) { stopped = true; return; }
        if (!response.ok) return;
        const payload = await response.json();
        const current = new Map(payload.webhooks.map(hook => [hook.id, hook]));
        for (const hook of payload.webhooks) {
          const card = document.querySelector(`a.hookbox[href="${panelBase}/webhooks/${hook.id}"]`);
          if (card) {
            let badge = card.querySelector('.unread-badge');
            if (hook.unread > 0) {
              if (!badge) { badge = document.createElement('span'); badge.className = 'unread-badge'; card.querySelector('.hook-title-row').append(badge); }
              badge.textContent = `${hook.unread} new`; badge.setAttribute('aria-label',`${hook.unread} unread messages`);
            } else badge?.remove();
            const count = card.querySelector('.hook-count');
            if (count) {
              [...count.childNodes].filter(node => node.nodeType === Node.TEXT_NODE).forEach(node => node.remove());
              count.append(document.createTextNode(`${hook.users} users`));
            }
          }
        }
        if (baseline) {
          const changed = payload.webhooks.some(hook => (activeHook ? hook.id === activeHook : true) && hook.latest > (baseline.get(hook.id)?.latest || 0));
          if (changed) {
            let banner = document.querySelector('#live-update');
            if (!banner) {
              banner = document.createElement('div'); banner.id = 'live-update'; banner.className = 'notice live-banner'; banner.setAttribute('role','status');
              const text = document.createElement('span'); text.textContent = 'New messages received.';
              const button = document.createElement('button'); button.type = 'button'; button.className = 'button'; button.textContent = 'Show updates';
              button.addEventListener('click', () => location.reload());
              banner.append(text,button); document.querySelector('main').prepend(banner);
            }
          }
        }
        baseline = current;
      } catch { /* Recover automatically on the next poll. */ }
      finally { polling = false; }
    };
    poll(); setInterval(poll, 5000);
    document.addEventListener('visibilitychange', () => { if (!document.hidden) poll(); });
  }
})();
