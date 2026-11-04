import {renderToString} from 'react-dom/server';
import {App} from './App';
import {contactLinks, hero, photographs} from './content';

export function render(path: string) { return renderToString(<App path={path} />); }
export function publicPhotos() { return [hero, ...photographs]; }
export function validateContacts() { return contactLinks(); }
