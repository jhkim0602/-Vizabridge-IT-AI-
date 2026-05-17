import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Vizabridge Intern Interview",
  description:
    "An interview session for the Vizabridge AI chatbot team — sharing the data pipeline and learning how the chatbot is being built.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-ink-50 font-sans text-ink-900 antialiased">
        <div className="mx-auto flex min-h-screen w-full max-w-4xl flex-col px-4 py-8 sm:px-6 sm:py-12">
          <header className="mb-8 flex items-center justify-between">
            <a
              href="/"
              className="flex items-center gap-2 text-sm font-semibold tracking-tight text-ink-900"
            >
              <span className="inline-flex h-7 w-7 items-center justify-center rounded-md bg-brand-600 text-xs font-bold text-white">
                VB
              </span>
              <span>Vizabridge · Intern Interview</span>
            </a>
            <a
              href="https://github.com/jhkim0602/-vizabridge-it-ai-"
              target="_blank"
              rel="noreferrer"
              className="text-xs text-ink-500 hover:text-ink-700"
            >
              Project repo
            </a>
          </header>
          <main className="flex-1">{children}</main>
          <footer className="mt-12 border-t border-ink-200 pt-6 text-xs text-ink-500">
            <p>
              Vizabridge — Korean immigration/visa data pipeline. This interview
              is for internal research only. Responses stay in your browser
              unless you choose to download or email them.
            </p>
          </footer>
        </div>
      </body>
    </html>
  );
}
