import {renderToString} from 'react-dom/server';
import {App} from './App';
import {contactLinks} from './content';
import {photographs, source} from './photos';

export function render(path: string) { return renderToString(<App path={path} />); }
export function publicPhotos() { return photographs.map(p => ({...p, src: source(p)})); }
export function validateContacts() { return contactLinks(); }
