const DECIMAL = /^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$/;
const COORDINATE_ERROR = 'Enter both X and Y as finite numbers in SVY21 metres.';
const LOAD_ERROR = 'The car park data could not load. Check your connection, then try the search again.';

export function coordinate(value) {
  const text = String(value).trim();
  const number = Number(text);
  if (text.length > 64 || !DECIMAL.test(text) || !Number.isFinite(number)) {
    throw new Error(COORDINATE_ERROR);
  }
  return number;
}

export function nearestCarpark(rows, x, y) {
  const inputX = coordinate(x);
  const inputY = coordinate(y);
  let nearest = null;
  let bestDistance = Infinity;
  for (const row of rows) {
    const distance = Math.hypot(inputX - row[2], inputY - row[3]);
    if (!Number.isFinite(distance)) {
      throw new Error('Coordinates are too large. Enter SVY21 coordinates in metres.');
    }
    if (distance < bestDistance) {
      nearest = row;
      bestDistance = distance;
    }
  }
  if (!nearest) throw new Error('The saved car park data is unavailable. Please try again later.');
  return { number: nearest[0], address: nearest[1], type: nearest[4], distance: bestDistance };
}

export function validateCatalog(data, sourceHash, expectedCount) {
  if (data?.schema !== 1 || data.source_sha256 !== sourceHash ||
      !Array.isArray(data.rows) || data.rows.length !== expectedCount ||
      expectedCount < 1 || expectedCount > 20000) throw new Error(LOAD_ERROR);
  const ids = new Set();
  for (const row of data.rows) {
    if (!Array.isArray(row) || row.length !== 5 ||
        ![row[0], row[1], row[4]].every(value => typeof value === 'string' && value.length > 0) ||
        !Number.isFinite(row[2]) || !Number.isFinite(row[3]) || ids.has(row[0])) {
      throw new Error(LOAD_ERROR);
    }
    ids.add(row[0]);
  }
  return data.rows;
}

export function createCatalogLoader(url, sourceHash, expectedCount, {
  fetchImpl = globalThis.fetch, timeoutMs = 10000, maxBytes = 1024 * 1024,
} = {}) {
  let pending;
  return function load() {
    if (pending) return pending;
    pending = (async () => {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), timeoutMs);
      try {
        const response = await fetchImpl(url, { signal: controller.signal, credentials: 'omit', referrerPolicy: 'no-referrer' });
        if (!response.ok || Number(response.headers.get('content-length')) > maxBytes || !response.body) {
          controller.abort();
          throw new Error(LOAD_ERROR);
        }
        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8', { fatal: true });
        let bytes = 0;
        let text = '';
        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            bytes += value.byteLength;
            if (bytes > maxBytes) {
              controller.abort();
              throw new Error(LOAD_ERROR);
            }
            text += decoder.decode(value, { stream: true });
          }
          text += decoder.decode();
        } finally {
          reader.releaseLock();
        }
        return validateCatalog(JSON.parse(text), sourceHash, expectedCount);
      } catch {
        throw new Error(LOAD_ERROR);
      } finally {
        clearTimeout(timer);
      }
    })().catch(error => {
      pending = undefined;
      throw error;
    });
    return pending;
  };
}

function start() {
  const form = document.querySelector('#search-form[data-catalog-url]');
  if (!form) return;
  const x = form.elements.xcoords;
  const y = form.elements.ycoords;
  const button = form.querySelector('button');
  const status = document.querySelector('#search-status');
  const errorBox = document.querySelector('#search-error');
  const result = document.querySelector('#search-result');
  const empty = document.querySelector('#empty-result');
  const load = createCatalogLoader(form.dataset.catalogUrl, form.dataset.sourceHash, Number(form.dataset.catalogCount));
  let sequence = 0;

  function clear() {
    sequence += 1;
    errorBox.hidden = true;
    result.hidden = true;
    empty.hidden = false;
    status.textContent = '';
    button.disabled = false;
    form.removeAttribute('aria-busy');
    x.removeAttribute('aria-invalid');
    y.removeAttribute('aria-invalid');
  }

  async function search(updateUrl = true) {
    clear();
    const current = sequence;
    let inputX, inputY;
    try {
      inputX = coordinate(x.value);
      inputY = coordinate(y.value);
    } catch (error) {
      x.setAttribute('aria-invalid', 'true');
      y.setAttribute('aria-invalid', 'true');
      errorBox.textContent = error.message;
      errorBox.hidden = false;
      errorBox.focus();
      return;
    }
    button.disabled = true;
    form.setAttribute('aria-busy', 'true');
    status.textContent = 'Finding your nearest car park…';
    try {
      const rows = await load();
      if (current !== sequence) return;
      const nearest = nearestCarpark(rows, inputX, inputY);
      document.querySelector('#carpark-number').textContent = nearest.number;
      document.querySelector('#carpark-address').textContent = nearest.address;
      document.querySelector('#carpark-type').textContent = nearest.type;
      document.querySelector('#carpark-distance').textContent = `${Math.round(nearest.distance)} m`;
      result.hidden = false;
      empty.hidden = true;
      status.textContent = 'Nearest car park found.';
      if (updateUrl) {
        const url = new URL(location.href);
        url.search = new URLSearchParams({ xcoords: String(inputX), ycoords: String(inputY) }).toString();
        history.pushState(null, '', url);
      }
      result.focus();
    } catch (error) {
      if (current !== sequence) return;
      status.textContent = '';
      errorBox.textContent = error.message;
      errorBox.hidden = false;
      errorBox.focus();
    } finally {
      if (current === sequence) {
        button.disabled = false;
        form.removeAttribute('aria-busy');
      }
    }
  }

  function restoreUrl() {
    clear();
    const params = new URLSearchParams(location.search);
    x.value = params.get('xcoords') || '';
    y.value = params.get('ycoords') || '';
    if (!params.has('xcoords') && !params.has('ycoords')) return;
    if (params.getAll('xcoords').length !== 1 || params.getAll('ycoords').length !== 1) {
      errorBox.textContent = COORDINATE_ERROR;
      errorBox.hidden = false;
      return;
    }
    void search(false);
  }

  form.addEventListener('submit', event => { event.preventDefault(); void search(); });
  form.addEventListener('input', clear);
  document.querySelector('#example-link').addEventListener('click', event => {
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    x.value = '28000';
    y.value = '38000';
    void search();
  });
  window.addEventListener('popstate', restoreUrl);
  restoreUrl();
}

if (typeof document !== 'undefined') start();
