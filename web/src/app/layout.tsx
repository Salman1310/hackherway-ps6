import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Access Assistant — Sun Life",
  description: "AI-powered access provisioning for Sun Life",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full">{children}</body>
    </html>
  );
}
