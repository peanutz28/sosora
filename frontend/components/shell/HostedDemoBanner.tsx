export function HostedDemoBanner({ loading = false }: { loading?: boolean }) {
  if (process.env.NEXT_PUBLIC_HOSTED_DEMO !== "true") return null;
  return (
    <div
      role="note"
      data-testid="hosted-demo-banner"
      className={`${loading ? "absolute inset-x-0 top-0" : "shrink-0"} border-b border-accent/20 bg-bg px-4 py-1 text-center text-[11px] text-muted`}
    >
      Hosted demo · cached replay · the real system runs offline on one GPU box
    </div>
  );
}
