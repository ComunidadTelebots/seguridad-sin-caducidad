(() => {
  const form = document.getElementById('support-form');
  const api = window.community.api;
  const es = () => document.documentElement.lang === 'es';
  const text = (a,b) => es() ? a : b;
  const panel = document.createElement('div');
  panel.className = 'telegram-vote';
  panel.innerHTML = '<button type="button" class="btn btn-ghost" id="telegram-vote" disabled></button><p class="support-selection-note" id="telegram-note"></p><p id="telegram-state" role="status" class="support-selection-note"></p><a id="telegram-open" class="btn btn-ghost" target="_blank" rel="noopener noreferrer" hidden></a>';
  form.append(panel);
  const button = document.getElementById('telegram-vote');
  const state = document.getElementById('telegram-state');
  const link = document.getElementById('telegram-open');
  let ready = false, pending = null, timer, checking = false;
  function render() {
    button.textContent = text('Verificar mi voto por Telegram', 'Verify my vote via Telegram');
    document.getElementById('telegram-note').textContent = ready
      ? text('Sin correo. Elige país y tecnología, abre @cintiabot y confirma. Un voto por cuenta de Telegram; usa un solo canal de apoyo.', 'No email needed. Choose a country and technology, open @cintiabot and confirm. One vote per Telegram account; use only one support channel.')
      : text('La verificación por Telegram no está disponible ahora.', 'Telegram verification is currently unavailable.');
    link.textContent = text('Abrir @cintiabot →', 'Open @cintiabot →');
  }
  async function post(path, body) {
    const response = await fetch(api + path, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal:AbortSignal.timeout(10000)});
    if (!response.ok) throw new Error(String(response.status));
    return response.json();
  }
  function stop() { clearTimeout(timer); pending = null; link.hidden = true; }
  async function check() {
    if (!pending || checking) return;
    checking = true;
    try {
      const result = await post('/api/telegram/status', {token:pending.token});
      if (['confirmed','duplicate'].includes(result.state)) {
        state.textContent = result.state === 'confirmed' ? text('Voto confirmado en Telegram. ¡Gracias!', 'Vote confirmed on Telegram. Thank you!') : text('Esta cuenta de Telegram ya tiene un voto. No se ha sumado otro.', 'This Telegram account has already voted. No additional vote was counted.');
        stop(); window.community.refresh();
      }
    } catch (error) {
      if (error.message === '410' || error.message === '404') {
        state.textContent = text('El enlace ha caducado. Solicita uno nuevo.', 'The link has expired. Request a new one.'); stop();
      } else state.textContent = text('No se ha podido consultar la confirmación. Reintentando…', 'Could not check confirmation. Retrying…');
    } finally { checking = false; if (pending) timer = setTimeout(check,4000); }
  }
  button.addEventListener('click', async () => {
    const country = document.getElementById('sf-country');
    if (!country.reportValidity()) return;
    button.disabled = true;
    try {
      const result = await post('/api/telegram/challenge', {country:country.value,technology:document.getElementById('sf-technology').value});
      const url = new URL(result.url);
      if (url.origin !== 'https://t.me' || url.pathname.toLowerCase() !== '/cintiabot') throw new Error('invalid link');
      stop(); pending = result; link.href = result.url; link.hidden = false;
      state.textContent = text('Abre el bot con el botón de abajo y confirma el voto. Este enlace caduca en 15 minutos.', 'Open the bot below and confirm your vote. This link expires in 15 minutes.');
      link.focus(); timer = setTimeout(check,2000);
    } catch { state.textContent = text('No se ha podido iniciar la verificación. Inténtalo de nuevo.', 'Could not start verification. Please try again.'); }
    finally { button.disabled = !ready; }
  });
  new MutationObserver(render).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
  render();
  fetch(api + '/api/telegram/config',{signal:AbortSignal.timeout(10000)}).then(r => r.ok ? r.json() : {}).then(config => {
    ready = config.enabled === true && config.username.toLowerCase() === 'cintiabot'; button.disabled = !ready; render();
  }).catch(() => {});
})();
