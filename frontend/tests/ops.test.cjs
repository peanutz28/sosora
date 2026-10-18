const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ts = require("typescript");
const modulePromise = import(
  "data:text/javascript;base64," +
    Buffer.from(
      ts.transpileModule(
        fs.readFileSync(path.join(__dirname, "../lib/ops.ts"), "utf8"),
        {
          compilerOptions: {
            module: ts.ModuleKind.ESNext,
            target: ts.ScriptTarget.ES2020,
          },
        },
      ).outputText,
    ).toString("base64")
);
const event = (id, kind, fields = {}) => ({
  id,
  kind,
  at: `2026-10-18T04:00:${String(id).padStart(2, "0")}Z`,
  message: "",
  step: 0,
  ...fields,
});

test("socket and persisted events merge without duplicate tool rows", async () => {
  const { mergeEvents } = await modulePromise;
  const call = event(1, "agent_tool_call", { tool: "find_segments" });
  const result = event(2, "agent_tool_result", { tool: "find_segments" });
  assert.deepEqual(mergeEvents([result, call], [call, result]), [call, result]);
  assert.equal(mergeEvents([], []).length, 0);
});
test("ambiguous bridges are deduped across directions and retain real centroids", async () => {
  const { reviewCandidates } = await modulePromise;
  const stream = [
    event(1, "agent_tool_result", {
      tool: "find_segments",
      result: {
        distinct_locations: 2,
        candidates: [
          {
            id: "bridge-east:f",
            name: "Warren Wilson Road",
            centroid: [-82.42702, 35.61258],
            match_score: 1,
          },
          {
            id: "bridge-east:b",
            name: "Warren Wilson Road",
            centroid: [-82.42702, 35.61258],
            match_score: 1,
          },
          {
            id: "bridge-west:f",
            name: "Warren Wilson Road",
            centroid: [-82.45, 35.61],
            match_score: 1,
          },
          { id: "bad", centroid: ["invented", 0], match_score: 1 },
          { id: "unrelated:f", centroid: [-82.6, 35.6], match_score: 0.2 },
        ],
      },
    }),
  ];
  const candidates = reviewCandidates(stream, { needs_human_review: true });
  assert.deepEqual(
    candidates.map((c) => [c.id, c.label]),
    [
      ["bridge-east", "A"],
      ["bridge-west", "B"],
    ],
  );
  assert.deepEqual(candidates[0].centroid, [-82.42702, 35.61258]);
  assert.deepEqual(reviewCandidates(stream, null), []);
  assert.deepEqual(
    reviewCandidates(
      [
        ...stream,
        event(2, "agent_tool_result", {
          tool: "find_segments",
          result: { distinct_locations: 1, candidates: [] },
        }),
      ],
      { needs_human_review: true },
    ),
    [],
  );
});
test("latest assessment and trace summaries use structured fields, not guessed prose", async () => {
  const { latestAssessment, traceSummary } = await modulePromise;
  const stream = [
    event(1, "agent_tool_result", {
      tool: "submit_assessment",
      result: {
        summary: "Needs review",
        affected_incident_ids: ["SOS-001", 42],
        needs_human_review: true,
      },
    }),
  ];
  assert.deepEqual(latestAssessment(stream), {
    summary: "Needs review",
    affected_incident_ids: ["SOS-001"],
    needs_human_review: true,
  });
  assert.equal(
    traceSummary(
      event(2, "agent_tool_result", {
        tool: "recompute_reachability",
        result: { newly_unreachable_incident_ids: ["SOS-001", "SOS-002"] },
      }),
    ),
    "2 incidents lost access",
  );
  assert.equal(
    traceSummary(
      event(3, "agent_tool_result", {
        tool: "find_segments",
        result: { distinct_locations: 2 },
      }),
    ),
    "2 locations match → needs review",
  );
  assert.equal(
    traceSummary(
      event(4, "agent_tool_result", {
        tool: "report_segment",
        result: { a: { status: "contested" } },
      }),
    ),
    "contested",
  );
  assert.equal(
    traceSummary(
      event(5, "agent_tool_result", {
        tool: "get_imagery_evidence",
        result: [],
      }),
    ),
    "No associated imagery; uncertainty retained",
  );
});

test("blocked roads count physical segments, not their forward/backward directions", async () => {
  const { physicalClosureCount } = await modulePromise;
  assert.equal(physicalClosureCount([]), 0);
  assert.equal(
    physicalClosureCount([{ id: "549633356:0:f" }, { id: "549633356:0:b" }]),
    1,
  );
  assert.equal(
    physicalClosureCount([
      { id: "549633356:0:f" },
      { id: "549633356:0:b" },
      { id: "549633356:1:f" },
      { id: "other" },
    ]),
    3,
  );
});

test("successful sign-off is teal; only ambiguity and contested roads are yellow", async () => {
  const { agentStatus } = await modulePromise;
  const assessment = { needs_human_review: true };
  const resolved = event(1, "agent_tool_result", { tool: "find_segments", result: { distinct_locations: 1, needs_human_review: false } });
  const ambiguous = event(1, "agent_tool_result", { tool: "find_segments", result: { distinct_locations: 2, needs_human_review: true } });
  assert.equal(agentStatus(false, null), "idle");
  assert.equal(agentStatus(false, assessment, [resolved]), "ready for operator");
  assert.equal(agentStatus(false, assessment, [ambiguous]), "needs review");
  assert.equal(agentStatus(false, assessment, [ambiguous, event(2, "radio_location_confirmed"), { ...resolved, id: 3 }]), "ready for operator");
  assert.equal(agentStatus(false, assessment, [resolved, event(2, "agent_tool_result", { tool: "report_segment", result: { bridge: { status: "contested" } } })]), "needs review");
  assert.equal(agentStatus(true, assessment, [ambiguous]), "working");
  assert.equal(agentStatus(false, assessment, [event(2, "agent_tool_result", { tool: "submit_assessment", call_id: "fallback" })]), "action required");
});

test("all three counters advance on reachability result before the final state arrives", async () => {
  const { accessCounters } = await modulePromise;
  const state = { closures: [], incidents: Array.from({ length: 9 }, (_, i) => ({ id: `SOS-${i}`, reachable: true })) };
  const blocked = event(1, "agent_tool_result", { tool: "report_segment", result: { "bridge:f": { status: "blocked" }, "bridge:b": { status: "blocked" } } });
  assert.deepEqual(accessCounters(state, [blocked]), { cutOff: 0, reachable: 9, blocked: 0 });
  const routes = Object.fromEntries(state.incidents.map((i, n) => [i.id, { status: n < 5 ? "unreachable" : "ok" }]));
  assert.deepEqual(accessCounters(state, [blocked, event(2, "agent_tool_result", { tool: "recompute_reachability", result: { routes } })]), { cutOff: 5, reachable: 4, blocked: 1 });
});

test("trace badge uses only backend provenance and never invents latency", async () => {
  const { agentTraceBadge } = await modulePromise;
  const runtime = { cached: false, model_id: "nvidia/nemotron-3.5-lightning-30b-a3b", serving_backend: "vLLM", last_call_latency_ms: 854 };
  const item = event(1, "agent_tool_call", { agent_runtime: runtime });
  assert.equal(agentTraceBadge([item], false).label, "Nemotron 3.5 Lightning · vLLM · 0.85s");
  assert.equal(agentTraceBadge([item], true).label, "cached replay");
  for (const latency of [null, -1, Infinity]) {
    assert.match(agentTraceBadge([{ ...item, agent_runtime: { ...runtime, last_call_latency_ms: latency } }], false).label, /latency unavailable/);
  }
  assert.equal(agentTraceBadge([], false).label, "Model metadata unavailable");
  assert.equal(agentTraceBadge([{ ...item, agent_runtime: { ...runtime, cached: true } }], false).label, "cached replay");
  assert.match(agentTraceBadge([{ ...item, agent_runtime: { ...runtime, model_id: "actual/other-id" } }], false).label, /^actual\/other-id/);
});

test('external seed drops prior take counts and tool history while normal snapshots retain streamed events', async () => {
  const {reconcileEvents,accessCounters}=await modulePromise;
  const old=[event(12,'agent_tool_result',{tool:'report_segment',result:{'bridge:f':{status:'blocked'}}}),event(13,'agent_tool_result',{tool:'recompute_reachability',result:{routes:{'SOS-001':{status:'unreachable'}}}})];
  const seed=[event(1,'situation')];
  const fresh=reconcileEvents(old,seed,true);
  assert.deepEqual(fresh,seed);
  assert.deepEqual(accessCounters({incidents:[{id:'SOS-001',reachable:true}],closures:[]},fresh),{cutOff:0,reachable:1,blocked:0});
  assert.equal(reconcileEvents(old,seed,false).length,3);
});
