// Input sanitizer and prompt-injection guard (port of backend/security/*.py).

export const MAX_PROMPT_CHARS = 4000;
const MAX_ANSWER_CHARS = 64;

const INJECTION_SIGNATURES: Array<[RegExp, string]> = [
  [/\bignore\s+(all\s+)?(previous|prior|above)\s+instructions\b/i, 'INSTRUCTION_OVERRIDE'],
  [/\byou\s+are\s+now\s+(in\s+)?(developer\s+mode|dan|jailbreak)\b/i, 'JAILBREAK_ATTEMPT'],
  [/\breveal\s+(your\s+)?(system\s+prompt|instructions|secret|api\s*key)\b/i, 'SECRET_EXFILTRATION'],
  [/\bprint\s+(your\s+)?(initial\s+prompt|hidden\s+text)\b/i, 'PROMPT_EXTRACTION'],
  [/\bact\s+as\s+(an\s+unrestricted|a\s+malicious|an\s+evil)\b/i, 'PERSONA_HIJACK'],
  [/\bdo\s+anything\s+now\b/i, 'DAN_OVERRIDE'],
  [/<\s*system\s*>.*<\s*\/\s*system\s*>/i, 'XML_SYSTEM_TAG_INJECTION'],
  [/\[\s*INST\s*\].*\[\s*\/\s*INST\s*\]/i, 'LLAMA_TAG_INJECTION'],
];

export function scanPrompt(text: string): { safe: boolean; pattern: string | null } {
  const normalized = (text || '').trim();
  for (const [pattern, tag] of INJECTION_SIGNATURES) {
    if (pattern.test(normalized)) return { safe: false, pattern: tag };
  }
  return { safe: true, pattern: null };
}

export function sanitizeText(value: unknown, maxLength = MAX_PROMPT_CHARS): string {
  if (typeof value !== 'string' || !value) return '';
  let clean = value.trim().slice(0, maxLength);
  clean = clean.replace(/\x00/g, '').replace(/\r\n/g, '\n');
  clean = clean.replace(/\.\.\/+/g, '');
  return clean;
}

export function sanitizeMathAnswer(value: unknown): string {
  if (typeof value !== 'string' || !value) return '';
  let clean = value.trim().slice(0, MAX_ANSWER_CHARS);
  clean = clean.replace(/<script[\s\S]*?>[\s\S]*?<\/script>/gi, '');
  clean = clean.replace(/<[^>]*>/g, '');
  clean = clean.replace(/[^0-9/\s.-]/g, '');
  return clean.split(/\s+/).filter(Boolean).join(' ');
}
