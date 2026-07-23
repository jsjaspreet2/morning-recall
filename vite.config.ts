import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Repo name for GitHub Pages. If you deploy to a different repo, change this
// (or set to '/' for Netlify/Vercel/custom-domain roots).
const BASE = '/morning-recall/'

// https://vite.dev/config/
export default defineConfig({
  base: BASE,
  plugins: [react()],
  assetsInclude: ['**/*.md'],
})
