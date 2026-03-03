/**
 * Module overview for frontend/app/layout.tsx.
 * Contains runtime logic for this feature area in LaunchPad Conversion Lab.
 */
import "./globals.css";
import type { Metadata } from "next";
import { Manrope } from "next/font/google";

const manrope = Manrope({ subsets: ["latin"], weight: ["400", "500", "600", "700"] });

export const metadata: Metadata = {
  title: "LaunchPad Conversion Lab",
  description: "E-commerce experimentation copilot"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={manrope.className}>
        <main className="mx-auto min-h-screen max-w-[1300px] p-6 md:p-8">{children}</main>
      </body>
    </html>
  );
}
