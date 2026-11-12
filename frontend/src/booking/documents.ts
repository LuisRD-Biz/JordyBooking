import type {Row} from '../shared';

export const DOCUMENT_TYPES: Record<string, string> = {
  contract: 'Contrato', deposit: 'Comprobante de anticipo', annex: 'Anexo', other: 'Otro documento',
};
export const ACCEPT = '.pdf,.jpg,.jpeg,.png';

export function fileProblem(file: File, maxBytes: number) {
  if (!/\.(pdf|jpe?g|png)$/i.test(file.name)) return 'Solo se admiten archivos PDF, JPG y PNG.';
  if (maxBytes && file.size > maxBytes) return `El archivo supera ${Math.round(maxBytes / 1048576)} MB.`;
  return '';
}

export function uploadDocument(bookingId: number, file: File, options: {type: string; notes?: string; replaces?: string}, onProgress?: (percent: number) => void): Promise<Row> {
  const query = new URLSearchParams({filename: file.name, document_type: options.type});
  if (options.notes) query.set('notes', options.notes);
  if (options.replaces) query.set('replaces', options.replaces);
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open('POST', `/api/bookings/${bookingId}/documents?${query}`);
    request.setRequestHeader('Content-Type', 'application/octet-stream');
    request.upload.onprogress = event => { if (event.lengthComputable) onProgress?.(Math.round(event.loaded / event.total * 100)); };
    request.onerror = () => reject(new Error('No se pudo enviar el archivo. Revisa tu conexión.'));
    request.onload = () => {
      let body: any = null;
      try { body = JSON.parse(request.responseText); } catch {}
      if (request.status >= 200 && request.status < 300) resolve(body);
      else reject(new Error(typeof body?.detail === 'string' ? body.detail : 'No se pudo guardar el documento.'));
    };
    request.send(file);
  });
}
