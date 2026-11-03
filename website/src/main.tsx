import {hydrateRoot, createRoot} from 'react-dom/client';
import '@fontsource/cormorant-garamond/latin-400.css';
import '@fontsource/cormorant-garamond/latin-400-italic.css';
import '@fontsource/manrope/latin-400.css';
import '@fontsource/manrope/latin-600.css';
import './style.css';
import {App} from './App';

const root = document.getElementById('root')!;
const app = <App path={window.location.pathname} />;
if (root.querySelector('header')) hydrateRoot(root, app);
else createRoot(root).render(app);
