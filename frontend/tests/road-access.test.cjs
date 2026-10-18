const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');

// Execute the actual pure TypeScript modules without introducing a test runtime.
async function load(relative) {
  const filename = path.join(__dirname, '..', relative);
  const result = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 },
  });
  return import('data:text/javascript;base64,' + Buffer.from(result.outputText).toString('base64'));
}

const incident = (id, reachable, status) => ({
  id, client_id: 'demo-' + id, source_id: 'simulated_seed', lon: -82.42, lat: 35.62,
  message: '[SIMULATED] Help needed.', people_affected: 2, medical: null, mobility: null,
  urgency: 'critical', delivery_status: 'received', verification: 'unverified',
  created_at: '2026-10-18T00:00:00Z', reachable,
  route: status ? { status } : undefined,
});
const state = (incidents) => ({ incidents, objective: { label: 'Swannanoa' } });

test('bridge closure changes only the five disconnected incidents; reset clears it', async () => {
  const { buildQueue } = await load('lib/queue.ts');
  const { roadAccess } = await load('lib/access.ts');
  const seeds = Array.from({ length: 9 }, (_, index) => incident(`SOS-${index + 1}`, true, 'ok'));
  const before = buildQueue(state(seeds)).filter(item => item.source === 'backend');
  assert.equal(before.filter(item => roadAccess(item).status === 'available').length, 9);
  const after = buildQueue(state(seeds.map((item, index) => index < 5
    ? { ...item, reachable: false, route: { status: 'unreachable' } } : item)));
  assert.deepEqual(after.filter(item => roadAccess(item).status === 'lost').map(item => item.id),
    ['SOS-1', 'SOS-2', 'SOS-3', 'SOS-4', 'SOS-5']);
  assert.equal(after.filter(item => roadAccess(item).status === 'available').length, 4);
  assert.equal(buildQueue(state(seeds)).filter(item => roadAccess(item).status === 'lost').length, 0);
});

test('missing access and map snap failures are unknown, including synthetic queue items', async () => {
  const { roadAccess } = await load('lib/access.ts');
  const { buildQueue } = await load('lib/queue.ts');
  for (const item of [{}, { reachable: null }, { reachable: false, route: { status: 'snap_failed' } }]) {
    assert.equal(roadAccess(item).status, 'unknown');
  }
  assert.ok(buildQueue(state([])).every(item => roadAccess(item).status === 'unknown'));
});

test('route status is a fallback only when the backend boolean is absent', async () => {
  const { roadAccess } = await load('lib/access.ts');
  assert.equal(roadAccess({ route: { status: 'unreachable' } }).status, 'lost');
  assert.equal(roadAccess({ route: { status: 'ok' } }).status, 'available');
  assert.equal(roadAccess({ reachable: false, route: { status: 'ok' } }).status, 'lost');
  assert.match(roadAccess({ reachable: true }).detail, /passability remains unverified/);
});
