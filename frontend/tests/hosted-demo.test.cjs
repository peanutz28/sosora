const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');

function load(relative) {
  const filename = path.resolve(__dirname, relative);
  const source = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
  }).outputText;
  const loaded = new Module(filename, module);
  loaded.paths = Module._nodeModulePaths(path.dirname(filename));
  loaded._compile(source, filename);
  return loaded.exports;
}
const { HostedDemoBanner } = load('../components/shell/HostedDemoBanner.tsx');
const { agentTraceBadge } = load('../lib/ops.ts');
function flag(value, run) {
  const before = process.env.NEXT_PUBLIC_HOSTED_DEMO;
  try {
    if (value === undefined) delete process.env.NEXT_PUBLIC_HOSTED_DEMO;
    else process.env.NEXT_PUBLIC_HOSTED_DEMO = value;
    run();
  } finally {
    if (before === undefined) delete process.env.NEXT_PUBLIC_HOSTED_DEMO;
    else process.env.NEXT_PUBLIC_HOSTED_DEMO = before;
  }
}

test('hosted banner is absent for local defaults and an explicit false flag', () => {
  for (const value of [undefined, 'false']) flag(value, () => {
    assert.equal(renderToStaticMarkup(React.createElement(HostedDemoBanner)), '');
  });
});
test('hosted flag shows the exact disclosure', () => flag('true', () => {
  assert.match(renderToStaticMarkup(React.createElement(HostedDemoBanner)),
    /Hosted demo · cached replay · the real system runs offline on one GPU box/);
}));
test('hosted trace cannot display a model identity or latency', () => flag('true', () => {
  const result = agentTraceBadge([{ agent_runtime: {
    model_id: 'live-model', serving_backend: 'vllm', cached: false, last_call_latency_ms: 1234,
  }}], false);
  assert.equal(result.label, 'cached replay');
  assert.doesNotMatch(result.label, /live-model|1\.23|vllm/);
}));
