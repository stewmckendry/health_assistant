import type { Metadata, Viewport } from "next";
import "./agents.css";

export const metadata: Metadata = {
  title: "Ontario Healthcare AI Registry",
  description: "Specialized AI agents for OHIP billing, drug coverage, practice guidelines, and medical education",
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
};

export default function AgentsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="agents-light-mode agents-page-wrapper" data-theme="light">
      {children}
    </div>
  );
}