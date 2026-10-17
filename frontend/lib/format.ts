export function km(meters: number | null | undefined): string {
  if (meters == null) return "—";
  return `${(meters / 1000).toFixed(2)} km`;
}

export function scenarioTime(iso: string): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "America/New_York",
    hourCycle: "h23",
  }).format(new Date(iso));
}

export function localTime(date: Date): string {
  return new Intl.DateTimeFormat("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    timeZone: "America/New_York",
    hourCycle: "h23",
  }).format(date);
}

export function titleCase(value: string): string {
  return value.replaceAll("_", " ");
}

export function peopleLabel(count: number | null): string {
  if (count == null) return "People unknown";
  return count === 1 ? "1 person" : `${count} people`;
}

export function closureKind(source: string): string {
  if (source === "simulation") return "Simulated closure";
  if (source === "verified") return "Verified closure";
  if (source === "reported") return "Reported closure";
  return source.replaceAll("_", " ");
}
