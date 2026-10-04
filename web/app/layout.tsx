import Link from "next/link";
import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: "manga-director",
  description: "A safe, page-at-a-time manga production workflow dashboard."
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <header className="siteHeader">
          <Link href="/" className="brand" aria-label="manga-director project dashboard">
            manga-director
          </Link>
          <span className="tagline">Page-at-a-time production workflow</span>
        </header>
        <main className="shell">{children}</main>
      </body>
    </html>
  );
}
