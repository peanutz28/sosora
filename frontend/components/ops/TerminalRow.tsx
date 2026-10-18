"use client";

import { useEffect, useState } from "react";
import { traceSummary } from "@/lib/ops";
import type { OpsEvent } from "@/lib/types";

function Typewriter({ text, onProgress, onComplete }: { text: string; onProgress: () => void; onComplete?: (done: boolean) => void }) {
  const [length, setLength] = useState(0);
  useEffect(() => {
    setLength(0);
    onComplete?.(false);
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setLength(text.length); onComplete?.(true); onProgress(); return;
    }
    let count = 0;
    const timer = setInterval(() => {
      count = Math.min(text.length, count + Math.max(1, Math.ceil(text.length / 45)));
      setLength(count); onProgress();
      if (count === text.length) { clearInterval(timer); onComplete?.(true); }
    }, 18);
    return () => clearInterval(timer);
  }, [text, onProgress, onComplete]);
  return <span>{text.slice(0, length)}{length < text.length && <span className="terminal-cursor" aria-hidden>▍</span>}</span>;
}

export function TerminalRow({ call, result, index, newest, inputs, onProgress }: { call: OpsEvent; result?: OpsEvent; index: number; newest: boolean; inputs: boolean; onProgress: () => void }) {
  const [nameDone, setNameDone] = useState(false);
  const [bodyDone, setBodyDone] = useState(false);
  const failed = !!result?.result?.error;
  return <div className={`tool-row ${newest ? "tool-newest" : ""} ${failed ? "tool-error" : ""}`}>
    <span className="tool-step font-mono">{String(index + 1).padStart(2,"0")}</span>
    <div>
      <div className="tool-title"><code><Typewriter text={call.tool || "tool"} onProgress={onProgress} onComplete={setNameDone} /></code>
        <span className="tool-completion" aria-label={result && nameDone && bodyDone ? (failed ? "Failed" : "Complete") : "Running"}>{result && nameDone && bodyDone ? (failed ? "!" : "✓") : "···"}</span>
      </div>
      {inputs && <p className="tool-args">{traceSummary(call)}</p>}
      <p><Typewriter text={result ? traceSummary(result) : "Waiting for tool result…"} onProgress={onProgress} onComplete={setBodyDone} /></p>
    </div>
  </div>;
}
