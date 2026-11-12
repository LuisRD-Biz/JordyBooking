import React from 'react';
import {createRoot} from 'react-dom/client';
import {App} from './app/App';
import {applyTheme, storedTheme} from './lib/theme';
import './style.css';

applyTheme(storedTheme());
createRoot(document.getElementById('root')!).render(<App/>);
