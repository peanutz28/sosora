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
