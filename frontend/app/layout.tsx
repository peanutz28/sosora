import type { Metadata } from "next";
import { DM_Sans, IBM_Plex_Mono, Manrope } from "next/font/google";
import "./globals.css";

// Type system from Jia's dashboard: DM Sans for UI, Manrope for display, Plex Mono for data.
const dm = DM_Sans({ subsets: ["latin"], variable: "--font-dm" });
const manrope = Manrope({ subsets: ["latin"], weight: ["600", "700", "800"], variable: "--font-manrope" });
const plexMono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--font-plex-mono" });

export const metadata: Metadata = {
  title: "SOSora · Rescue Intelligence",
  description: "The rescue map that keeps working when the towers and the roads don't. Hackathon prototype; simulated incidents on real roads.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${dm.variable} ${manrope.variable} ${plexMono.variable}`}>
      <body className="antialiased">{children}</body>
    </html>
  );
}
