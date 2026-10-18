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
