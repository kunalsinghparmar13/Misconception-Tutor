// Deterministic grounding and verification tools (port of LLM/tutor_agents/grounding.py
// plus the Brown & Burton buggy rules from backend/backend_code.py).
//
// The model writes every explanation, answer and exercise. These tools only compute exact
// facts before generation and re-check the model's output after it. Python code is never
// executed here: AppDeploy has no Python sandbox, so code facts say so honestly.

import { Fraction, fmt, lcm } from './fraction';
import { evaluate, UnsafeExpression } from './expr';
import { firstPythonBlock } from './parsing';

export const PYTHON_SUBJECTS = new Set(['python', 'coding', 'programming', 'computer science', 'cs']);

export interface CodeRun {
  success: boolean;
  stdout?: string;
  error_type?: string;
  error_message?: string;
  line?: number;
}

export interface Grounding {
  kind: string; // fraction | arithmetic | equation | python | general
  expression: string | null;
  verified_answer: string | null;
  student_answer: string | null;
  student_correct: boolean | null;
  misconception_id: string | null;
  replay: string | null;
  code: string | null;
  code_run: CodeRun | null;
  facts: string[];
}

export function emptyGrounding(): Grounding {
  return {
    kind: 'general',
    expression: null,
    verified_answer: null,
    student_answer: null,
    student_correct: null,
    misconception_id: null,
    replay: null,
    code: null,
    code_run: null,
    facts: [],
  };
}

export function isCode(g: Grounding): boolean {
  return g.kind === 'python';
}

export function factsBlock(g: Grounding): string {
  if (!g.facts.length) return '';
  return (
    'Verified facts (computed exactly by tools - trust these over your own mental arithmetic):\n' +
    g.facts.map((f) => `- ${f}`).join('\n')
  );
}

/** No sandbox on this host, so code is never run. Callers treat null as 'could not run'. */
export function runCode(_code: string): CodeRun | null {
  return null;
}

// ----------------------------------------------------------------------------- numbers

export function normalizeExpression(text: string, implicitVariable: string | null = null): string {
  let s = text.trim();
  s = s.replace(/×/g, '*').replace(/÷/g, '/').replace(/−/g, '-').replace(/–/g, '-').replace(/\^/g, '**');
  s = s.replace(/(?<=\d),(?=\d{3}\b)/g, '');
  if (implicitVariable === null) s = s.replace(/(?<=\d)\s*[xX]\s*(?=\d)/g, '*');
  if (implicitVariable) {
    const v = implicitVariable.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    s = s.replace(new RegExp(`(?<=[\\d\\)])\\s*(${v})\\b`, 'g'), '*$1');
    s = s.replace(new RegExp(`\\b(${v})\\s*(?=\\()`, 'g'), '$1*');
  }
  s = s.replace(/(?<=\d)\s*(?=\()/g, '*');
  s = s.replace(/(?<=\))\s*(?=[\d(])/g, '*');
  return s;
}

const NUMBER = /-?\d+(?:\.\d+)?(?:\s*\/\s*-?\d+)?/;

/** Parse '5/12', '0.5', '-3', 'x = 4' ... into a Fraction (first number found). */
export function parseNumber(text: string | null | undefined): Fraction | null {
  const m = NUMBER.exec((text || '').replace(/,/g, ''));
  if (!m) return null;
  const token = m[0].replace(/ /g, '').replace(/\s/g, '');
  try {
    if (token.includes('/')) {
      const [n, d] = token.split('/');
      const nn = Math.trunc(parseFloat(n));
      const dd = Math.trunc(parseFloat(d));
      if (parseFloat(d) === 0 || dd === 0) return null;
      return new Fraction(BigInt(nn), BigInt(dd));
    }
    return Fraction.fromDecimal(token);
  } catch {
    return null;
  }
}

export function numbersIn(text: string): Fraction[] {
  const out: Fraction[] = [];
  const re = new RegExp(NUMBER.source, 'g');
  for (const m of (text || '').replace(/,/g, '').matchAll(re)) {
    const n = parseNumber(m[0]);
    if (n) out.push(n);
  }
  return out;
}

// ------------------------------------------------------------------- fraction answers

const RE_INTEGER = /^-?\d+$/;
const RE_FRACTION = /^(-?\d+)\s*\/\s*(-?\d+)$/;
const RE_MIXED = /^(-?\d+)\s+(\d+)\s*\/\s*(\d+)$/;
const RE_DECIMAL = /^-?\d+\.\d+$/;

/** Student answer formats: '5/12', ' 5 / 12 ', '2', '1 1/2', '0.5'. */
export function parseFraction(input: string): Fraction | null {
  const s = (input || '').trim();
  if (!s) return null;
  try {
    if (RE_INTEGER.test(s)) return new Fraction(BigInt(s));
    let m = RE_FRACTION.exec(s);
    if (m) {
      const den = BigInt(m[2]);
      return den === 0n ? null : new Fraction(BigInt(m[1]), den);
    }
    m = RE_MIXED.exec(s);
    if (m) {
      const whole = BigInt(m[1]);
      const num = BigInt(m[2]);
      const den = BigInt(m[3]);
      if (den === 0n) return null;
      const absWhole = whole < 0n ? -whole : whole;
      const frac = new Fraction(absWhole * den + num, den);
      return whole < 0n ? frac.neg() : frac;
    }
    if (RE_DECIMAL.test(s)) return Fraction.fromDecimal(s).limitDenominator(1000n);
  } catch {
    return null;
  }
  return null;
}

export function checkAnswer(userInput: string, correctAnswer: string): [boolean, Fraction | null] {
  const user = parseFraction(userInput);
  const correct = parseFraction(correctAnswer);
  if (!user || !correct) return [false, user];
  return [user.equals(correct), user];
}

// ---------------------------------------------------------------- buggy rules (M1-M5)

type Bug = (a: bigint, b: bigint, c: bigint, d: bigint) => [bigint, bigint];

export const BUGS_ADD: Record<string, Bug> = {
  M1_add_across: (a, b, c, d) => [a + c, b + d],
  M2_tops_add_bottoms_multiply: (a, b, c, d) => [a + c, b * d],
  M3_no_scaling: (a, b, c, d) => [a + c, lcm(b, d)],
};

export const BUGS_DIV: Record<string, Bug> = {
  M4_divide_multiply_across: (a, b, c, d) => [a * c, b * d],
  M5_flip_wrong_fraction: (a, b, c, d) => [b * c, a * d],
};

export const EXPLANATION_TITLES: Record<string, string> = {
  M1_add_across: 'Adding Numerators and Denominators Directly',
  M2_tops_add_bottoms_multiply: 'Adding Tops and Multiplying Bottoms',
  M3_no_scaling: 'Finding Common Denominator Without Scaling Numerators',
  M4_divide_multiply_across: 'Multiplying Straight Across When Dividing',
  M5_flip_wrong_fraction: 'Flipping the First Fraction Instead of the Second',
};

function reduced(top: bigint, bot: bigint): string {
  const red = fmt(new Fraction(top, bot));
  return red !== `${top}/${bot}` ? ` -> ${red}.` : '.';
}

export function generateReplay(misc: string, a: bigint, b: bigint, c: bigint, d: bigint): string {
  if (misc === 'M1_add_across') {
    const top = a + c;
    const bot = b + d;
    return `You added tops (${a}+${c}=${top}) and bottoms (${b}+${d}=${bot}), yielding ${top}/${bot}` + reduced(top, bot) + ' That matches your answer!';
  }
  if (misc === 'M2_tops_add_bottoms_multiply') {
    const top = a + c;
    const bot = b * d;
    return `You added tops (${a}+${c}=${top}) and multiplied bottoms (${b}×${d}=${bot}), yielding ${top}/${bot}` + reduced(top, bot) + ' That matches your answer!';
  }
  if (misc === 'M3_no_scaling') {
    const top = a + c;
    const bot = lcm(b, d);
    return `You found common denominator lcm(${b},${d})=${bot}, but added numerators (${a}+${c}=${top}) without scaling, giving ${top}/${bot}` + reduced(top, bot) + ' That matches your answer!';
  }
  if (misc === 'M4_divide_multiply_across') {
    const top = a * c;
    const bot = b * d;
    return `You multiplied across without flipping: ${a}×${c}=${top} on top, ${b}×${d}=${bot} on bottom, giving ${top}/${bot}` + reduced(top, bot) + ' That matches your answer!';
  }
  if (misc === 'M5_flip_wrong_fraction') {
    const top = b * c;
    const bot = a * d;
    return `You inverted the 1st fraction (${b}/${a}) instead of the 2nd (${d}/${c}), giving (${b}×${c})/(${a}×${d}) = ${top}/${bot}` + reduced(top, bot) + ' That matches your answer!';
  }
  return 'Unknown mistake pattern detected.';
}

function matchBuggyRule(g: Grounding, sym: string, a: bigint, b: bigint, c: bigint, d: bigint, student: Fraction): void {
  const rules = sym === '+' ? BUGS_ADD : BUGS_DIV;
  for (const [bugId, fn] of Object.entries(rules)) {
    try {
      const [top, bot] = fn(a, b, c, d);
      if (bot !== 0n && new Fraction(top, bot).equals(student)) {
        g.misconception_id = bugId;
        g.replay = generateReplay(bugId, a, b, c, d);
        const title = EXPLANATION_TITLES[bugId] || bugId;
        g.facts.push(`The learner's wrong answer is exactly what the buggy rule '${title}' (${bugId}) produces` + (g.replay ? `: ${g.replay}` : '.'));
        return;
      }
    } catch {
      continue;
    }
  }
}

// --------------------------------------------------------------------------- python

const QUESTION_PREFIXES = ['why', 'how', 'what', 'where', 'when', 'can ', 'could', 'is ', 'it ', 'i ', 'my ', 'please', 'help'];

function looksLikeCodeLine(line: string): boolean {
  const stripped = line.trim();
  if (!stripped) return false;
  const starts = ['#', 'def ', 'class ', 'if ', 'elif ', 'else:', 'for ', 'while ', 'try:', 'except', 'finally:', 'return ', 'import ', 'from ', 'with ', 'async '];
  if (starts.some((p) => stripped.startsWith(p))) return true;
  if (/^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)?\s*=/.test(stripped)) return true;
  if (/^(?:print|len|range|sum|int|float|str|list|dict|set)\s*\(/.test(stripped)) return true;
  if (/^[)\]}]/.test(stripped)) return true;
  return /^\s/.test(line) && !QUESTION_PREFIXES.some((p) => stripped.toLowerCase().startsWith(p));
}

/** Port of python_debugger.split_input: the code part of mixed prose/code input. */
function splitCode(text: string): string {
  const block = /```(?:python)?\s*\n([\s\S]*?)\n```/i.exec(text);
  if (block) return block[1].trim();
  const lines = text.trim().split(/\r?\n/);
  let start = lines.findIndex((l) => looksLikeCodeLine(l));
  if (start < 0) start = 0;
  const code: string[] = [];
  let sawCode = false;
  for (const line of lines.slice(start)) {
    const stripped = line.trim();
    if (stripped && sawCode && !looksLikeCodeLine(line)) continue;
    if (!stripped && sawCode) {
      code.push(line);
      continue;
    }
    if (looksLikeCodeLine(line)) {
      code.push(line);
      sawCode = true;
    }
  }
  return code.join('\n').trim() || text.trim();
}

export function looksLikePython(text: string): boolean {
  if (text.includes('```')) return true;
  const codeLike = /^\s*(def |class |import |from \S+ import |for .+ in .+:|while .+:|if .+:|elif .+:|else:|try:|except|return |print\(|\w+\s*=\s*\S)/;
  const count = text.split(/\r?\n/).filter((l) => codeLike.test(l)).length;
  return count >= 2 || /\b(def |import |print\()/.test(text);
}

export function extractPython(text: string): string | null {
  const block = firstPythonBlock(text);
  if (block) return block;
  if (!looksLikePython(text)) return null;
  return splitCode(text) || null;
}

// ------------------------------------------------------------------------- grounding

const FRACTION_OP = /(-?\d+)\s*\/\s*(\d+)\s*([+\-*×x÷/])\s*(-?\d+)\s*\/\s*(\d+)/;
const AFTER_EQ = /(?:=|\bgot\b|\bget\b|\banswer(?:\s+is)?\b|\bresult(?:\s+is)?\b|\bgives?\b|\bwrote\b|\bsay\b|\bsaid\b)\s*:?\s*(-?\d+(?:\.\d+)?(?:\s*\/\s*\d+)?)/i;
const ARITH_CLAIM = /(?<expr>(?:\(?\s*-?\d[\d.,]*\s*\)?\s*[+\-*/×÷^x]\s*)+\(?\s*-?\d[\d.,]*\s*\)?(?:\s*[+\-*/×÷^x]\s*\(?\s*-?\d[\d.,]*\s*\)?)*)\s*=\s*(?<ans>-?\d[\d.,]*(?:\s*\/\s*\d+)?)/;
const ARITH_ASK = /(?:what\s+is|calculate|compute|evaluate|simplify|find)\s+(?<expr>[\d\s.,+\-*/×÷^()xX]*\d[\d\s.,+\-*/×÷^()xX]*)\??/i;
const EQUATION = /(?<lhs>[\dx\s.+\-*/()^]*x[\dx\s.+\-*/()^]*|[\d\s.+\-*/()^]+)\s*=\s*(?<rhs>[\dx\s.+\-*/()^]+)/gi;

function squash(s: string): string {
  return s.split(/\s+/).filter(Boolean).join(' ');
}

function stripChars(s: string, chars: string): string {
  let start = 0;
  let end = s.length;
  while (start < end && chars.includes(s[start])) start++;
  while (end > start && chars.includes(s[end - 1])) end--;
  return s.slice(start, end);
}

function solveLinear(lhs: string, rhs: string): Fraction | null {
  try {
    const l = normalizeExpression(lhs.toLowerCase(), 'x');
    const r = normalizeExpression(rhs.toLowerCase(), 'x');
    const f = (x: Fraction): Fraction => evaluate(l, { x }).sub(evaluate(r, { x }));
    const f0 = f(new Fraction(0n));
    const f1 = f(new Fraction(1n));
    const f2 = f(new Fraction(2n));
    const slope = f1.sub(f0);
    if (slope.isZero() || !f2.sub(f1).equals(slope)) return null;
    return f0.neg().div(slope);
  } catch {
    return null;
  }
}

/** Compute exact facts about the learner's question. Never throws. */
export function ground(question: string, subject = ''): Grounding {
  try {
    return groundInner(question, subject);
  } catch {
    return emptyGrounding();
  }
}

function verdict(g: Grounding): void {
  g.facts.push(`The learner's answer ${g.student_answer} is ${g.student_correct ? 'correct' : 'NOT correct'}.`);
}

function groundInner(question: string, subject: string): Grounding {
  const g = emptyGrounding();
  const isPythonSubject = PYTHON_SUBJECTS.has(subject.trim().toLowerCase());

  // --- fractions (+ buggy-rule detection)
  const fm = FRACTION_OP.exec(question);
  if (fm && !(isPythonSubject && question.includes('```'))) {
    const a = BigInt(fm[1]);
    const b = BigInt(fm[2]);
    const c = BigInt(fm[4]);
    const d = BigInt(fm[5]);
    const op = fm[3];
    if (b !== 0n && d !== 0n) {
      const fa = new Fraction(a, b);
      const fb = new Fraction(c, d);
      const sym = ({ '+': '+', '-': '-', '*': '×', '×': '×', x: '×', '÷': '÷', '/': '÷' } as Record<string, string>)[op];
      let exact: Fraction | null = null;
      try {
        exact = sym === '+' ? fa.add(fb) : sym === '-' ? fa.sub(fb) : sym === '×' ? fa.mul(fb) : fa.div(fb);
      } catch {
        exact = null;
      }
      if (exact) {
        g.kind = 'fraction';
        g.expression = `${a}/${b} ${sym} ${c}/${d}`;
        g.verified_answer = fmt(exact);
        g.facts.push(`Exact value: ${g.expression} = ${g.verified_answer}.`);
        const after = question.slice((fm.index || 0) + fm[0].length);
        const sm = AFTER_EQ.exec(after);
        const student = sm ? parseNumber(sm[1]) : null;
        if (student) {
          g.student_answer = fmt(student);
          g.student_correct = student.equals(exact);
          verdict(g);
          if (!g.student_correct && (sym === '+' || sym === '÷')) matchBuggyRule(g, sym, a, b, c, d, student);
        }
        return g;
      }
    }
  }

  // --- python code (described, never executed here)
  if (isPythonSubject || looksLikePython(question)) {
    const code = extractPython(question);
    if (code && (isPythonSubject || looksLikePython(code))) {
      g.kind = 'python';
      g.code = code;
      g.code_run = runCode(code);
      g.facts.push('(The code could not be executed here; reason about it carefully.)');
      return g;
    }
  }

  // --- arithmetic claim "12 * 7 = 82"
  const cm = ARITH_CLAIM.exec(question);
  if (cm && cm.groups) {
    let exact: Fraction | null = null;
    let claimed: Fraction | null = null;
    try {
      exact = evaluate(normalizeExpression(cm.groups.expr));
      claimed = parseNumber(cm.groups.ans);
    } catch (e) {
      if (!(e instanceof UnsafeExpression) && !(e instanceof RangeError)) throw e;
    }
    if (exact) {
      g.kind = 'arithmetic';
      g.expression = squash(cm.groups.expr);
      g.verified_answer = fmt(exact);
      g.facts.push(`Exact value: ${g.expression} = ${g.verified_answer}.`);
      if (claimed) {
        g.student_answer = fmt(claimed);
        g.student_correct = claimed.equals(exact);
        verdict(g);
      }
      return g;
    }
  }

  // --- linear equation in x
  for (const em of question.matchAll(EQUATION)) {
    if (!em.groups) continue;
    const lhs = stripChars(em.groups.lhs, ' .');
    const rhs = stripChars(em.groups.rhs, ' .');
    if (!(lhs + rhs).toLowerCase().includes('x')) continue;
    if (/^\s*x\s*$/i.test(lhs) && /^\s*-?[\d./]+\s*$/.test(rhs)) continue; // an answer, not the equation
    const root = solveLinear(lhs, rhs);
    if (!root) continue;
    g.kind = 'equation';
    g.expression = `${squash(lhs)} = ${squash(rhs)}`;
    g.verified_answer = `x = ${fmt(root)}`;
    g.facts.push(`Exact solution of ${g.expression}: ${g.verified_answer}.`);
    const rest = question.split(em[0]).join(' ');
    const am = /\bx\s*=\s*(-?\d+(?:\.\d+)?(?:\s*\/\s*\d+)?)/i.exec(rest);
    if (am) {
      const claimed = parseNumber(am[1]);
      if (claimed) {
        g.student_answer = `x = ${fmt(claimed)}`;
        g.student_correct = claimed.equals(root);
        verdict(g);
      }
    }
    return g;
  }

  // --- plain "what is 12*7+3?"
  const qm = ARITH_ASK.exec(question);
  if (qm && qm.groups) {
    const expr = stripChars(qm.groups.expr, ' ?.');
    if (/\d\s*[+\-*/×÷^xX]\s*\(?\d/.test(expr)) {
      let exact: Fraction | null = null;
      try {
        exact = evaluate(normalizeExpression(expr));
      } catch {
        exact = null;
      }
      if (exact) {
        g.kind = 'arithmetic';
        g.expression = squash(expr);
        g.verified_answer = fmt(exact);
        g.facts.push(`Exact value: ${g.expression} = ${g.verified_answer}.`);
        return g;
      }
    }
  }
  return g;
}
