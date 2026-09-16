let csrf = '';
export function setCsrf(value) { csrf = value || ''; }
export async function api(path, { method = 'GET', body, headers = {}, file = false } = {}) {
  let response;
  try {
    response = await fetch(`/api${path}`, { method, credentials: 'same-origin',
      headers: { ...(body ? { 'Content-Type': 'application/json' } : {}), ...(csrf ? { 'X-CSRF-Token': csrf } : {}), ...headers },
      body: body ? JSON.stringify(body) : undefined });
  } catch { throw new Error('Não foi possível conectar ao NexusGest. Verifique se o servidor está aberto.'); }
  if (file && response.ok) return response.blob();
  const result = await response.json().catch(() => ({ message: 'Resposta inválida do servidor.' }));
  if (!response.ok) {
    const error = new Error(result.message || 'Não foi possível concluir a operação.'); error.status = response.status;
    if (response.status === 401 && !path.startsWith('/auth/')) window.dispatchEvent(new Event('session-expired'));
    throw error;
  }
  if (result.data?.csrf) setCsrf(result.data.csrf);
  return result.data;
}
export async function downloadReport(kind, format) {
  const blob = await api(`/reports/${kind}.${format}`, { file: true });
  const url = URL.createObjectURL(blob); const link = document.createElement('a');
  link.href = url; link.download = `nexusgest-${kind}.${format}`; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
