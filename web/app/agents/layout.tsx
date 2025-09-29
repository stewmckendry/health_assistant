import type { Metadata, Viewport } from "next";
import "./agents.css";
import "./critical-styles.css";

export const metadata: Metadata = {
  title: "Ontario Healthcare AI Registry",
  description: "Specialized AI agents for OHIP billing, drug coverage, practice guidelines, and medical education",
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1.0,
  maximumScale: 1.0,
  minimumScale: 1.0,
  userScalable: false,
};

export default function AgentsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="antialiased" data-theme="light">
      {children}
    </div>
  );
}