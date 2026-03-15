import type { Metadata, Viewport } from "next";
import { Fraunces, Space_Grotesk } from "next/font/google";
import type { ReactNode } from "react";

import "./globals.css";

const displayFont = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
});

const bodyFont = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-body",
});

export const metadata: Metadata = {
  title: "Relational Fraud Intelligence",
  description:
    "Fraud investigation platform with case management, automated alerts, graph analysis, and AI-assisted risk assessment.",
  openGraph: {
    title: "Relational Fraud Intelligence",
    description:
      "Dataset-first fraud triage with statistical analysis, persistent alerts, durable case management, and explainable risk reasoning.",
    type: "website",
    siteName: "Relational Fraud Intelligence",
  },
  twitter: {
    card: "summary",
    title: "Relational Fraud Intelligence",
    description:
      "Dataset-first fraud triage with statistical analysis, persistent alerts, durable case management, and explainable risk reasoning.",
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: dark)", color: "#0b0f14" },
    { media: "(prefers-color-scheme: light)", color: "#f4efe4" },
  ],
};

type RootLayoutProps = {
  children: ReactNode;
};

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en" className={`${displayFont.variable} ${bodyFont.variable}`}>
      <body>
        <a href="#main-content" className="skip-to-content">
          Skip to content
        </a>
        {children}
      </body>
    </html>
  );
}
