(() => {
  'use strict';
  const EU = 'AT BE BG HR CY CZ DK EE FI FR DE GR HU IE IT LV LT LU MT NL PL PT RO SK SI ES SE'.split(' ');
  const local = ['127.0.0.1', 'localhost', '[::1]'].includes(location.hostname);
  const api = new URLSearchParams(location.search).get('api')?.replace(/\/$/, '') || (local ? '' : 'https://data.righttoupdates.eu');
  const copy = {
    es: {
      eyebrow: '// La comunidad, país a país', title: 'Europa pide más vida para su tecnología.',
      intro: 'Cada apoyo cuenta. Descubre cuántas personas se han sumado y elige la tecnología para la que pides más soporte.',
      total: 'Apoyos registrados en la UE', countries: 'Países con apoyos', votes: 'Apoyos a tecnologías',
      note: 'Apoyos a esta campaña; no son firmas oficiales de una ICE ni correos verificados.',
      mode: 'Entorno local · datos independientes', country: 'Explora un país', countryCount: 'apoyos registrados en este país',
      join: 'Apoyar desde este país →', caption: 'Un tono más intenso indica más apoyos. Selecciona un país en el mapa o en la lista.',
      loading: 'Consultando los apoyos…', error: 'Los recuentos no están disponibles. No se muestran cifras estimadas.', retry: 'Volver a intentar',
      fresh: 'Recuentos actualizados', choose: 'Pedir más soporte', count: 'apoyos', selected: 'Tecnología elegida',
      label: '¿Qué tecnología necesita más soporte?', optional: 'Solo apoyar la iniciativa',
      help: 'Opcional. Elige una tecnología de la lista: tu apoyo contará para ella y una sola vez en el total europeo.',
      ranking: 'Tecnologías con más apoyos', empty: 'Todavía no hay votos a tecnologías. Elige la tuya en la lista.',
      localOk: '¡Gracias! Tu apoyo se ha guardado en este entorno local. No se ha enviado ningún correo.',
      unavailable: 'El servicio de votos a tecnologías no está disponible. Inténtalo más tarde.',
      localConsent: 'Prueba local: el apoyo se guarda solo en este equipo. No se envían correos ni datos al servicio de producción.',
      saved: 'Tu apoyo se ha registrado.', mapError: 'No se ha podido cargar el mapa. Puedes consultar todos los países en la lista.',
    },
    en: {
      eyebrow: '// The community, country by country', title: 'Europe wants more life for its technology.',
      intro: 'Every supporter counts. See how many people have joined and choose the technology you want supported for longer.',
      total: 'Registered supporters in the EU', countries: 'Countries with supporters', votes: 'Technology votes',
      note: 'Campaign supports; these are not official ECI signatures or verified emails.',
      mode: 'Local environment · separate data', country: 'Explore a country', countryCount: 'registered supporters in this country',
      join: 'Support from this country →', caption: 'A brighter shade means more supporters. Select a country on the map or in the list.',
      loading: 'Loading support counts…', error: 'Support counts are unavailable. No estimated figures are shown.', retry: 'Try again',
      fresh: 'Counts updated', choose: 'Request more support', count: 'supporters', selected: 'Selected technology',
      label: 'Which technology needs more support?', optional: 'Support the initiative only',
      help: 'Optional. Choose a technology from the list: your support counts towards it and only once in the European total.',
      ranking: 'Technologies with the most support', empty: 'No technology votes yet. Choose yours from the list.',
      localOk: 'Thank you! Your support was saved in this local environment. No email was sent.',
      unavailable: 'Technology voting is currently unavailable. Please try again later.',
      localConsent: 'Local preview: support is stored only on this computer. No emails or data are sent to the production service.',
      saved: 'Your support has been registered.', mapError: 'The map could not load. All countries are available in the list.',
    },
  };
  const $ = id => document.getElementById(id);
  const t = key => (copy[document.documentElement.lang] || copy.en)[key];
  const number = n => n == null ? '—' : new Intl.NumberFormat(document.documentElement.lang).format(n);
  const countryName = code => new Intl.DisplayNames([document.documentElement.lang], {type: 'region'}).of(code);
  let stats = null, technologies = [], selectedCountry = 'ES', geometry = null, busy = false;
  let loading = true, lastUpdate = null;

  const section = document.createElement('section');
  section.id = 'community';
  section.innerHTML = `<div class="wrap">
    <div class="community-heading"><div><div class="eyebrow" data-community="eyebrow"></div><h2 data-community="title"></h2></div><span class="community-mode" hidden data-community="mode"></span></div>
    <p class="section-lede" data-community="intro"></p>
    <div class="community-summary">
      <div class="community-stat"><strong id="eu-total">—</strong><span data-community="total"></span><small>27 / EU</small></div>
      <div class="community-stat"><strong id="eu-countries">—</strong><span data-community="countries"></span></div>
      <div class="community-stat"><strong id="eu-votes">—</strong><span data-community="votes"></span></div>
    </div>
    <div class="community-panel"><div class="community-map"><svg id="europe-map" viewBox="0 0 650 560" role="group"></svg><p id="map-error" hidden></p><p class="map-caption" data-community="caption"></p></div>
      <div class="country-panel"><label for="map-country" data-community="country"></label><select id="map-country"></select><div class="country-total" id="country-total">—</div><p data-community="countryCount"></p><a class="btn btn-primary" id="country-join" href="#support" data-community="join"></a><div class="country-list" id="country-list"></div></div>
    </div>
    <p class="community-status" id="community-status" role="status"></p><button class="community-retry" id="community-retry" type="button" data-community="retry" hidden></button>
    <p class="community-status" data-community="note"></p>
    <h3 style="margin-top:32px" data-community="ranking"></h3><div class="technology-ranking" id="technology-ranking"></div>
  </div>`;
  $('rescue').before(section);
  const field = document.createElement('div');
  field.className = 'fld';
  field.innerHTML = '<label for="sf-technology" data-community="label"></label><select id="sf-technology" name="technology" aria-describedby="technology-help"></select><p id="technology-help" class="support-selection-note" data-community="help"></p>';
  $('sf-submit').before(field);

  function chooseTechnology(id) {
    $('sf-technology').value = id;
    $('support-form').scrollIntoView({behavior: 'smooth', block: 'center'});
    $('sf-technology').focus({preventScroll: true});
  }
  function selectCountry(code) {
    selectedCountry = code;
    $('map-country').value = code;
    $('country-total').textContent = number(stats?.countries[code]);
    document.querySelectorAll('[data-country]').forEach(el => {
      const active = el.dataset.country === code;
      el.classList.toggle('selected', active);
      el.setAttribute('aria-pressed', String(active));
    });
  }
  // Equirectangular projection, longitude scaled at 54° N; overseas polygons excluded.
  const project = ([lon, lat]) => [32 + (lon + 12) * 12.7, 24 + (72 - lat) * 14];
  function drawMap() {
    const svg = $('europe-map');
    svg.replaceChildren();
    svg.setAttribute('aria-label', t('country'));
    if (!geometry) return;
    const ns = 'http://www.w3.org/2000/svg';
    const maximum = Math.max(1, ...Object.values(stats?.countries || {}));
    geometry.features.forEach(feature => {
      const code = feature.properties.code;
      const group = document.createElementNS(ns, 'g');
      group.dataset.country = code;
      group.setAttribute('role', 'button'); group.setAttribute('tabindex', '0');
      group.setAttribute('aria-label', `${countryName(code)}: ${number(stats?.countries[code])} ${t('count')}`);
      const title = document.createElementNS(ns, 'title');
      title.textContent = group.getAttribute('aria-label'); group.append(title);
      const polygons = feature.geometry.type === 'Polygon' ? [feature.geometry.coordinates] : feature.geometry.coordinates;
      const path = document.createElementNS(ns, 'path');
      const rings = polygons.flat().filter(ring => ring.every(([lon, lat]) => lon >= -15 && lon <= 36 && lat >= 33 && lat <= 73));
      path.setAttribute('d', rings.map(ring => ring.map((p, i) => `${i ? 'L' : 'M'}${project(p).map(v => v.toFixed(1)).join(',')}`).join(' ') + 'Z').join(' '));
      const count = stats?.countries[code] || 0;
      path.setAttribute('fill', count ? `hsl(78 65% ${24 + 40 * Math.sqrt(count / maximum)}%)` : '#293b3a');
      path.setAttribute('fill-rule', 'evenodd'); group.append(path);
      if (['MT', 'LU', 'CY'].includes(code)) {
        const location = {MT: [14.4,35.95], LU: [6.1,49.8], CY: [33.1,35.1]}[code];
        const [x,y] = project(location);
        const dot = document.createElementNS(ns, 'circle'); dot.setAttribute('cx',x); dot.setAttribute('cy',y); dot.setAttribute('r',6); dot.classList.add('locator'); group.append(dot);
        const label = document.createElementNS(ns, 'text'); label.setAttribute('x',x+10); label.setAttribute('y',y+4); label.textContent = code; group.append(label);
      }
      group.addEventListener('click', () => selectCountry(code));
      group.addEventListener('keydown', e => { if (['Enter',' '].includes(e.key)) { e.preventDefault(); selectCountry(code); } });
      svg.append(group);
    });
  }
  function render() {
    document.querySelectorAll('[data-community]').forEach(el => el.textContent = t(el.dataset.community));
    section.querySelector('.community-mode').hidden = stats ? stats.mode !== 'local' : !(local && !api);
    $('eu-total').textContent = number(stats?.total);
    $('eu-countries').textContent = stats ? `${number(Object.values(stats.countries).filter(n => n > 0).length)} / 27` : '—';
    $('eu-votes').textContent = stats ? number(Object.values(stats.technologies).reduce((a,b) => a+b,0)) : '—';
    const sorted = [...EU].sort((a,b) => countryName(a).localeCompare(countryName(b), document.documentElement.lang));
    const formCountry = $('sf-country').value;
    $('map-country').replaceChildren(); $('country-list').replaceChildren();
    $('sf-country').querySelectorAll('option[value]:not([value=""])').forEach(el => el.remove());
    sorted.forEach(code => {
      const option = new Option(countryName(code), code);
      $('map-country').append(option); $('sf-country').append(option.cloneNode(true));
      const row = document.createElement('button'); row.type = 'button'; row.className = 'country-row'; row.dataset.country = code;
      const name = document.createElement('span'); name.textContent = countryName(code);
      const total = document.createElement('strong'); total.textContent = number(stats?.countries[code]);
      row.append(name,total); row.addEventListener('click', () => selectCountry(code)); $('country-list').append(row);
    });
    $('sf-country').value = formCountry;
    const choice = $('sf-technology').value;
    $('sf-technology').replaceChildren(new Option(t('optional'), ''));
    technologies.forEach(tech => $('sf-technology').append(new Option(tech.name, tech.id)));
    $('sf-technology').value = choice;
    document.querySelectorAll('.technology-action').forEach(el => {
      el.querySelector('button').textContent = t('choose');
      el.querySelector('span').textContent = `${number(stats?.technologies[el.dataset.technology])} ${t('count')}`;
    });
    $('technology-ranking').replaceChildren();
    const ranked = technologies.filter(tech => stats?.technologies[tech.id] > 0).sort((a,b) => stats.technologies[b.id]-stats.technologies[a.id] || a.name.localeCompare(b.name)).slice(0,5);
    ranked.forEach((tech,index) => {
      const button = document.createElement('button'); button.type = 'button';
      button.textContent = `${index+1}. ${tech.name}`;
      const total = document.createElement('strong'); total.textContent = number(stats.technologies[tech.id]); button.append(total);
      button.addEventListener('click', () => chooseTechnology(tech.id)); $('technology-ranking').append(button);
    });
    if (!ranked.length) $('technology-ranking').textContent = stats ? t('empty') : t('error');
    $('community-status').textContent = loading ? t('loading') : stats ? `${t('fresh')} · ${lastUpdate.toLocaleTimeString(document.documentElement.lang, {hour:'2-digit',minute:'2-digit'})}` : t('error');
    $('community-retry').hidden = loading || !!stats;
    $('map-error').textContent = t('mapError');
    if (stats?.mode === 'local' || (local && !api)) document.querySelector('.support-form .consent').textContent = t('localConsent');
    drawMap(); selectCountry(selectedCountry);
  }
  async function loadStats() {
    if (busy) return;
    busy = true; loading = true; render();
    try {
      const response = await fetch(`${api}/api/community/stats`, {cache:'no-store', signal:AbortSignal.timeout(10000)});
      if (!response.ok) throw new Error('stats');
      const data = await response.json();
      const count = n => Number.isSafeInteger(n) && n >= 0;
      if (!count(data.total) || !data.countries || !data.technologies || !EU.every(code => count(data.countries[code])) || !technologies.every(tech => count(data.technologies[tech.id])) || EU.reduce((sum,code) => sum+data.countries[code],0) !== data.total) throw new Error('invalid stats');
      stats = data; lastUpdate = new Date();
    } catch { stats = null; }
    finally { loading = false; busy = false; render(); }
  }
  window.community = {
    api, refresh: loadStats,
    canVote: () => stats?.technologyVoting === true,
    text: t,
    isLocal: () => stats?.mode === 'local',
  };
  $('map-country').addEventListener('change', e => selectCountry(e.target.value));
  $('country-join').addEventListener('click', () => { $('sf-country').value = selectedCountry; $('sf-email').focus({preventScroll:true}); });
  $('community-retry').addEventListener('click', loadStats);
  new MutationObserver(render).observe(document.documentElement, {attributes:true, attributeFilter:['lang']});
  render();
  Promise.all([
    fetch('technologies.json').then(r => { if (!r.ok) throw new Error('catalog'); return r.json(); }),
    fetch('europe.geojson').then(r => { if (!r.ok) throw new Error('map'); return r.json(); }).catch(() => { $('map-error').hidden = false; return null; }),
  ]).then(([catalog, geo]) => {
    technologies = catalog; geometry = geo;
    document.querySelectorAll('.rescue-card').forEach(card => {
      const tech = technologies.find(item => item.name === card.querySelector('.rescue-card-name').textContent);
      if (!tech) return;
      const actions = document.createElement('div'); actions.className = 'technology-action'; actions.dataset.technology = tech.id;
      const button = document.createElement('button'); button.type = 'button'; button.addEventListener('click', () => chooseTechnology(tech.id));
      actions.append(button,document.createElement('span')); card.append(actions);
    });
    loadStats();
    setInterval(() => { if (!document.hidden) loadStats(); },60000);
  }).catch(() => { loading = false; render(); });
})();
