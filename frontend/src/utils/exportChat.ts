import { Message } from '@/types';

export function exportChatAsMarkdown(messages: Message[], patientName?: string): string {
  const header = [
    '# Atlas Chat Export',
    `**Date:** ${new Date().toLocaleDateString()}`,
    patientName ? `**Patient:** ${patientName}` : '',
    `**Messages:** ${messages.length}`,
    '',
    '---',
    '',
  ].filter(Boolean).join('\n');

  const body = messages.map(m => {
    const role = m.role === 'user' ? 'User' : 'Assistant';
    const time = m.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    let text = `### ${role} (${time})\n\n${m.content}`;
    if (m.sources && m.sources.length > 0) {
      text += `\n\n> Sources: ${m.sources.map(s => s.doc_id).join(', ')}`;
    }
    return text;
  }).join('\n\n---\n\n');

  return header + body;
}

export function downloadMarkdown(content: string, filename: string) {
  const blob = new Blob([content], { type: 'text/markdown' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
