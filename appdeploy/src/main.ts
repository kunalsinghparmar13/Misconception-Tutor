/* Misconception Tutor - frontend controller (port of 'UI and UX/app.js').
 *
 * A question runs through four agents, all powered by the fine-tuned model:
 *   1 Explain  ->  2 Solve  ->  3 Practice  ->  4 Review
 * Each agent is its own backend request, so every result is rendered as soon as it arrives.
 * Everything coming from the server is inserted with textContent / DOM nodes (never innerHTML).
 */
import './styles.css';
import { api } from '@appdeploy/client';

type Json = Record<string, any>;

declare global {
  interface Window {
    setSubject: (subject: string) => void;
    stagePrompt: (text: string) => void;
    clearStagedPrompt: () => void;
  }
}

// ---------------------------------------------------------------- landing-page helpers
window.setSubject = (subject: string): void => {
  const mathCard = document.getElementById('tab-math');
  const pythonCard = document.getElementById('tab-python');
  const mathBadge = document.getElementById('badge-math');
  const pythonBadge = document.getElementById('badge-python');
  const pythonHint = document.getElementById('hint-python');
  const area = document.querySelector('textarea');
  if (!mathCard || !pythonCard || !mathBadge || !pythonBadge) return;
  const math = subject === 'math';
  mathCard.classList.toggle('ring-2', math);
  mathCard.classList.toggle('ring-primary', math);
  pythonCard.classList.toggle('ring-2', !math);
  pythonCard.classList.toggle('ring-primary', !math);
  mathBadge.classList.toggle('hidden', !math);
  mathBadge.classList.toggle('inline-flex', math);
  pythonBadge.classList.toggle('hidden', math);
  pythonBadge.classList.toggle('inline-flex', !math);
  if (pythonHint) pythonHint.classList.toggle('hidden', !math);
  if (area && area.value.trim() === '') {
    area.placeholder = math
      ? 'Enter your Mathematics theorem, derivation, or formula step...'
      : 'Paste your Python script, traceback, or algorithm issue...';
  }
};

window.stagePrompt = (text: string): void => {
  const area = document.querySelector('textarea');
  const banner = document.getElementById('staging-banner');
  if (area) {
    area.value = text;
    area.style.height = 'auto';
    area.style.height = `${area.scrollHeight}px`;
    area.dispatchEvent(new Event('input'));
    area.focus();
  }
  if (banner) banner.classList.remove('hidden');
};

window.clearStagedPrompt = (): void => {
  const banner = document.getElementById('staging-banner');
  if (banner) banner.classList.add('hidden');
};

// ---------------------------------------------------------------- API helpers
class ApiError extends Error {
  status: number;
  payload: Json;

  constructor(message: string, status: number, payload: Json) {
    super(message);
    this.status = status;
    this.payload = payload;
  }
}

async function post(url: string, body: Json): Promise<Json> {
  try {
    const res = await api.post(url, body);
    return (res && res.data) || {};
  } catch (err: any) {
    const payload: Json = (err && err.response && err.response.data) || (err && err.data) || {};
    const status: number = (err && err.response && err.response.status) || (err && err.status) || 0;
    const message = payload.error || payload.message || (err && err.message) || 'Request failed';
    throw new ApiError(String(message), status, payload);
  }
}

function isOffline(err: unknown): boolean {
  return err instanceof ApiError && (err.status === 503 || err.payload.status === 'model_unavailable');
}

// ---------------------------------------------------------------- app
(function main() {
  const MAX_CHARS = 4000;
  const textarea = document.querySelector('textarea');
  const sendButton = document.querySelector<HTMLButtonElement>('button[aria-label="Send"]');
  const counter = document.getElementById('char-counter');
  const modelStatus = document.getElementById('model-status');
  if (!textarea || !sendButton) return;
  const area: HTMLTextAreaElement = textarea;
  const send: HTMLButtonElement = sendButton;

  let activeSubject = 'Python'; // matches the card highlighted on load
  let busy = false;
  let generation = 0; // bumped by New Chat so an old run stops rendering
  const history: Array<{ question: string; subject: string }> = [];

  function learnerId(): string {
    try {
      let id = localStorage.getItem('learner_id');
      if (!id) {
        id = 'learner_' + Math.random().toString(36).slice(2, 10);
        localStorage.setItem('learner_id', id);
      }
      return id;
    } catch {
      return 'student_demo';
    }
  }

  // ---------------------------------------------------------------- tiny DOM helpers
  function el<K extends keyof HTMLElementTagNameMap>(tag: K, className?: string, text?: string | null): HTMLElementTagNameMap[K] {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  function inline(text: string): DocumentFragment {
    const frag = document.createDocumentFragment();
    String(text).split(/(`[^`\n]+`|\*\*[^*\n]+\*\*)/g).forEach((part) => {
      if (!part) return;
      if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
        frag.appendChild(el('code', 'px-1 py-0.5 rounded bg-surface-container font-code-inline text-code-inline', part.slice(1, -1)));
      } else if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
        frag.appendChild(el('strong', 'font-semibold', part.slice(2, -2)));
      } else {
        frag.appendChild(document.createTextNode(part));
      }
    });
    return frag;
  }

  function codeBlock(code: string): HTMLElement {
    const pre = el('pre', 'whitespace-pre-wrap overflow-x-auto rounded-lg bg-surface-container-low p-3 font-code-block text-code-block text-on-surface my-2');
    pre.appendChild(el('code', '', code));
    return pre;
  }

  function markdown(text: string): HTMLElement {
    const root = el('div', 'space-y-2 font-body-md text-body-md text-on-surface');
    const chunks = String(text || '').split(/```[^\n]*\n([\s\S]*?)(?:```|$)/g);
    chunks.forEach((chunk, index) => {
      if (index % 2 === 1) {
        root.appendChild(codeBlock(chunk.replace(/\n$/, '')));
        return;
      }
      let list: HTMLElement | null = null;
      chunk.split('\n').forEach((line) => {
        const heading = line.match(/^\s*#{1,4}\s+(.*)$/);
        const bullet = line.match(/^\s*(?:[-*]|\d+[.)])\s+(.*)$/);
        if (heading) {
          list = null;
          const h = el('h4', 'font-headline-sm text-headline-sm text-on-surface mt-3');
          h.appendChild(inline(heading[1]));
          root.appendChild(h);
        } else if (bullet) {
          if (!list) {
            list = el('ul', 'list-disc pl-5 space-y-1');
            root.appendChild(list);
          }
          const li = el('li');
          li.appendChild(inline(bullet[1]));
          list.appendChild(li);
        } else if (line.trim()) {
          list = null;
          const p = el('p');
          p.appendChild(inline(line.trim()));
          root.appendChild(p);
        } else {
          list = null;
        }
      });
    });
    return root;
  }

  // ---------------------------------------------------------------- results container
  const results = el('section', 'hidden w-full max-w-3xl mx-auto mb-6 space-y-4');
  results.id = 'llm-response';
  const mainWrap = document.querySelector('main > div');
  if (mainWrap) mainWrap.prepend(results);

  const AGENTS = [
    { key: 'explainer', number: 1, title: 'Why it went wrong', hint: 'Explanation agent' },
    { key: 'solver', number: 2, title: 'The correct answer', hint: 'Solution agent' },
    { key: 'practice', number: 3, title: 'Practice for you', hint: 'Practice agent' },
    { key: 'reviewer', number: 4, title: 'Review', hint: 'Review agent' },
  ];
  type Panel = { card: HTMLElement; chip: HTMLElement; body: HTMLElement };
  let panels: Record<string, Panel> = {};

  function buildPanels(): void {
    results.replaceChildren();
    panels = {};
    const banner = el('div', 'hidden rounded-2xl p-4 bg-error-container text-on-error-container font-body-sm text-body-sm');
    banner.id = 'result-banner';
    results.appendChild(banner);
    AGENTS.forEach((agent) => {
      const card = el('div', 'rounded-2xl bg-surface-container-lowest p-5 shadow-sm ring-1 ring-outline-variant/30');
      card.setAttribute('data-agent', agent.key);
      const head = el('div', 'flex items-center justify-between mb-3');
      const left = el('div', 'flex items-center gap-2');
      left.appendChild(el('span', 'w-6 h-6 rounded-full bg-primary text-on-primary flex items-center justify-center font-label-sm text-label-sm', String(agent.number)));
      left.appendChild(el('span', 'font-headline-sm text-headline-sm text-on-surface', agent.title));
      const chip = el('span', 'font-label-sm text-label-sm px-2 py-0.5 rounded-full bg-surface-container text-on-surface-variant', 'Waiting');
      head.appendChild(left);
      head.appendChild(chip);
      const body = el('div', 'text-on-surface-variant font-body-sm text-body-sm', agent.hint + ' will appear here.');
      card.appendChild(head);
      card.appendChild(body);
      results.appendChild(card);
      panels[agent.key] = { card, chip, body };
    });
    results.classList.remove('hidden');
  }

  function setChip(key: string, label: string, tone: string): void {
    const chip = panels[key] && panels[key].chip;
    if (!chip) return;
    chip.textContent = label;
    const tones: Record<string, string> = {
      work: 'bg-secondary-fixed text-on-secondary-fixed animate-pulse',
      done: 'bg-tertiary-fixed text-on-tertiary-fixed',
      warn: 'bg-error-container text-on-error-container',
      idle: 'bg-surface-container text-on-surface-variant',
    };
    chip.className = 'font-label-sm text-label-sm px-2 py-0.5 rounded-full ' + (tones[tone] || tones.idle);
  }

  function startAgent(key: string, message = 'The model is writing this part...'): void {
    setChip(key, 'Working...', 'work');
    if (panels[key]) panels[key].body.textContent = message;
  }

  function showBanner(message: string, kind?: string): void {
    const banner = document.getElementById('result-banner');
    if (!banner) return;
    banner.className = 'rounded-2xl p-4 font-body-sm text-body-sm ' +
      (kind === 'info' ? 'bg-secondary-fixed text-on-secondary-fixed' : 'bg-error-container text-on-error-container');
    banner.textContent = message;
  }

  // ---------------------------------------------------------------- agent renderers
  function labelled(label: string, text: string): HTMLElement {
    const wrap = el('div', 'mb-3');
    wrap.appendChild(el('div', 'font-label-sm text-label-sm uppercase tracking-wider text-outline mb-1', label));
    wrap.appendChild(markdown(text));
    return wrap;
  }

  function renderExplanation(data: Json): void {
    const body = panels.explainer.body;
    body.replaceChildren();
    body.className = '';
    const s: Json = data.sections || {};
    const order: Array<[string, string]> = [
      ['misconception', 'The idea that tripped you up'],
      ['what_went_wrong', 'What went wrong'],
      ['why_mistake', 'Why this mistake happens'],
      ['correct_thinking', 'How to think about it'],
      ['check_yourself', 'Check yourself'],
    ];
    const present = order.filter(([key]) => s[key]);
    if (present.length < 2) body.appendChild(markdown(data.text));
    else present.forEach(([key, label]) => body.appendChild(labelled(label, s[key])));
    setChip('explainer', 'Done', 'done');
  }

  function renderSolution(data: Json): void {
    const body = panels.solver.body;
    body.replaceChildren();
    body.className = '';
    if (data.kind === 'code') {
      if (data.code) body.appendChild(codeBlock(data.code));
      if (data.what_changed) body.appendChild(labelled('What changed', data.what_changed));
      if (!data.code) body.appendChild(markdown(data.text));
    } else {
      if (data.final_answer) {
        const box = el('div', 'rounded-xl bg-primary text-on-primary px-4 py-3 mb-3');
        box.appendChild(el('div', 'font-label-sm text-label-sm uppercase tracking-wider opacity-70', 'Final answer'));
        box.appendChild(el('div', 'font-headline-md text-headline-md', data.final_answer));
        body.appendChild(box);
      }
      body.appendChild(markdown(data.steps || data.text));
    }
    setChip('solver', 'Done', 'done');
  }

  function renderReview(review: Json): void {
    const body = panels.reviewer.body;
    body.replaceChildren();
    body.className = '';
    const verdict = review.approved
      ? (review.verified ? 'Checked - the answer matches exact computation.' : 'Approved, but some parts could not be machine-verified.')
      : 'Not fully verified - treat the answer with caution.';
    body.appendChild(el('p', 'font-body-md text-body-md text-on-surface mb-3 font-medium', verdict));
    const icons: Record<string, string> = { pass: '✓', fail: '✕', warn: '!', skip: '–' };
    const colors: Record<string, string> = { pass: 'text-on-tertiary-container', fail: 'text-error', warn: 'text-error', skip: 'text-outline' };
    const list = el('ul', 'space-y-1.5');
    (review.checks || []).forEach((check: Json) => {
      const li = el('li', 'flex gap-2 font-body-sm text-body-sm text-on-surface-variant');
      li.appendChild(el('span', 'font-semibold w-4 shrink-0 ' + (colors[check.status] || ''), icons[check.status] || '•'));
      li.appendChild(el('span', '', check.detail));
      list.appendChild(li);
    });
    body.appendChild(list);
    setChip('reviewer', review.approved ? 'Done' : 'Needs care', review.approved ? 'done' : 'warn');
  }

  // ---- practice ------------------------------------------------------------------------
  const LEVEL_LABEL: Record<string, string> = { start: 'Starting level', easier: 'Easier', same: 'Same level, new problems', harder: 'Harder' };

  /** Calls /api/practice/generate (one model call each) until the round is complete. */
  async function fillRound(set: Json, gen: number, onProgress: (n: number, total: number) => void): Promise<Json> {
    let current = set;
    for (let i = 0; i < 12 && !current.done; i++) {
      if (gen !== generation) throw new Error('cancelled');
      current = await post('/api/practice/generate', { set_id: current.set_id });
      onProgress((current.questions || []).length, current.count_target || 3);
    }
    return current;
  }

  function renderPractice(set: Json): void {
    const body = panels.practice.body;
    body.replaceChildren();
    body.className = '';
    const questions = (set && set.questions) || [];
    if (!questions.length) {
      body.appendChild(el('p', 'font-body-sm text-body-sm text-on-surface-variant', 'The model did not produce usable practice problems this time. Ask again to retry.'));
      setChip('practice', 'None', 'warn');
      return;
    }
    body.appendChild(el('p', 'font-body-sm text-body-sm text-on-surface-variant mb-3',
      `Problems built from your question and your mistake (${set.misconception}). Get ${Math.round((set.mastery_threshold || 0.8) * 100)}% of a round right to finish; otherwise you get a new round of different problems.`));
    const rounds = el('div', 'space-y-6');
    body.appendChild(rounds);
    renderRound(set, rounds);
    setChip('practice', 'Done', 'done');
  }

  function renderRound(set: Json, rounds: HTMLElement): void {
    const section = el('div', 'space-y-3');
    const head = el('div', 'flex items-center justify-between');
    head.appendChild(el('span', 'font-label-md text-label-md text-on-surface', `Round ${set.round || 1} - ${LEVEL_LABEL[set.level] || 'Practice'}`));
    const score = el('span', 'font-label-sm text-label-sm text-outline', `0 / ${set.questions.length} answered`);
    head.appendChild(score);
    section.appendChild(head);
    if (set.previous) {
      section.appendChild(el('p', 'font-body-sm text-body-sm text-on-surface-variant',
        `Last round: ${set.previous.correct}/${set.previous.total} correct (${Math.round(set.previous.accuracy * 100)}%). These are new problems for the same mistake.`));
    }
    const list = el('div', 'space-y-3');
    set.questions.forEach((q: Json, index: number) => list.appendChild(practiceCard(q, index, (info) => onGraded(info, section, score, rounds))));
    section.appendChild(list);
    rounds.appendChild(section);
  }

  function onGraded(info: Json, section: HTMLElement, score: HTMLElement, rounds: HTMLElement): void {
    if (!info) return;
    score.textContent = `${info.correct} correct, ${info.answered} / ${info.total} answered`;
    if (!info.complete || section.dataset.done) return;
    section.dataset.done = '1';
    const pct = Math.round(info.accuracy * 100);
    if (info.mastered) {
      section.appendChild(el('div', 'rounded-xl bg-tertiary-container p-4 font-body-md text-body-md text-on-tertiary-container',
        `Mastered: ${info.correct}/${info.total} correct (${pct}%). You have fixed this misconception - no more practice needed.`));
      setChip('practice', 'Mastered', 'done');
      return;
    }
    const note = el('div', 'rounded-xl bg-surface-container p-4 font-body-md text-body-md text-on-surface',
      `${info.correct}/${info.total} correct (${pct}%), below ${Math.round(info.threshold * 100)}%. Making new problems (${(LEVEL_LABEL[info.next_level] || info.next_level).toLowerCase()})...`);
    section.appendChild(note);
    setChip('practice', 'New round...', 'work');
    nextRound(info.set_id, note, rounds);
  }

  async function nextRound(setId: string, note: HTMLElement, rounds: HTMLElement): Promise<void> {
    const gen = generation;
    try {
      const opened = await post('/api/practice/next', { set_id: setId });
      const payload = await fillRound(opened, gen, () => undefined);
      if (gen !== generation) return;
      if (!payload.questions || !payload.questions.length) throw new Error('The model did not produce usable problems');
      note.textContent += ' ready below.';
      renderRound(payload, rounds);
      setChip('practice', `Round ${payload.round}`, 'done');
    } catch (error: any) {
      if (gen !== generation) return;
      note.textContent = `Could not make a new round: ${error.message}. `;
      const retry = el('button', 'ml-2 rounded-full bg-primary px-3 py-1 font-label-md text-label-md text-on-primary', 'Try again');
      retry.type = 'button';
      retry.addEventListener('click', () => {
        retry.remove();
        note.textContent = 'Making new problems...';
        nextRound(setId, note, rounds);
      });
      note.appendChild(retry);
      setChip('practice', 'Retry', 'warn');
    }
  }

  function practiceCard(q: Json, index: number, onRound: (info: Json) => void): HTMLElement {
    const isCode = q.type === 'code';
    const card = el('div', 'rounded-xl bg-surface-container-low p-4');
    card.setAttribute('data-practice', String(index + 1));
    const top = el('div', 'flex items-center justify-between mb-2');
    top.appendChild(el('span', 'font-label-sm text-label-sm uppercase tracking-wider text-outline', `Practice ${index + 1}`));
    top.appendChild(el('span', 'font-label-sm text-label-sm ' + (q.verified ? 'text-on-tertiary-container' : 'text-outline'),
      q.verified ? '✓ answer machine-verified' : 'answer not machine-verified'));
    card.appendChild(top);
    card.appendChild(el('p', 'font-body-md text-body-md text-on-surface mb-2', q.prompt));
    if (isCode && q.code) card.appendChild(codeBlock(q.code));

    const input: HTMLInputElement | HTMLTextAreaElement = isCode ? el('textarea') : el('input');
    input.className = 'w-full rounded-lg bg-surface-container-lowest px-3 py-2 font-code-block text-code-block text-on-surface ring-1 ring-outline-variant/50 focus:ring-2 focus:ring-primary';
    input.placeholder = isCode ? 'Paste your corrected Python code here...' : 'Type your answer, for example 5/12';
    input.setAttribute('aria-label', `Answer for practice ${index + 1}`);
    if (input instanceof HTMLTextAreaElement) {
      input.rows = 4;
      input.spellcheck = false;
    } else {
      input.type = 'text';
    }
    card.appendChild(input);

    const row = el('div', 'mt-3 flex items-center gap-3');
    const submit = el('button', 'rounded-full bg-primary px-4 py-2 font-label-md text-label-md text-on-primary', 'Check answer');
    submit.type = 'button';
    const verdict = el('span', 'font-body-sm text-body-sm text-on-surface-variant');
    row.appendChild(submit);
    row.appendChild(verdict);
    card.appendChild(row);

    submit.addEventListener('click', async () => {
      if (!input.value.trim()) return;
      submit.disabled = true;
      const old = card.querySelector('[data-solution]');
      if (old) old.remove();
      try {
        const payload = await post('/api/practice/submit', {
          learner_id: learnerId(),
          practice_id: q.id,
          subject: q.subject,
          misconception: q.target_misconception,
          answer: input.value,
        });
        verdict.textContent = payload.correct ? 'Correct - this misconception is getting weaker.' : 'Not yet - compare with the solution below.';
        verdict.className = 'font-body-sm text-body-sm ' + (payload.correct ? 'text-on-tertiary-container' : 'text-error');
        const box = el('div', 'mt-3 rounded-lg bg-surface-container-lowest p-3 text-on-surface');
        box.setAttribute('data-solution', '1');
        box.appendChild(el('p', 'font-label-md text-label-md mb-2', isCode ? 'Correct code' : 'Correct answer'));
        if (isCode) {
          box.appendChild(codeBlock(payload.correct_code || q.correct_code || 'No reference solution available.'));
          if (payload.grading) box.appendChild(el('p', 'font-body-sm text-body-sm text-outline', `Graded by ${payload.grading}.`));
        } else {
          box.appendChild(el('p', 'font-body-md text-body-md mb-1', payload.correct_answer || q.correct_answer || ''));
        }
        if (payload.explanation) box.appendChild(el('p', 'font-body-sm text-body-sm text-on-surface-variant', payload.explanation));
        card.appendChild(box);
        if (payload.round) onRound(payload.round);
      } catch (error: any) {
        verdict.textContent = `Could not grade: ${error.message}`;
        verdict.className = 'font-body-sm text-body-sm text-error';
      } finally {
        submit.disabled = false;
      }
    });
    return card;
  }

  function addFeedback(result: Json): void {
    if (!result || !result.sample_id) return;
    const wrap = el('div', 'flex items-center justify-end gap-2 font-body-sm text-body-sm text-on-surface-variant');
    wrap.appendChild(document.createTextNode('Was this helpful?'));
    ['helpful', 'unhelpful'].forEach((value) => {
      const b = el('button', 'rounded-full px-3 py-1 bg-surface-container hover:bg-surface-container-high', value === 'helpful' ? '👍' : '👎');
      b.type = 'button';
      b.setAttribute('aria-label', value === 'helpful' ? 'Helpful' : 'Not helpful');
      b.addEventListener('click', async () => {
        b.disabled = true;
        try {
          await post('/api/llm/feedback', { sample_id: result.sample_id, feedback: value });
          wrap.textContent = 'Thanks for the feedback.';
        } catch {
          b.disabled = false;
        }
      });
      wrap.appendChild(b);
    });
    results.appendChild(wrap);
  }

  // ---------------------------------------------------------------- the four steps
  function stopAll(): void {
    AGENTS.forEach((a) => {
      const chip = panels[a.key] && panels[a.key].chip;
      if (chip && (chip.textContent === 'Working...' || chip.textContent === 'Waiting')) setChip(a.key, 'Stopped', 'warn');
    });
  }

  async function ask(): Promise<void> {
    const question = area.value.trim();
    if (!question) {
      area.focus();
      return;
    }
    if (busy) return;
    setBusy(true);
    buildPanels();
    results.scrollIntoView({ behavior: 'smooth', block: 'start' });
    const gen = ++generation;
    const live = (): boolean => gen === generation;
    try {
      const started = await post('/api/tutor/start', { question, subject: activeSubject, mode: 'diagnostic', learner_id: learnerId() });
      const runId: string = started.run_id;
      if (!live()) return;

      startAgent('explainer');
      const explained = await post('/api/tutor/explain', { run_id: runId });
      if (!live()) return;
      renderExplanation(explained.explanation);

      startAgent('solver');
      const solved = await post('/api/tutor/solve', { run_id: runId });
      if (!live()) return;
      renderSolution(solved.solution);

      startAgent('practice');
      try {
        const opened = await post('/api/tutor/practice', { run_id: runId });
        const set = await fillRound(opened, gen, (n) => {
          if (live()) panels.practice.body.textContent = `The model is writing practice problems (${n} ready)...`;
        });
        if (!live()) return;
        renderPractice(set);
      } catch (error) {
        if (!live()) return;
        if (isOffline(error)) throw error;
        renderPractice({ questions: [] });
      }

      startAgent('reviewer', 'Running the exact checks...');
      const reviewed = await post('/api/tutor/review', { run_id: runId });
      if (!live()) return;
      renderReview(reviewed.review);
      addFeedback(reviewed.result);
      history.unshift({ question, subject: activeSubject });
      renderHistory();
    } catch (error: any) {
      if (!live()) return;
      if (isOffline(error)) {
        showBanner(`Your tutor model is offline, so nothing was generated. ${error.payload.message || error.message || ''}`);
      } else if (error instanceof ApiError && error.payload.status === 'refused_injection') {
        showBanner(error.message);
      } else {
        showBanner(`Service unavailable: ${error.message}`);
      }
      stopAll();
    } finally {
      if (live()) setBusy(false);
      refreshBackendStatus();
    }
  }

  function setBusy(value: boolean): void {
    busy = value;
    send.disabled = value;
    send.classList.toggle('opacity-50', value);
    const icon = send.querySelector('.material-symbols-outlined');
    if (icon) icon.textContent = value ? 'hourglass_top' : 'arrow_upward';
  }

  // ---------------------------------------------------------------- sidebar + status
  function renderHistory(): void {
    const box = document.getElementById('history-list');
    if (!box) return;
    box.replaceChildren();
    if (!history.length) {
      box.appendChild(el('p', 'px-space-sm py-1.5 font-body-sm text-body-sm text-outline', 'Your questions from this visit will appear here.'));
      return;
    }
    history.slice(0, 12).forEach((item) => {
      const a = el('button', 'block w-full text-left px-space-sm py-1.5 rounded text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low transition-colors truncate font-body-sm text-body-sm', item.question.split('\n')[0]);
      a.type = 'button';
      a.title = item.question;
      a.addEventListener('click', () => {
        area.value = item.question;
        updateCounter();
        area.focus();
      });
      box.appendChild(a);
    });
  }

  async function refreshBackendStatus(): Promise<void> {
    if (!modelStatus) return;
    try {
      const res = await api.get('/api/backend-status');
      const s: Json = (res && res.data) || {};
      const agents: Json = s.agents || {};
      if (s.llmLoaded) {
        modelStatus.textContent = `Model online: ${String(s.model || 'fine-tuned Gemma').split(' - ')[0]}`;
        modelStatus.className = 'font-label-sm text-label-sm text-on-tertiary-container';
        modelStatus.title = '';
      } else {
        modelStatus.textContent = 'Model offline - answers are paused';
        modelStatus.className = 'font-label-sm text-label-sm text-error';
        modelStatus.title = agents.error || s.llmError || '';
      }
    } catch {
      modelStatus.textContent = 'Server unreachable';
      modelStatus.className = 'font-label-sm text-label-sm text-error';
    }
  }

  function updateCounter(): void {
    if (counter) counter.textContent = `${area.value.length} / ${MAX_CHARS}`;
  }

  // ---------------------------------------------------------------- wiring
  area.maxLength = MAX_CHARS;
  area.addEventListener('input', updateCounter);
  area.addEventListener('keydown', (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
      event.preventDefault();
      ask();
    }
  });
  send.addEventListener('click', () => {
    ask();
  });

  ([['tab-math', 'Mathematics'], ['tab-python', 'Python']] as Array<[string, string]>).forEach(([id, subject]) => {
    const card = document.getElementById(id);
    if (card) card.addEventListener('click', () => {
      activeSubject = subject;
    });
  });

  const newChat = Array.from(document.querySelectorAll('aside button')).find((b) => /new chat/i.test(b.textContent || ''));
  if (newChat) {
    newChat.addEventListener('click', () => {
      generation += 1;
      setBusy(false);
      area.value = '';
      updateCounter();
      results.classList.add('hidden');
      results.replaceChildren();
      area.focus();
    });
  }

  updateCounter();
  renderHistory();
  refreshBackendStatus();
  setInterval(refreshBackendStatus, 30000);
})();
