import type { Metadata } from "next";
import ThemeScript from "@/components/ThemeScript";
import "./globals.css";

export const metadata: Metadata = {
  title: "FEAR - Flood Economics and Risk",
  description:
    "How FEMA flood zone reclassifications affect home property values: an interactive research presentation using difference-in-differences and event study methods.",
  openGraph: {
    title: "FEAR - Flood Economics and Risk",
    description:
      "Interactive research: LOMR flood zone reclassifications reduce home values by 2.7% over five years.",
    type: "website",
    images: [
      {
        url: "https://fear.camkeith.me/images/event_study_main.png",
        alt: "Event study: LOMR effect on home values",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "FEAR - Flood Economics and Risk",
    description:
      "Interactive research: LOMR flood zone reclassifications reduce home values by 2.7% over five years.",
    images: ["https://fear.camkeith.me/images/event_study_main.png"],
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="icon" href="/favicon.ico" sizes="any" />
      </head>
      <body className="antialiased">
        <ThemeScript />
        {children}
      </body>
    </html>
  );
}
