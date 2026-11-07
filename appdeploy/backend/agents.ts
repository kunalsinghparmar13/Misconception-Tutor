// The four agents (port of LLM/tutor_agents/agents.py, fast mode).
// Each is a prompt + parser around the user's fine-tuned model.

import * as gr from './grounding';
import * as parsing from './parsing';
import * as prompts from './prompts';
import { chat, ChatResult } from './model';

// Output-token budgets of the Python app's fast mode (the default).
const TOKENS = { explainer: 260, solver: 300, practice: 420, reviewer: 120 };

export const EXPLAIN_HEADINGS: Record<string, string[]> = {
  misconception: ['misconception'],
  what_went_wrong: ['what went wrong', 'where it went wrong', 'the mistake'],
  why_mistake: ['why you made this mistake', 'why this mistake happens', 'why you made that mistake', 'why it happens'],
  correct_thinking: ['how to think about it correctly', 'the right way to think', 'correct thinking', 'how to fix it'],
  check_yourself: ['check yourself', 'try this'],
};

export function clip(text: string, limit: number): string {
  const t = (text || '').trim();
  if (t.length <= limit) return t;
  const cut = t.slice(0, limit);
  const space = cut.lastIndexOf(' ');
  return (space > 0 ? cut.slice(0, space) : cut) + ' ...';
}

export interface Explanation {
  text: string;
  sections: Record<string, string>;
  misconception: string;
  model: string;
  seconds: number;
}

export interface Solution {
  kind: 'math' | 'code';
  text: string;
  final_answer: string | null;
  steps: string;
  code: string | null;
  what_changed: string;
  run: gr.CodeRun | null;
  model: string;
  seconds: number;
}

export interface PracticeItem {
  id: string;
  type: 'math' | 'code';
  prompt: string;
  correct_answer: string | null;
  code: string | null;
  correct_code: string | null;
  expected_output: string | null;
  explanation: string;
  verified: boolean;
  verification: string;
}

export interface Check {
  name: string;
  status: 'pass' | 'fail' | 'warn' | 'skip';
  detail: string;
}

export interface Review {
  approved: boolean;
  verified: boolean;
  checks: Check[];
  issues: string[];
  model_verdict: string | null;
  model_notes: string;
  revisions: number;
  seconds: number;
}

function ask(system: string, user: string, maxTokens: number, temperature: number): Promise<ChatResult> {
  return chat(
    [
      { role: 'system', content: system },
      { role: 'user', content: user },
    ],
    maxTokens,
    temperature,
  );
}

// ------------------------------------------------------------------------------ agent 1
export async function explain(question: string, g: gr.Grounding): Promise<Explanation> {
  let user = `Learner's message:\n${question}\n`;
  if (gr.factsBlock(g)) user += `\n${gr.factsBlock(g)}\n`;
  const res = await ask(prompts.EXPLAINER, user, TOKENS.explainer, 0.2);
  const sections = parsing.splitSections(res.text, EXPLAIN_HEADINGS);
  let label = (sections.misconception || parsing.findField(res.text, ['misconception']) || '').split('\n')[0];
  label = label.trim().replace(/^[ .*]+|[ .*]+$/g, '');
  label = clip(label, 80) || g.misconception_id || '';
  return { text: res.text, sections, misconception: label, model: res.model, seconds: res.seconds };
}

// ------------------------------------------------------------------------------ agent 2
export async function solve(question: string, g: gr.Grounding): Promise<Solution> {
  const isCode = gr.isCode(g);
  const system = isCode ? prompts.SOLVER_CODE : prompts.SOLVER_MATH;
  let user: string;
  if (isCode) {
    user =
      "Task: write the corrected, complete Python program for the learner's problem below. " +
      "Do not ask questions. Start your reply with 'Corrected code:'.\n\n" +
      `Learner's problem:\n${question}\n`;
  } else {
    const problem = g.expression || question;
    user =
      'Task: solve this maths problem yourself and show the steps. Do not ask the learner anything. ' +
      "Start your reply with 'Final answer:', then 'Steps:' as a numbered list, then 'Check:'.\n\n" +
      `Problem: ${problem}\n`;
    if (g.expression && g.expression !== question) user += `(The learner wrote: ${question})\n`;
  }
  if (gr.factsBlock(g)) user += `\n${gr.factsBlock(g)}\n`;
  const res = await ask(system, user, TOKENS.solver, 0.1);
  if (isCode) {
    const code = parsing.firstPythonBlock(res.text);
    const changed = parsing.findField(res.text, ['what changed']) || '';
    const run = code ? gr.runCode(code) : null;
    return { kind: 'code', text: res.text, final_answer: null, steps: '', code, what_changed: changed, run, model: res.model, seconds: res.seconds };
  }
  const final = parsing.findField(res.text, ['final answer', 'answer']);
  const sections = parsing.splitSections(res.text, { steps: ['steps', 'solution steps'], check: ['check'] });
  return { kind: 'math', text: res.text, final_answer: final, steps: sections.steps || '', code: null, what_changed: '', run: null, model: res.model, seconds: res.seconds };
}

// ------------------------------------------------------------------------------ agent 3
/** What makes two practice items 'the same exercise' (maths: numbers and operators; code: the code). */
export function practiceKey(type: 'math' | 'code', prompt: string, code: string | null = null): string {
  if (type === 'math') {
    const nums = (prompt.match(/\d+(?:\.\d+)?/g) || []).sort();
    const ops = (prompt.match(/[+\-*/÷×^]/g) || []).sort().join('');
    return 'math:' + nums.join(',') + '|' + ops;
  }
  let source = code || prompt || '';
  source = source.replace(/#[^\n]*/g, '');
  return source.toLowerCase().replace(/\s+/g, '');
}

/** Ratcliff/Obershelp similarity, like difflib.SequenceMatcher(None, a, b).ratio(). */
function similarity(a: string, b: string): number {
  function matches(x: string, y: string): number {
    if (!x.length || !y.length) return 0;
    let best = 0;
    let bi = 0;
    let bj = 0;
    const prev = new Array<number>(y.length + 1).fill(0);
    for (let i = 1; i <= x.length; i++) {
      let diag = 0;
      for (let j = 1; j <= y.length; j++) {
        const tmp = prev[j];
        prev[j] = x[i - 1] === y[j - 1] ? diag + 1 : 0;
        if (prev[j] > best) {
          best = prev[j];
          bi = i - best;
          bj = j - best;
        }
        diag = tmp;
      }
    }
    if (!best) return 0;
    return best + matches(x.slice(0, bi), y.slice(0, bj)) + matches(x.slice(bi + best), y.slice(bj + best));
  }
  const total = a.length + b.length;
  return total ? (2 * matches(a, b)) / total : 1;
}

export function similar(a: string, b: string): boolean {
  if (!a || !b) return false;
  if (a === b) return true;
  if (a.startsWith('math:') || b.startsWith('math:')) return false;
  return similarity(a.slice(0, 600), b.slice(0, 600)) >= 0.85;
}

export interface BatchRequest {
  question: string;
  grounding: gr.Grounding;
  misconception: string;
  count: number;
  avoid: string[];
  level: string;
  mistakes: string[];
  temperature: number;
}

/** One model call that writes up to ``count`` practice items. */
export async function practiceBatch(req: BatchRequest): Promise<PracticeItem[]> {
  const g = req.grounding;
  const code = gr.isCode(g);
  const label = req.misconception || g.misconception_id || "the mistake in the learner's work";
  const levelRule = prompts.LEVEL_RULES[req.level] || prompts.LEVEL_RULES.start;
  const system = prompts.fill(code ? prompts.PRACTICE_CODE : prompts.PRACTICE_MATH, {
    count: req.count,
    misconception: label,
    level_rule: levelRule,
  });
  let user = `The learner's original problem:\n${clip(req.question, 1200)}\n`;
  if (code) {
    user +=
      '\nDo NOT copy this code. Each exercise needs its own task, its own data and its own variable names ' +
      '(for example scores, temperatures, words, ages), but the same kind of bug.\n';
  } else {
    user += "\nDo NOT reuse the learner's numbers. Every problem needs new numbers.\n";
  }
  if (g.student_answer && !g.student_correct) user += `\nThe learner's wrong answer: ${g.student_answer}\n`;
  if (g.replay) user += `How that mistake happened: ${clip(g.replay, 300)}\n`;
  if (gr.factsBlock(g)) user += `\n${gr.factsBlock(g)}\n`;
  if (req.mistakes.length) {
    user +=
      '\nIn the last practice round the learner still got these wrong (target this same mistake):\n' +
      req.mistakes.slice(0, 6).map((m) => `- ${clip(m, 200)}`).join('\n') + '\n';
  }
  if (req.avoid.length) {
    user += '\nDo not repeat these problems:\n' + req.avoid.slice(-20).map((a) => `- ${clip(a, 120)}`).join('\n') + '\n';
  }
  const res = await ask(system, user, Math.min(TOKENS.practice, 200 * req.count + 120), req.temperature);
  const items: PracticeItem[] = [];
  for (const raw of parsing.parsePractice(res.text)) {
    const base = { id: '', correct_answer: null, code: null, correct_code: null, expected_output: null, verified: false, verification: 'unchecked' };
    if (code) {
      if (!(raw.code && raw.correct_code)) continue;
      items.push({ ...base, type: 'code', prompt: raw.question || 'Fix this code.', code: raw.code, correct_code: raw.correct_code, explanation: raw.why || '' });
    } else {
      if (!(raw.question && raw.answer)) continue;
      items.push({ ...base, type: 'math', prompt: raw.question, correct_answer: raw.answer.trim(), explanation: raw.why || '' });
    }
  }
  return items;
}

// ------------------------------------------------------------------------------ agent 4
export function checkSolution(g: gr.Grounding, s: Solution): Check[] {
  const checks: Check[] = [];
  if (s.kind === 'math') {
    if (g.verified_answer === null) {
      checks.push({ name: 'answer_matches_exact_value', status: 'skip', detail: 'This kind of problem cannot be computed exactly by the tools, so the answer is not machine-verified.' });
    } else if (!s.final_answer) {
      checks.push({ name: 'answer_matches_exact_value', status: 'fail', detail: "The solver did not give a clearly marked 'Final answer'." });
    } else {
      const expected = gr.parseNumber(g.verified_answer);
      const got = gr.parseNumber(s.final_answer);
      if (expected && got && expected.equals(got)) {
        checks.push({ name: 'answer_matches_exact_value', status: 'pass', detail: `Final answer ${s.final_answer} equals the exact value ${g.verified_answer}.` });
      } else {
        checks.push({ name: 'answer_matches_exact_value', status: 'fail', detail: `Solver answered '${s.final_answer}' but the exact value is ${g.verified_answer}.` });
      }
    }
  } else if (!s.code) {
    checks.push({ name: 'code_runs', status: 'fail', detail: 'The solver did not provide a Python code block.' });
  } else {
    checks.push({ name: 'code_runs', status: 'skip', detail: 'No Python sandbox on this host, so the corrected code was not executed.' });
  }
  return checks;
}

export function checkExplanation(g: gr.Grounding, e: Explanation): Check[] {
  const checks: Check[] = [];
  const required = ['what_went_wrong', 'why_mistake', 'correct_thinking'];
  const missing = required.filter((k) => !(k in e.sections));
  if (missing.length) {
    checks.push({ name: 'explanation_structure', status: 'warn', detail: 'Explanation is missing sections: ' + missing.map((m) => m.replace(/_/g, ' ')).join(', ') + '.' });
  } else {
    checks.push({ name: 'explanation_structure', status: 'pass', detail: 'Explanation covers what went wrong, why the mistake happens and the correct idea.' });
  }
  if (g.verified_answer && g.kind !== 'python') {
    const expected = gr.parseNumber(g.verified_answer);
    if (expected && !gr.numbersIn(e.text).some((n) => n.equals(expected))) {
      checks.push({ name: 'explanation_mentions_exact_value', status: 'warn', detail: `Explanation never states the exact value ${g.verified_answer}.` });
    }
  }
  return checks;
}

/** 'ok' | 'wrong' | 'unknown'; sets verified/verification on the item. */
export function verifyItem(item: PracticeItem): 'ok' | 'wrong' | 'unknown' {
  if (item.type === 'math') {
    const probe = gr.ground(item.prompt, 'Mathematics');
    if (probe.verified_answer === null || probe.kind === 'python') {
      item.verification = 'not machine-checkable';
      return 'unknown';
    }
    const stated = gr.parseNumber(item.correct_answer || '');
    const exact = gr.parseNumber(probe.verified_answer);
    if (!stated || !exact || !stated.equals(exact)) return 'wrong';
    item.verified = true;
    item.verification = 'answer computed exactly';
    return 'ok';
  }
  // Code: no sandbox. Still reject exercises whose 'buggy' code is identical to the fix.
  if (practiceKey('code', '', item.code) === practiceKey('code', '', item.correct_code)) return 'wrong';
  item.verification = 'no sandbox';
  return 'unknown';
}

export function buildReview(checks: Check[], revisions: number, seconds: number): Review {
  const failed = checks.filter((c) => c.status === 'fail');
  const passed = checks.filter((c) => c.status === 'pass');
  return {
    approved: !failed.length,
    verified: passed.length > 0 && !failed.length,
    checks,
    issues: failed.map((c) => c.detail),
    model_verdict: null,
    model_notes: '',
    revisions,
    seconds,
  };
}

export function composeMarkdown(explanation: Explanation, solution: Solution, review: Review): string {
  const parts = [
    '## Why this went wrong',
    explanation.text,
    '## The correct ' + (solution.kind === 'code' ? 'code' : 'answer'),
    solution.text,
  ];
  const status = review.approved && review.verified
    ? 'all checks passed'
    : review.approved
      ? 'approved, but some parts could not be machine-verified'
      : 'NOT fully verified - see issues';
  parts.push(`## Review (${status})`);
  for (const c of review.checks) parts.push(`- [${c.status}] ${c.detail}`);
  return parts.join('\n\n');
}

// ---------------------------------------------------------------- grading code answers

function normLines(code: string): string[] {
  return (code || '')
    .split(/\r?\n/)
    .map((l) => l.replace(/#.*$/, '').replace(/\s+/g, ''))
    .filter(Boolean);
}

/**
 * Without a Python sandbox, a code answer counts as correct when it contains every line the
 * reference fix added and none of the lines the fix removed (spacing and comments ignored).
 */
export function gradeCodeAnswer(answer: string, buggy: string | null, fixed: string | null): boolean {
  if (!fixed) return false;
  const student = normLines(answer);
  const ref = normLines(fixed);
  if (student.join('\n') === ref.join('\n')) return true;
  const bug = normLines(buggy || '');
  const added = ref.filter((l) => !bug.includes(l));
  const removed = bug.filter((l) => !ref.includes(l));
  if (!added.length && !removed.length) return false;
  return added.every((l) => student.includes(l)) && removed.every((l) => !student.includes(l));
}
