// Misconception Tutor - AppDeploy backend.
//
// The Flask app streamed all four agents from one request. AppDeploy runs this backend as a
// function that returns one complete response, so each agent is its own request and the
// browser drives the steps in order:
//   start -> explain -> solve -> practice/start + practice/generate (one model call each) -> review
// Practice rounds and runs are kept in the AppDeploy database so grading never trusts the browser.

import { router, json, error, db, increment } from '@appdeploy/sdk';
import * as gr from './grounding';
import * as agents from './agents';
import { health, ModelUnavailable, MODEL_NAME } from './model';
import { sanitizeText, sanitizeMathAnswer, scanPrompt } from './security';

const AGENT_ORDER = ['explainer', 'solver', 'practice', 'reviewer'];
const PRACTICE_COUNT = 3; // fast-mode default of the Python app
const MASTERY_THRESHOLD = 0.8;

type Body = Record<string, unknown>;

interface Run {
  question: string;
  subject: string;
  learner_id: string;
  mode: string;
  grounding: gr.Grounding;
  explanation?: agents.Explanation;
  solution?: agents.Solution;
  solution_checks?: agents.Check[];
  set_id?: string;
  created: number;
}

interface Round {
  set_id: string;
  run_id: string;
  question: string;
  subject: string;
  misconception: string;
  round: number;
  level: string;
  count: number;
  items: agents.PracticeItem[];
  ids: string[];
  results: Record<string, boolean>;
  answers: Record<string, string>;
  history: string[];
  mistakes: string[];
  attempts: number;
  rejected: number;
  dropped: number;
  done: boolean;
  previous?: RoundStatus;
  created: number;
}

interface RoundStatus {
  set_id: string;
  round: number;
  level: string;
  total: number;
  answered: number;
  correct: number;
  accuracy: number;
  threshold: number;
  complete: boolean;
  mastered: boolean;
  next_level: string | null;
}

// ------------------------------------------------------------------------------ helpers

function newId(prefix: string): string {
  const c = (globalThis as { crypto?: { randomUUID?: () => string } }).crypto;
  const raw = c && c.randomUUID ? c.randomUUID().replace(/-/g, '') : Math.random().toString(16).slice(2) + Date.now().toString(16);
  return `${prefix}_${raw.slice(0, 12)}`;
}

function bodyOf(ctx: { body: unknown }): Body {
  const b = ctx.body;
  if (typeof b === 'string') {
    try {
      return JSON.parse(b) as Body;
    } catch {
      return {};
    }
  }
  return b && typeof b === 'object' ? (b as Body) : {};
}

function safeId(value: unknown): string {
  const s = typeof value === 'string' ? value.trim() : '';
  return /^[A-Za-z0-9_-]{1,64}$/.test(s) ? s : '';
}

async function getOne<T>(table: string, id: string): Promise<T | null> {
  if (!id) return null;
  const [rec] = await db.get<T>(table, [id], { consistent: true });
  return rec || null;
}

async function putNew(table: string, id: string, record: Record<string, unknown>): Promise<void> {
  const [created] = await db.tx.add(table, [{ ...record, id }]);
  if (!created) throw new Error(`could not create ${table} record`);
}

async function save(table: string, id: string, record: Record<string, unknown>): Promise<void> {
  const [ok] = await db.update(table, [{ id, record: { ...record, id } }]);
  if (!ok) throw new Error(`could not save ${table} record`);
}

function unavailable(e: unknown) {
  if (e instanceof ModelUnavailable) {
    console.warn('model unavailable:', e.message);
    return json({ status: 'model_unavailable', error: e.publicMessage, message: e.publicMessage }, 503);
  }
  console.error('unexpected error', e instanceof Error ? e.stack || e.message : String(e));
  return error('The tutor hit an unexpected error.', 500);
}

// ---------------------------------------------------------------------- practice rounds

function nextLevel(current: string, accuracy: number): string {
  const ladder = ['easier', 'same', 'harder'];
  const base = current === 'start' ? 'same' : current;
  let idx = ladder.indexOf(base);
  if (idx < 0) idx = 1;
  if (accuracy < 0.5) idx = Math.max(0, idx - 1);
  return ladder[idx];
}

function roundStatus(r: Round): RoundStatus {
  const total = r.ids.length;
  const answered = r.ids.filter((i) => i in r.results).length;
  const correct = r.ids.filter((i) => r.results[i]).length;
  const complete = total > 0 && answered >= total;
  const accuracy = total ? correct / total : 0;
  const mastered = complete && accuracy >= MASTERY_THRESHOLD;
  return {
    set_id: r.set_id,
    round: r.round,
    level: r.level,
    total,
    answered,
    correct,
    accuracy: Math.round(accuracy * 1000) / 1000,
    threshold: MASTERY_THRESHOLD,
    complete,
    mastered,
    next_level: mastered || !complete ? null : nextLevel(r.level, accuracy),
  };
}

function practiceSet(r: Round, isCode: boolean) {
  const subject = isCode ? 'Python' : 'Mathematics';
  const target = r.misconception || 'general';
  const questions = r.items.map((item) => ({
    ...item,
    subject,
    target_misconception: target,
    generated_by: 'fine-tuned model',
    set_id: r.set_id,
  }));
  return {
    subject,
    misconception: target,
    count: questions.length,
    questions,
    set_id: r.set_id,
    round: r.round,
    level: r.level,
    mastery_threshold: MASTERY_THRESHOLD,
    previous: r.previous,
    done: r.done,
  };
}

function newRound(fields: Partial<Round> & Pick<Round, 'run_id' | 'question' | 'subject' | 'misconception'>): Round {
  return {
    set_id: newId('pr'),
    round: 1,
    level: 'start',
    count: PRACTICE_COUNT,
    items: [],
    ids: [],
    results: {},
    answers: {},
    history: [],
    mistakes: [],
    attempts: 0,
    rejected: 0,
    dropped: 0,
    done: false,
    created: Date.now(),
    ...fields,
  };
}

/** One model call: add new, verified, non-duplicate items to the round. */
async function generateStep(r: Round): Promise<void> {
  const g = gr.ground(r.question, r.subject);
  const isCode = gr.isCode(g);
  const cap = 2 * r.count + 2;
  if (r.items.length < r.count && r.attempts < cap) {
    r.attempts += 1;
    const seen = [...r.history, ...r.items.map((i) => i.prompt)];
    const type = isCode ? 'code' : 'math';
    const seenKeys = [
      ...r.history.map((p) => agents.practiceKey(type, p)),
      ...r.items.map((i) => agents.practiceKey(i.type, i.prompt, i.code)),
    ];
    const ownKey = agents.practiceKey(type, (!isCode ? g.expression : null) || r.question);
    const want = Math.min(isCode ? 1 : 3, r.count - r.items.length);
    const batch = await agents.practiceBatch({
      question: r.question,
      grounding: g,
      misconception: r.misconception,
      count: want,
      avoid: seen,
      level: r.level,
      mistakes: r.mistakes,
      temperature: Math.min(1, 0.5 + 0.15 * r.rejected),
    });
    for (const item of batch) {
      const key = agents.practiceKey(item.type, item.prompt, item.code);
      if (seenKeys.some((k) => agents.similar(key, k)) || agents.similar(key, ownKey)) {
        r.rejected += 1;
        continue;
      }
      if (agents.verifyItem(item) === 'wrong') {
        r.dropped += 1;
        continue;
      }
      seenKeys.push(key);
      r.items.push(item);
      if (r.items.length >= r.count) break;
    }
  }
  if (r.items.length >= r.count || r.attempts >= cap) {
    r.items = r.items.slice(0, r.count);
    r.items.forEach((item, i) => {
      item.id = `${r.set_id}_${i + 1}`;
    });
    r.ids = r.items.map((i) => i.id);
    r.history = [...r.history, ...r.items.map((i) => i.prompt)];
    r.done = true;
  }
}

function practiceCheck(r: Round | null): agents.Check {
  const items = r ? r.items : [];
  if (!items.length) return { name: 'practice_items_verified', status: 'warn', detail: 'No usable practice problems were produced.' };
  const verified = items.filter((i) => i.verified).length;
  let detail = `${verified}/${items.length} practice problems machine-verified`;
  if (r && r.dropped) detail += `; ${r.dropped} dropped because their stated answer was wrong`;
  return { name: 'practice_items_verified', status: verified ? 'pass' : 'warn', detail: detail + '.' };
}

async function logSample(record: Record<string, unknown>): Promise<string> {
  const id = newId('samp');
  await putNew('samples', id, { ...record, timestamp: new Date().toISOString(), feedback: record.feedback || 'unrated' });
  try {
    await db.tx.add('counters', [{ id: 'samples', value: 0 }]);
    await db.tx.update('counters', [{ id: 'samples', record: { value: increment(1) } }], { patch: true });
  } catch (e) {
    console.warn('sample counter not updated', e instanceof Error ? e.message : '');
  }
  return id;
}

async function sampleCount(): Promise<number> {
  try {
    const rec = await getOne<{ value?: number }>('counters', 'samples');
    return rec && typeof rec.value === 'number' ? rec.value : 0;
  } catch {
    return 0;
  }
}

// ------------------------------------------------------------------------------- routes

export const handler = router({
  'GET /api/health': [async () => json({ status: 'online' })],

  'GET /api/backend-status': [
    async () => {
      const [h, samples] = await Promise.all([health(), sampleCount()]);
      return json({
        status: 'online',
        liveAiEnabled: h.reachable,
        model: h.model || MODEL_NAME,
        llmLoaded: h.reachable,
        llmError: h.error || null,
        mode: h.reachable ? 'Fine-tuned Gemma - 4-agent pipeline (remote)' : 'Model offline',
        remoteBackend: h.configured ? { reachable: h.reachable } : null,
        agents: { configured: h.configured, reachable: h.reachable, mode: h.mode, model: h.model || MODEL_NAME, error: h.error || null, agents: AGENT_ORDER },
        modelOnly: true,
        trainingMode: 'offline_kaggle',
        trainingSamplesCollected: samples,
      });
    },
  ],

  // 0. Validate, guard and ground the question; opens a run.
  'POST /api/tutor/start': [
    async (ctx) => {
      const body = bodyOf(ctx);
      const raw = typeof body.question === 'string' ? body.question.trim() : '';
      if (!raw) return error('Enter a question before sending it.', 400);
      const question = sanitizeText(raw);
      const scan = scanPrompt(question);
      if (!scan.safe) {
        return json({
          error: 'I am a dedicated Socratic Math Tutor designed to guide you through mathematical problem solving. I cannot process instruction override requests, system prompt inspections, or roleplay escapes. Let\'s focus on solving fractions and algebra!',
          model: 'ECC-Security-Guard (OWASP-Blocked)',
          status: 'refused_injection',
          risk_level: 'HIGH',
          flagged_pattern: scan.pattern,
        }, 400);
      }
      const subject = sanitizeText(typeof body.subject === 'string' ? body.subject : 'Mathematics', 64) || 'Mathematics';
      const learnerId = sanitizeText(typeof body.learner_id === 'string' ? body.learner_id : '', 64) || 'student_demo';
      const mode = sanitizeText(typeof body.mode === 'string' ? body.mode : 'diagnostic', 64) || 'diagnostic';
      const grounding = gr.ground(question, subject);
      const runId = newId('run');
      const run: Run = { question, subject, learner_id: learnerId, mode, grounding, created: Date.now() };
      await putNew('runs', runId, run as unknown as Record<string, unknown>);
      return json({ run_id: runId, agents: AGENT_ORDER, grounding });
    },
  ],

  // 1. Explanation agent.
  'POST /api/tutor/explain': [
    async (ctx) => {
      const runId = safeId(bodyOf(ctx).run_id);
      const run = await getOne<Run>('runs', runId);
      if (!run) return error('This question has expired. Ask it again.', 404);
      try {
        run.explanation = await agents.explain(run.question, run.grounding);
      } catch (e) {
        return unavailable(e);
      }
      await save('runs', runId, run as unknown as Record<string, unknown>);
      return json({ explanation: run.explanation });
    },
  ],

  // 2. Solution agent.
  'POST /api/tutor/solve': [
    async (ctx) => {
      const runId = safeId(bodyOf(ctx).run_id);
      const run = await getOne<Run>('runs', runId);
      if (!run) return error('This question has expired. Ask it again.', 404);
      try {
        run.solution = await agents.solve(run.question, run.grounding);
      } catch (e) {
        return unavailable(e);
      }
      run.solution_checks = agents.checkSolution(run.grounding, run.solution);
      await save('runs', runId, run as unknown as Record<string, unknown>);
      return json({ solution: run.solution });
    },
  ],

  // 3a. Opens practice round 1 for a run.
  'POST /api/tutor/practice': [
    async (ctx) => {
      const runId = safeId(bodyOf(ctx).run_id);
      const run = await getOne<Run>('runs', runId);
      if (!run) return error('This question has expired. Ask it again.', 404);
      const label = (run.explanation && run.explanation.misconception) || run.grounding.misconception_id || '';
      const r = newRound({ run_id: runId, question: run.question, subject: run.subject, misconception: label });
      await putNew('rounds', r.set_id, r as unknown as Record<string, unknown>);
      run.set_id = r.set_id;
      await save('runs', runId, run as unknown as Record<string, unknown>);
      return json(practiceSet(r, gr.isCode(run.grounding)));
    },
  ],

  // 3b. One model call towards the round's problems; call until done is true.
  'POST /api/practice/generate': [
    async (ctx) => {
      const setId = safeId(bodyOf(ctx).set_id);
      const r = await getOne<Round>('rounds', setId);
      if (!r) return error('This practice round has expired. Ask your question again.', 404);
      if (!r.done) {
        try {
          await generateStep(r);
        } catch (e) {
          if (!(e instanceof ModelUnavailable) || !r.items.length) return unavailable(e);
          console.warn('practice batch failed; keeping', r.items.length, 'items');
          r.attempts = 2 * r.count + 2;
          await generateStep(r); // closes the round with what it has (no model call)
        }
        await save('rounds', setId, r as unknown as Record<string, unknown>);
      }
      const g = gr.ground(r.question, r.subject);
      return json(practiceSet(r, gr.isCode(g)));
    },
  ],

  // 4. Review agent: exact checks (the fast-mode default skips the advisory model critique).
  'POST /api/tutor/review': [
    async (ctx) => {
      const runId = safeId(bodyOf(ctx).run_id);
      const run = await getOne<Run>('runs', runId);
      if (!run || !run.explanation || !run.solution) return error('Run the explanation and solution steps first.', 409);
      const started = Date.now();
      const round = run.set_id ? await getOne<Round>('rounds', run.set_id) : null;
      const checks = [
        ...(run.solution_checks || agents.checkSolution(run.grounding, run.solution)),
        ...agents.checkExplanation(run.grounding, run.explanation),
        practiceCheck(round),
      ];
      const review = agents.buildReview(checks, 0, Math.round((Date.now() - started) / 10) / 100);
      const misconception = run.explanation.misconception || run.grounding.misconception_id || 'general';
      const answer = agents.composeMarkdown(run.explanation, run.solution, review);
      let sampleId = '';
      if (review.approved) {
        try {
          sampleId = await logSample({
            learner_id: run.learner_id,
            subject: run.subject,
            instruction: "Explain the learner's mistake and give the verified correct solution.",
            input: run.question,
            output: answer,
            misconception,
            feedback: review.verified ? 'auto_verified' : 'unrated',
            metadata: { source: 'agent_pipeline', mode: run.mode, verified: review.verified },
          });
        } catch (e) {
          console.warn('training sample not logged', e instanceof Error ? e.message : '');
        }
      }
      return json({
        review,
        result: {
          status: 'success',
          question: run.question,
          subject: run.subject,
          misconception,
          model: `${MODEL_NAME}`,
          answer,
          sample_id: sampleId,
        },
      });
    },
  ],

  'POST /api/practice/submit': [
    async (ctx) => {
      const body = bodyOf(ctx);
      const practiceId = sanitizeText(typeof body.practice_id === 'string' ? body.practice_id : '', 128);
      const answer = typeof body.answer === 'string' ? body.answer.trim().slice(0, 4000) : '';
      if (!practiceId || !answer) return error('Practice ID and answer are required.', 400);
      const setId = safeId(practiceId.slice(0, practiceId.lastIndexOf('_')));
      const r = await getOne<Round>('rounds', setId);
      const item = r ? r.items.find((i) => i.id === practiceId) : undefined;
      if (!r || !item) return error('This practice problem has expired. Ask your question again.', 404);

      let correct: boolean;
      let details: Record<string, unknown>;
      if (item.type === 'code') {
        correct = agents.gradeCodeAnswer(answer, item.code, item.correct_code);
        details = {
          correct_code: item.correct_code,
          explanation: item.explanation || '',
          grading: 'compared with the reference fix (code is not executed on this host)',
        };
      } else {
        const correctAnswer = sanitizeMathAnswer(item.correct_answer || '');
        const [ok, parsed] = gr.checkAnswer(sanitizeMathAnswer(answer), correctAnswer);
        correct = ok;
        details = {
          student_parsed: parsed ? parsed.toString() : answer,
          correct_answer: correctAnswer,
          explanation: item.explanation ||
            'Find a common denominator, scale each numerator by the same factor, then add the numerators and reduce the fraction.',
        };
      }
      if (!(practiceId in r.results)) {
        r.results[practiceId] = correct; // first attempt counts
        r.answers[practiceId] = answer.slice(0, 400);
        await save('rounds', setId, r as unknown as Record<string, unknown>);
      }
      return json({
        correct,
        practice_id: practiceId,
        misconception: r.misconception,
        round: roundStatus(r),
        ...details,
      });
    },
  ],

  // A new round of different problems after a round scored below 80%; then call /api/practice/generate.
  'POST /api/practice/next': [
    async (ctx) => {
      const setId = safeId(bodyOf(ctx).set_id);
      if (!setId) return error('set_id is required.', 400);
      const prev = await getOne<Round>('rounds', setId);
      if (!prev) return error('This practice round has expired. Ask your question again.', 404);
      const status = roundStatus(prev);
      if (!status.complete) return error('Answer every problem in this round first.', 409);
      if (status.mastered) return error('This round is already mastered; no more practice is needed.', 409);
      const mistakes = prev.items
        .filter((i) => !prev.results[i.id])
        .map((i) => `${i.prompt} -> learner answered: ${(prev.answers[i.id] || '').slice(0, 120)}`);
      const r = newRound({
        run_id: prev.run_id,
        question: prev.question,
        subject: prev.subject,
        misconception: prev.misconception,
        round: prev.round + 1,
        level: status.next_level || 'same',
        count: prev.ids.length || PRACTICE_COUNT,
        history: prev.history,
        mistakes,
        previous: status,
      });
      await putNew('rounds', r.set_id, r as unknown as Record<string, unknown>);
      const g = gr.ground(r.question, r.subject);
      return json(practiceSet(r, gr.isCode(g)));
    },
  ],

  'POST /api/llm/feedback': [
    async (ctx) => {
      const body = bodyOf(ctx);
      const sampleId = safeId(body.sample_id);
      const feedback = body.feedback === 'unhelpful' ? 'unhelpful' : 'helpful';
      if (!sampleId) return error('Sample ID is required.', 400);
      const [ok] = await db.tx.update('samples', [{ id: sampleId, record: { feedback } }], { patch: true });
      return json({ success: Boolean(ok), sample_id: sampleId });
    },
  ],
});
