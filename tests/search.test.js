import assert from 'node:assert/strict';
import test from 'node:test';
import { coordinate, nearestCarpark, validateCatalog, createCatalogLoader } from '../static/app.js';

const rows = [['A', 'First, Road', 0, 0, 'SURFACE'], ['B', 'Second Road', 10, 0, 'SURFACE'], ['C', 'Third Road', 0, 10, 'SURFACE']];
const payload = { schema: 1, source_sha256: 'fixture', rows };
const response = () => new Response(JSON.stringify(payload));

test('nearest, distance and stable ties match known geometry', () => {
  assert.equal(nearestCarpark(rows, 9, 0).number, 'B');
  assert.equal(nearestCarpark(rows, 5, 0).number, 'A');
  assert.equal(nearestCarpark(rows, 3, 4).distance, 5);
});

test('queries and result edits leave source rows unchanged', () => {
  const before = structuredClone(rows);
  nearestCarpark(rows, 0, 9).address = 'Changed';
  assert.deepEqual(rows, before);
});

test('invalid and nonfinite coordinates are rejected', () => {
  for (const value of ['', ' ', null, true, 'NaN', 'Infinity', '-inf', '1e999', '0x10', '1_000', '1,000', '1x', '9'.repeat(65), '１２']) {
    assert.throws(() => coordinate(value), /finite numbers/);
  }
});

test('decimal forms accepted consistently with Python', () => {
  for (const [value, expected] of [[' 2.5 ', 2.5], ['.5', .5], ['1.', 1], ['+2e3', 2000], ['-1', -1], [0, 0]]) assert.equal(coordinate(value), expected);
});

test('empty catalogs and overflowing distances fail clearly', () => {
  assert.throws(() => nearestCarpark([], 0, 0), /unavailable/);
  assert.throws(() => nearestCarpark(rows, '1.79e308', '1.79e308'), /too large/);
});

test('catalog rejects malformed, stale, duplicate and missing rows', () => {
  assert.deepEqual(validateCatalog(payload, 'fixture', 3), rows);
  for (const data of [null, { ...payload, schema: 2 }, { ...payload, source_sha256: 'old' }, { ...payload, rows: [] }, { ...payload, rows: [rows[0], rows[0], rows[1]] }, { ...payload, rows: [['A', 'A', null, 0, 'A'], rows[1], rows[2]] }]) {
    assert.throws(() => validateCatalog(data, 'fixture', 3), /could not load/);
  }
});

test('concurrent and repeated searches share one download', async () => {
  let calls = 0;
  const load = createCatalogLoader('fixture.json', 'fixture', 3, { fetchImpl: async () => { calls++; return response(); } });
  const [first, second] = await Promise.all([load(), load()]);
  assert.equal(first, second);
  assert.equal(await load(), first);
  assert.equal(calls, 1);
});

test('failed downloads can be retried and then cached', async () => {
  let calls = 0;
  const load = createCatalogLoader('fixture.json', 'fixture', 3, { fetchImpl: async () => ++calls === 1 ? new Response('unavailable', { status: 503 }) : response() });
  await assert.rejects(load(), /could not load/);
  assert.equal((await load()).length, 3);
  await load();
  assert.equal(calls, 2);
});

test('malformed JSON is a recoverable load error', async () => {
  const load = createCatalogLoader('fixture.json', 'fixture', 3, { fetchImpl: async () => new Response('{') });
  await assert.rejects(load(), /could not load/);
});

test('both advertised and streamed oversized responses are bounded', async () => {
  for (const headers of [{ 'content-length': '100' }, {}]) {
    const load = createCatalogLoader('fixture.json', 'fixture', 3, { maxBytes: 10, fetchImpl: async () => new Response('x'.repeat(100), { headers }) });
    await assert.rejects(load(), /could not load/);
  }
});

test('deadline cancels a stalled connection', async () => {
  let aborted = false;
  const load = createCatalogLoader('fixture.json', 'fixture', 3, {
    timeoutMs: 20,
    fetchImpl: (_url, { signal }) => new Promise((_resolve, reject) => signal.addEventListener('abort', () => { aborted = true; reject(new Error('aborted')); })),
  });
  await assert.rejects(load(), /could not load/);
  assert.equal(aborted, true);
});

test('deadline also covers a stalled response body', async () => {
  let aborted = false;
  const load = createCatalogLoader('fixture.json', 'fixture', 3, {
    timeoutMs: 20,
    fetchImpl: async (_url, { signal }) => new Response(new ReadableStream({ start(controller) {
      controller.enqueue(new TextEncoder().encode('{'));
      signal.addEventListener('abort', () => { aborted = true; controller.error(new Error('aborted')); });
    } })),
  });
  await assert.rejects(load(), /could not load/);
  assert.equal(aborted, true);
});
