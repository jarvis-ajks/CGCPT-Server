import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// StrictMode is intentionally off: the upstream Materials Project viewer
// (@materialsproject/mp-react-components 0.5.2) throws during React's
// development-only mount/unmount probe, which empties the whole tree.
createRoot(document.getElementById('root')!).render(<App />)
