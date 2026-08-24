import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_SITE_URL ??
      "https://customwear-analytics-dashboard.achan7632917.chatgpt.site",
  ),
  title: "CustomWear Analytics Dashboard",
  description:
    "Customer segmentation, retention insights, and purchasing behavior for modern apparel brands.",
  icons: { icon: "/favicon.svg", shortcut: "/favicon.svg" },
  openGraph: {
    title: "CustomWear Analytics",
    description: "Customer intelligence for modern apparel brands",
    images: [{ url: "/og.png", width: 1200, height: 630, alt: "CustomWear Analytics" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "CustomWear Analytics",
    description: "Customer intelligence for modern apparel brands",
    images: ["/og.png"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
