/* Misconception Tutor - frontend controller.
 *
 * Talks to the Flask backend. A question runs through four agents (all powered by the
 * fine-tuned model) and each agent's result is rendered as soon as it arrives:
 *   1 Explain  ->  2 Solve  ->  3 Practice  ->  4 Review
 * Everything coming from the server is inserted with textContent / DOM nodes (never innerHTML).
 */
(function () {
  'use strict';

  const MAX_CHARS = 4000;
  const textarea = document.querySelector('textarea');
  const sendButton = document.querySelector('button[aria-label="Send"]');
  const counter = document.getElementById('char-counter');
  const modelStatus = document.getElementById('model-status');
  if (!textarea || !sendButton) return;

  let activeSubject = 'Python'; // matches the card that is highlighted on load
  let busy = false;
  let currentController = null;
  const history = []; // { question, subject, result }

  function learnerId() {
    try {
      let id = localStorage.getItem('learner_id');
      if (!id) {
        id = 'learner_' + Math.random().toString(36).slice(2, 10);
        localStorage.setItem('learner_id', id);
      }
      return id;
    } catch (e) {
      return 'student_demo';
    }
  }

  // ---------------------------------------------------------------- tiny DOM helpers
  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  function inline(text) {
    // `code` and **bold** only; everything else stays literal text.
    const frag = document.createDocumentFragment();
    const parts = String(text).split(/(`[^`\n]+`|\*\*[^*\n]+\*\*)/g);
    parts.forEach((part) => {
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

  function codeBlock(code) {
    const pre = el('pre', 'whitespace-pre-wrap overflow-x-auto rounded-lg bg-surface-container-low p-3 font-code-block text-code-block text-on-surface my-2');
    pre.appendChild(el('code', '', code));
    return pre;
  }

  function markdown(text) {
    const root = el('div', 'space-y-2 font-body-md text-body-md text-on-surface');
    const chunks = String(text || '').split(/```[^\n]*\n([\s\S]*?)(?:```|$)/g);
    chunks.forEach((chunk, index) => {
      if (index % 2 === 1) {
        root.appendChild(codeBlock(chunk.replace(/\n$/, '')));
        return;
      }
      let list = null;
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
  let panels = {};

  function buildPanels() {
    results.replaceChildren();
    panels = {};
    const banner = el('div', 'hidden rounded-2xl p-4 bg-error-container text-on-error-container font-body-sm text-body-sm');
    banner.id = 'result-banner';
    results.appendChild(banner);
    AGENTS.forEach((agent) => {
      const card = el('div', 'rounded-2xl bg-surface-container-lowest p-5 shadow-sm ring-1 ring-outline-variant/30');
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

  function setChip(key, label, tone) {
    const chip = panels[key] && panels[key].chip;
    if (!chip) return;
    chip.textContent = label;
    const tones = {
      work: 'bg-secondary-fixed text-on-secondary-fixed animate-pulse',
      done: 'bg-tertiary-fixed text-on-tertiary-fixed',
      warn: 'bg-error-container text-on-error-container',
      idle: 'bg-surface-container text-on-surface-variant',
    };
    chip.className = 'font-label-sm text-label-sm px-2 py-0.5 rounded-full ' + (tones[tone] || tones.idle);
  }

  function showBanner(message, kind) {
    const banner = document.getElementById('result-banner');
    if (!banner) return;
    banner.className = 'rounded-2xl p-4 font-body-sm text-body-sm ' +
      (kind === 'info' ? 'bg-secondary-fixed text-on-secondary-fixed' : 'bg-error-container text-on-error-container');
    banner.textContent = message;
  }

  // ---------------------------------------------------------------- agent renderers
  function labelled(label, text) {
    const wrap = el('div', 'mb-3');
    wrap.appendChild(el('div', 'font-label-sm text-label-sm uppercase tracking-wider text-outline mb-1', label));
    wrap.appendChild(markdown(text));
    return wrap;
  }

  function renderExplanation(data) {
    const body = panels.explainer.body;
    body.replaceChildren();
    body.className = '';
    const s = data.sections || {};
    const order = [
      ['misconception', 'The idea that tripped you up'],
      ['what_went_wrong', 'What went wrong'],
      ['why_mistake', 'Why this mistake happens'],
      ['correct_thinking', 'How to think about it'],
      ['check_yourself', 'Check yourself'],
    ];
    const present = order.filter(([key]) => s[key]);
    if (present.length < 2) {
      body.appendChild(markdown(data.text));
    } else {
      present.forEach(([key, label]) => body.appendChild(labelled(label, s[key])));
    }
    setChip('explainer', 'Done', 'done');
  }

  function renderSolution(data) {
    const body = panels.solver.body;
    body.replaceChildren();
    body.className = '';
    if (data.kind === 'code') {
      if (data.code) body.appendChild(codeBlock(data.code));
      if (data.what_changed) body.appendChild(labelled('What changed', data.what_changed));
      if (data.run) {
        const ok = data.run.success;
        const out = el('div', 'rounded-lg p-3 font-body-sm text-body-sm ' + (ok ? 'bg-tertiary-fixed/40' : 'bg-error-container'));
        out.appendChild(el('div', 'font-label-sm text-label-sm uppercase tracking-wider mb-1', ok ? 'Output when this code was actually run' : 'Running this code failed'));
        out.appendChild(el('pre', 'whitespace-pre-wrap font-code-block text-code-block',
          ok ? ((data.run.stdout || '').trim() || '(no output)') : `${data.run.error_type}: ${data.run.error_message}`));
        body.appendChild(out);
      }
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

  function renderReview(review) {
    const body = panels.reviewer.body;
    body.replaceChildren();
    body.className = '';
    const verdict = review.approved
      ? (review.verified ? 'Checked - the answer and the code match exact computation.' : 'Approved, but some parts could not be machine-verified.')
      : 'Not fully verified - treat the answer with caution.';
    body.appendChild(el('p', 'font-body-md text-body-md text-on-surface mb-3 font-medium', verdict));
    const icons = { pass: '✓', fail: '✕', warn: '!', skip: '–' };
    const colors = { pass: 'text-on-tertiary-container', fail: 'text-error', warn: 'text-error', skip: 'text-outline' };
    const list = el('ul', 'space-y-1.5');
    (review.checks || []).forEach((check) => {
      const li = el('li', 'flex gap-2 font-body-sm text-body-sm text-on-surface-variant');
      li.appendChild(el('span', 'font-semibold w-4 shrink-0 ' + (colors[check.status] || ''), icons[check.status] || '•'));
      li.appendChild(el('span', '', check.detail));
      list.appendChild(li);
    });
    body.appendChild(list);
    if (review.model_notes) body.appendChild(labelled('Reviewer model notes', review.model_notes));
    if (review.revisions) {
      body.appendChild(el('p', 'font-body-sm text-body-sm text-outline mt-2', `${review.revisions} automatic revision(s) were needed.`));
    }
    setChip('reviewer', review.approved ? 'Done' : 'Needs care', review.approved ? 'done' : 'warn');
  }

  // ---- practice ------------------------------------------------------------------------
  function renderPractice(set) {
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

  const LEVEL_LABEL = { start: 'Starting level', easier: 'Easier', same: 'Same level, new problems', harder: 'Harder' };

  function renderRound(set, rounds) {
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
    set.questions.forEach((q, index) => list.appendChild(practiceCard(q, index, (info) => onGraded(info, set, section, score, rounds))));
    section.appendChild(list);
    rounds.appendChild(section);
  }

  function onGraded(info, set, section, score, rounds) {
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

  async function nextRound(setId, note, rounds) {
    try {
      const res = await fetch('/api/practice/next', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ set_id: setId }),
      });
      const payload = await res.json();
      if (!res.ok) throw new Error(payload.error || 'Could not create new problems');
      if (!payload.questions || !payload.questions.length) throw new Error('The model did not produce usable problems');
      note.textContent += ' ready below.';
      renderRound(payload, rounds);
      setChip('practice', `Round ${payload.round}`, 'done');
    } catch (error) {
      note.textContent = `Could not make a new round: ${error.message}. `;
      const retry = el('button', 'ml-2 rounded-full bg-primary px-3 py-1 font-label-md text-label-md text-on-primary', 'Try again');
      retry.type = 'button';
      retry.addEventListener('click', () => { retry.remove(); note.textContent = 'Making new problems...'; nextRound(setId, note, rounds); });
      note.appendChild(retry);
      setChip('practice', 'Retry', 'warn');
    }
  }

  function practiceCard(q, index, onRound) {
    const isCode = q.type === 'code';
    const card = el('div', 'rounded-xl bg-surface-container-low p-4');
    const top = el('div', 'flex items-center justify-between mb-2');
    top.appendChild(el('span', 'font-label-sm text-label-sm uppercase tracking-wider text-outline', `Practice ${index + 1}`));
    top.appendChild(el('span', 'font-label-sm text-label-sm ' + (q.verified ? 'text-on-tertiary-container' : 'text-outline'),
      q.verified ? '✓ answer machine-verified' : 'answer not machine-verified'));
    card.appendChild(top);
    card.appendChild(el('p', 'font-body-md text-body-md text-on-surface mb-2', q.prompt));
    if (isCode && q.code) card.appendChild(codeBlock(q.code));

    const input = el(isCode ? 'textarea' : 'input', 'w-full rounded-lg bg-surface-container-lowest px-3 py-2 font-code-block text-code-block text-on-surface ring-1 ring-outline-variant/50 focus:ring-2 focus:ring-primary');
    input.placeholder = isCode ? 'Paste your corrected Python code here...' : 'Type your answer, for example 5/12';
    input.setAttribute('aria-label', `Answer for practice ${index + 1}`);
    if (isCode) { input.rows = 4; input.spellcheck = false; } else { input.type = 'text'; }
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
        const res = await fetch('/api/practice/submit', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            learner_id: learnerId(),
            session_id: `practice_${Date.now()}`,
            practice_id: q.id,
            subject: q.subject,
            misconception: q.target_misconception,
            answer: input.value,
            correct_answer: q.correct_answer,
            reference_code: q.code,
          }),
        });
        const payload = await res.json();
        if (!res.ok) throw new Error(payload.error || 'Unable to grade this answer');
        verdict.textContent = payload.correct ? 'Correct - this misconception is getting weaker.' : 'Not yet - compare with the solution below.';
        verdict.className = 'font-body-sm text-body-sm ' + (payload.correct ? 'text-on-tertiary-container' : 'text-error');
        const box = el('div', 'mt-3 rounded-lg bg-surface-container-lowest p-3 text-on-surface');
        box.setAttribute('data-solution', '1');
        box.appendChild(el('p', 'font-label-md text-label-md mb-2', isCode ? 'Correct code' : 'Correct answer'));
        if (isCode) {
          box.appendChild(codeBlock(payload.correct_code || q.correct_code || 'No reference solution available.'));
          if (payload.error) box.appendChild(el('p', 'font-body-sm text-body-sm text-error', `Your code failed: ${payload.error}`));
          else if (payload.your_output !== undefined && !payload.correct) {
            box.appendChild(el('p', 'font-body-sm text-body-sm', `Your output: ${payload.your_output || '(nothing)'}  |  expected: ${payload.expected_output || '(nothing)'}`));
          }
        } else {
          box.appendChild(el('p', 'font-body-md text-body-md mb-1', payload.correct_answer || q.correct_answer || ''));
        }
        if (payload.explanation) box.appendChild(el('p', 'font-body-sm text-body-sm text-on-surface-variant', payload.explanation));
        card.appendChild(box);
        if (onRound && payload.round) onRound(payload.round);
      } catch (error) {
        verdict.textContent = `Could not grade: ${error.message}`;
        verdict.className = 'font-body-sm text-body-sm text-error';
      } finally {
        submit.disabled = false;
      }
    });
    return card;
  }

  // ---------------------------------------------------------------- stream handling
  function handleEvent(event, state) {
    switch (event.event) {
      case 'agent_start':
        setChip(event.agent, 'Working...', 'work');
        if (panels[event.agent]) panels[event.agent].body.textContent = 'The model is writing this part...';
        break;
      case 'revision':
        setChip(event.agent, 'Re-checking...', 'work');
        break;
      case 'agent_result':
        if (event.agent === 'explainer') renderExplanation(event.data);
        else if (event.agent === 'solver') renderSolution(event.data);
        else if (event.agent === 'practice') renderPractice(event.data);
        else if (event.agent === 'reviewer') renderReview(event.data);
        break;
      case 'complete':
        state.result = event.result;
        addFeedback(event.result);
        break;
      case 'error':
        state.error = event;
        break;
      default:
        break;
    }
  }

  function addFeedback(result) {
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
          await fetch('/api/llm/feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sample_id: result.sample_id, feedback: value }),
          });
          wrap.textContent = 'Thanks for the feedback.';
        } catch (e) { b.disabled = false; }
      });
      wrap.appendChild(b);
    });
    results.appendChild(wrap);
  }

  async function readStream(response, state) {
    if (!response.body || !response.body.getReader) {
      (await response.text()).split('\n').filter(Boolean).forEach((line) => handleEvent(JSON.parse(line), state));
      return;
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let newline;
      while ((newline = buffer.indexOf('\n')) >= 0) {
        const line = buffer.slice(0, newline).trim();
        buffer = buffer.slice(newline + 1);
        if (line) handleEvent(JSON.parse(line), state);
      }
    }
    if (buffer.trim()) handleEvent(JSON.parse(buffer.trim()), state);
  }

  async function ask() {
    const question = textarea.value.trim();
    if (!question) { textarea.focus(); return; }
    if (busy) return;
    setBusy(true);
    buildPanels();
    results.scrollIntoView({ behavior: 'smooth', block: 'start' });
    currentController = new AbortController();
    const state = { result: null, error: null };
    try {
      const response = await fetch('/api/tutor/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, subject: activeSubject, mode: 'diagnostic', learner_id: learnerId() }),
        signal: currentController.signal,
      });
      if (!response.ok) {
        let payload = {};
        try { payload = await response.json(); } catch (e) { /* not JSON */ }
        throw new Error(payload.error || payload.answer || `The server answered with an error (${response.status}).`);
      }
      await readStream(response, state);
      if (state.error) {
        const offline = state.error.status === 'model_unavailable';
        showBanner(offline
          ? `Your tutor model is offline, so nothing was generated. ${state.error.message || ''}`
          : (state.error.message || 'Something went wrong.'));
        AGENTS.forEach((a) => { const chip = panels[a.key].chip; if (chip.textContent === 'Working...' || chip.textContent === 'Waiting') setChip(a.key, 'Stopped', 'warn'); });
      } else if (state.result) {
        history.unshift({ question, subject: activeSubject });
        renderHistory();
      }
    } catch (error) {
      if (error.name !== 'AbortError') showBanner(`Service unavailable: ${error.message}`);
    } finally {
      setBusy(false);
      refreshBackendStatus();
    }
  }

  function setBusy(value) {
    busy = value;
    sendButton.disabled = value;
    sendButton.classList.toggle('opacity-50', value);
    const icon = sendButton.querySelector('.material-symbols-outlined');
    if (icon) icon.textContent = value ? 'hourglass_top' : 'arrow_upward';
  }

  // ---------------------------------------------------------------- sidebar + status
  function renderHistory() {
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
      a.addEventListener('click', () => { textarea.value = item.question; updateCounter(); textarea.focus(); });
      box.appendChild(a);
    });
  }

  async function refreshBackendStatus() {
    if (!modelStatus) return;
    try {
      const res = await fetch('/api/backend-status', { cache: 'no-store' });
      const s = await res.json();
      const agents = s.agents || {};
      if (s.llmLoaded) {
        modelStatus.textContent = `Model online: ${String(s.model || 'fine-tuned Gemma').split(' - ')[0]}`;
        modelStatus.className = 'font-label-sm text-label-sm text-on-tertiary-container';
      } else {
        modelStatus.textContent = 'Model offline - answers are paused';
        modelStatus.className = 'font-label-sm text-label-sm text-error';
        modelStatus.title = agents.error || s.llmError || '';
      }
    } catch (e) {
      modelStatus.textContent = 'Server unreachable';
      modelStatus.className = 'font-label-sm text-label-sm text-error';
    }
  }

  function updateCounter() {
    if (counter) counter.textContent = `${textarea.value.length} / ${MAX_CHARS}`;
  }

  // ---------------------------------------------------------------- wiring
  textarea.maxLength = MAX_CHARS;
  textarea.addEventListener('input', updateCounter);
  textarea.addEventListener('keydown', (event) => {
    if (event.isComposing) return;
    if (event.key === 'Enter') {
      if (!event.shiftKey) {
        event.preventDefault();
        ask();
      }
      // Shift + Enter naturally falls through to insert a new line
    }
  });
  sendButton.addEventListener('click', ask);

  [['tab-math', 'Mathematics'], ['tab-python', 'Python']].forEach(([id, subject]) => {
    const card = document.getElementById(id);
    if (card) card.addEventListener('click', () => { activeSubject = subject; });
  });

  const newChat = Array.from(document.querySelectorAll('aside button')).find((b) => /new chat/i.test(b.textContent));
  if (newChat) {
    newChat.addEventListener('click', () => {
      if (currentController) currentController.abort();
      textarea.value = '';
      updateCounter();
      results.classList.add('hidden');
      results.replaceChildren();
      textarea.focus();
    });
  }

  updateCounter();
  renderHistory();
  refreshBackendStatus();
  setInterval(refreshBackendStatus, 30000);
})();
