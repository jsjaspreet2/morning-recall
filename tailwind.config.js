/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  // Theme is a deliberate choice (Light / Dark / System), not just the OS
  // preference, so the `dark` class on <html> — set by the inline script in
  // index.html and kept in sync by src/lib/theme.ts — is what drives `dark:`.
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Consolas', 'monospace'],
      },
    },
  },
  // No safelist needed: every accent class is written as a complete literal
  // string in src/lib/accents.ts, so Tailwind's content scanner keeps them.
  plugins: [],
}
