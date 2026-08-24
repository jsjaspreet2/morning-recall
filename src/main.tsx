import React from 'react'
import ReactDOM from 'react-dom/client'
import { HashRouter } from 'react-router-dom'
import App from './App'
import { ThemeProvider } from './lib/useTheme'
import { DocTitleProvider } from './lib/docTitle'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ThemeProvider>
      <DocTitleProvider>
        <HashRouter>
          <App />
        </HashRouter>
      </DocTitleProvider>
    </ThemeProvider>
  </React.StrictMode>,
)
