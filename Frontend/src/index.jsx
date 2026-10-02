import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router'
import { initSentry, rootErrorOptions } from './sentry.js'
import App from './App.jsx'
import './i18n'

initSentry()

const root = createRoot(document.getElementById('root'), rootErrorOptions())

root.render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>
)
