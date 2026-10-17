export const STAGE_TARGETS = [1, 5, 6, 9] as const;

export const STAGES = [
  {
    id: "normal",
    label: "Normal conditions",
    summary: "Rescue unit, fictional destination, and a candidate access route.",
  },
  {
    id: "failure",
    label: "Road failure",
    summary: "A simulated closure withdraws any candidate that uses that segment.",
  },
  {
    id: "reroute",
    label: "Rerouting",
    summary: "The graph is searched again. A missing path means potentially isolated.",
  },
  {
    id: "response",
    label: "Emergency response",
    summary: "A fictional SOS is stored and held for a person to review.",
  },
] as const;

export function stageIndex(step: number): number {
  if (step >= 9) return 3;
  if (step >= 6) return 2;
  if (step >= 2) return 1;
  if (step >= 1) return 0;
  return -1;
}

export function nextTarget(step: number): number | null {
  if (step < 1) return 1;
  if (step < 5) return 5;
  if (step < 6) return 6;
  if (step < 9) return 9;
  return null;
}

export function prevTarget(step: number): number | null {
  if (step > 6 && step >= 9) return 6;
  if (step >= 6) return 5;
  if (step >= 2) return 1;
  if (step >= 1) return 0;
  return null;
}

export function stageLabel(step: number): string {
  const index = stageIndex(step);
  if (index < 0) return "Standby";
  return STAGES[index].label;
}
