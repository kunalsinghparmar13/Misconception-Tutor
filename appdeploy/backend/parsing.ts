// Tolerant parsers for model output (port of LLM/tutor_agents/parsing.py).

const FENCE = /```[ \t]*([A-Za-z0-9_+-]*)[ \t]*\n([\s\S]*?)```/g;

function escapeRe(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function stripNewlines(s: string): string {
  return s.replace(/^\n+|\n+$/g, '');
}

export function extractCodeBlocks(text: string): Array<[string, string]> {
  const blocks: Array<[string, string]> = [];
  for (const m of text.matchAll(FENCE)) blocks.push([m[1].toLowerCase(), stripNewlines(m[2])]);
  if (!blocks.length) {
    const tail = /```[ \t]*([A-Za-z0-9_+-]*)[ \t]*\n([\s\S]*)$/.exec(text);
    if (tail) blocks.push([tail[1].toLowerCase(), stripNewlines(tail[2])]);
  }
  return blocks;
}

export function firstPythonBlock(text: string): string | null {
  const blocks = extractCodeBlocks(text);
  for (const [lang, code] of blocks) {
    if (['python', 'py', 'python3'].includes(lang) && code.trim()) return code;
  }
  for (const [lang, code] of blocks) {
    if (!lang && code.trim()) return code;
  }
  return null;
}

function headingRegex(aliases: string[]): string {
  return aliases.map(escapeRe).join('|');
}

export function splitSections(text: string, headings: Record<string, string[]>): Record<string, string> {
  const patterns = Object.entries(headings).map(([key, aliases]) => [
    key,
    new RegExp(
      '^\\s*(?:#{1,6}\\s*)?(?:\\*\\*|__)?\\s*(?:\\d+[.)]\\s*)?(?:' + headingRegex(aliases) +
        ')\\s*(?:\\*\\*|__)?\\s*[:\\-–—]?\\s*(?:\\*\\*|__)?\\s*(.*)$',
      'i',
    ),
  ] as const);
  const sections: Record<string, string[]> = { _preamble: [] };
  let current = '_preamble';
  let inFence = false;
  for (const line of text.split(/\r?\n/)) {
    if (line.trim().startsWith('```')) {
      inFence = !inFence;
      (sections[current] ||= []).push(line);
      continue;
    }
    let matched: [string, string] | null = null;
    if (!inFence) {
      for (const [key, pattern] of patterns) {
        const m = pattern.exec(line);
        if (m) {
          matched = [key, m[1]];
          break;
        }
      }
    }
    if (matched) {
      current = matched[0];
      sections[current] ||= [];
      if (matched[1].trim()) sections[current].push(matched[1].trim());
    } else {
      (sections[current] ||= []).push(line);
    }
  }
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(sections)) {
    const joined = v.join('\n').trim();
    if (joined) out[k] = joined;
  }
  return out;
}

export function findField(text: string, labels: string[]): string | null {
  const pattern = new RegExp(
    '^\\s*(?:[-*]\\s*)?(?:#{1,6}\\s*)?(?:\\*\\*|__)?\\s*(?:' + headingRegex(labels) +
      ')\\s*(?:\\*\\*|__)?\\s*[:=\\-–—]\\s*(?:\\*\\*|__)?\\s*(.+?)\\s*$',
    'im',
  );
  const m = pattern.exec(text);
  if (!m) return null;
  const value = m[1].trim().replace(/^[*_`]+|[*_`]+$/g, '').trim();
  return value || null;
}

const PROBLEM_SPLIT = new RegExp(
  '^\\s*(?:#{1,6}\\s*)?(?:\\*\\*|__)?\\s*(?:problem|question|exercise|practice)\\s*#?\\s*(\\d+)\\s*(?:\\*\\*|__)?\\s*[:.)\\-–—]?\\s*(?:\\*\\*|__)?\\s*$|' +
    '^\\s*(?:#{1,6}\\s*)?(?:\\*\\*|__)?\\s*(?:problem|exercise|practice)\\s*#?\\s*(\\d+)\\s*(?:\\*\\*|__)?\\s*[:.)\\-–—]\\s*(?:\\*\\*|__)?\\s*(\\S.*)$',
  'i',
);
const FIELD = new RegExp(
  '^\\s*(?:[-*]\\s*)?(?:\\*\\*|__)?\\s*(question|task|prompt|answer|final answer|solution|why|explanation|hint|' +
    'buggy code|starter code|broken code|code|correct code|fixed code|corrected code|expected output)' +
    '\\s*(?:\\*\\*|__)?\\s*[:\\-–—]\\s*(?:\\*\\*|__)?\\s*(.*)$',
  'i',
);
const FIELD_KEYS: Record<string, string> = {
  question: 'question',
  task: 'question',
  prompt: 'question',
  answer: 'answer',
  'final answer': 'answer',
  solution: 'answer',
  why: 'why',
  explanation: 'why',
  hint: 'hint',
  'buggy code': 'code',
  'starter code': 'code',
  'broken code': 'code',
  code: 'code',
  'correct code': 'correct_code',
  'fixed code': 'correct_code',
  'corrected code': 'correct_code',
  'expected output': 'expected_output',
};

export type RawPractice = Record<string, string>;

/** Parse 'Problem N' blocks into dicts with question/answer/code/correct_code/why/hint. */
export function parsePractice(text: string): RawPractice[] {
  const blocks: string[][] = [];
  let current: string[] | null = null;
  let inFence = false;
  for (const line of text.split(/\r?\n/)) {
    if (line.trim().startsWith('```')) inFence = !inFence;
    if (!inFence) {
      const m = PROBLEM_SPLIT.exec(line);
      if (m) {
        current = [];
        blocks.push(current);
        if (m[3]) current.push(`Question: ${m[3]}`);
        continue;
      }
    }
    if (current) current.push(line);
  }

  const items: RawPractice[] = [];
  for (const lines of blocks) {
    const item: RawPractice = {};
    let field: string | null = null;
    let buf: string[] = [];
    let fence = false;
    let fenceBuf: string[] = [];
    let pendingCodeLabel: string | null = null;

    const flush = (): void => {
      if (field && buf.length) {
        const value = buf.join('\n').trim();
        if (value && !(field in item)) item[field] = value;
      }
      buf = [];
    };

    for (const line of lines) {
      const stripped = line.trim();
      if (stripped.startsWith('```')) {
        if (!fence) {
          fence = true;
          fenceBuf = [];
          continue;
        }
        fence = false;
        const code = stripNewlines(fenceBuf.join('\n'));
        const key = pendingCodeLabel || (!('code' in item) ? 'code' : 'correct_code');
        if (code.trim() && !(key in item)) item[key] = code;
        pendingCodeLabel = null;
        continue;
      }
      if (fence) {
        fenceBuf.push(line);
        continue;
      }
      const m = FIELD.exec(line);
      if (m) {
        flush();
        const key = FIELD_KEYS[m[1].toLowerCase()];
        const rest = m[2].trim();
        if (key === 'code' || key === 'correct_code') {
          pendingCodeLabel = key;
          field = null;
          if (rest && !(key in item)) item[key] = rest;
        } else {
          field = key;
          buf = rest ? [rest] : [];
        }
      } else if (field) {
        buf.push(line);
      }
    }
    flush();
    if (fence && fenceBuf.length) {
      const key = pendingCodeLabel || (!('code' in item) ? 'code' : 'correct_code');
      if (!(key in item)) item[key] = stripNewlines(fenceBuf.join('\n'));
    }
    if (item.question || item.code) items.push(item);
  }
  return items;
}
