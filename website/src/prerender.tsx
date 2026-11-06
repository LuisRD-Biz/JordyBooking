import {renderToString} from 'react-dom/server';
import {App} from './App';
import {contactLinks} from './content';
import {manifest} from './photo-manifest';
export {validateManifest, selectPhotos} from './photos';

export function render(path: string) { return renderToString(<App path={path} />); }
export function publicPhotos() { return manifest; }
export function validateContacts() { return contactLinks(); }
