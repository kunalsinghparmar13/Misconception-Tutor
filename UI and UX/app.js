/* Sikora AI (Misconception Tutor) - frontend controller for index.html.
 *
 * Talks to the Flask backend. A question runs through four agents (all powered by the
 * fine-tuned model) and each agent's result is rendered as soon as it arrives:
 *   1 Explain  ->  2 Solve  ->  3 Practice  ->  4 Review
 * Everything coming from the server is inserted with textContent / DOM nodes (never innerHTML).
 * Styles for the result cards live in tutor.css.
 */
(async function () {
  'use strict';

  // Signed-in learners only (auth.js). Without Supabase configured the page still works for local testing.
  const auth = window.tutorAuth || null;
  const user = auth ? await auth.requireUser() : null;
  const apiFetch = auth ? auth.apiFetch : fetch.bind(window);

  const MAX_CHARS = 4000;
  const textarea = document.getElementById('composer-input');
  const sendButton = document.querySelector('button[aria-label="Send"]');
  const hint = document.getElementById('compose-hint');
  const modelPill = document.getElementById('model-pill');
  const modelStatus = document.getElementById('model-status');
  const content = document.querySelector('main.content');
  if (!textarea || !sendButton || !content) return;

  let busy = false;
  let currentController = null;
  let currentSessionId = null; // Supabase row for the question on screen
  const history = []; // { question, subject }

  function learnerId() {
    if (user) return user.id;
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

  /** The subject card the learner picked in index.html ('math' or 'python'). */
  function activeSubject() {
    const card = document.querySelector('.subject.selected');
    return card && card.dataset.subject === 'math' ? 'Mathematics' : 'Python';
  }

  function setHint(text) {
    if (hint) hint.textContent = text;
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
    String(text).split(/(`[^`\n]+`|\*\*[^*\n]+\*\*)/g).forEach((part) => {
      if (!part) return;
      if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
        frag.appendChild(el('code', 't-inline-code', part.slice(1, -1)));
      } else if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
        frag.appendChild(el('strong', '', part.slice(2, -2)));
      } else {
        frag.appendChild(document.createTextNode(part));
      }
    });
    return frag;
  }

  // ---------------------------------------------------------------- code colours
  // Colours code the way VS Code's default dark theme does (classes are coloured in tutor.css).
  const PY_CONTROL = new Set(['if', 'elif', 'else', 'for', 'while', 'in', 'return', 'break', 'continue', 'pass',
    'try', 'except', 'finally', 'with', 'as', 'raise', 'yield', 'await', 'async', 'import', 'from', 'del',
    'assert', 'global', 'nonlocal']);
  const PY_KEYWORD = new Set(['def', 'class', 'lambda', 'and', 'or', 'not', 'is', 'None', 'True', 'False', 'self', 'cls']);
  const PY_BUILTIN_TYPES = new Set(['int', 'float', 'str', 'list', 'dict', 'set', 'tuple', 'bool', 'bytes', 'object',
    'Exception', 'ValueError', 'TypeError', 'IndexError', 'KeyError', 'ZeroDivisionError', 'RecursionError']);
  const PY_TOKEN = new RegExp([
    '(#[^\\n]*)',                                                       // 1 comment
    '((?:[rRbBuUfF]{1,2})?(?:"""[\\s\\S]*?(?:"""|$)|\'\'\'[\\s\\S]*?(?:\'\'\'|$)|"(?:\\\\.|[^"\\\\\\n])*"?|\'(?:\\\\.|[^\'\\\\\\n])*\'?))', // 2 string
    '(\\b(?:0[xXoObB][\\da-fA-F_]+|\\d[\\d_]*\\.?\\d*(?:[eE][+-]?\\d+)?|\\.\\d+)[jJ]?\\b)', // 3 number
    '([A-Za-z_]\\w*)',                                                  // 4 name
    '([()[\\]{}])',                                                     // 5 bracket
    '([+\\-*/%=<>!&|^~@:.,;]+)',                                        // 6 operator / punctuation
  ].join('|'), 'g');

  function colourPython(code) {
    const frag = document.createDocumentFragment();
    let last = 0;
    let depth = 0;
    let prevName = '';
    const push = (text, cls) => {
      if (!text) return;
      frag.appendChild(cls ? el('span', cls, text) : document.createTextNode(text));
    };
    for (const m of code.matchAll(PY_TOKEN)) {
      push(code.slice(last, m.index));
      last = m.index + m[0].length;
      const [tok, comment, string, number, name, bracket] = m;
      if (comment) push(comment, 'c-comment');
      else if (string) push(string, 'c-string');
      else if (number) push(number, 'c-number');
      else if (name) {
        const next = code.slice(last).match(/^\s*(\(?)/);
        let cls = 'c-var';
        if (PY_CONTROL.has(name)) cls = 'c-control';
        else if (PY_KEYWORD.has(name)) cls = 'c-keyword';
        else if (prevName === 'class' || PY_BUILTIN_TYPES.has(name)) cls = 'c-type';
        else if (prevName === 'def' || (next && next[1] === '(')) cls = 'c-func';
        push(name, cls);
        prevName = name;
        continue;
      } else if (bracket) {
        const opening = '([{'.includes(bracket);
        if (!opening) depth = Math.max(0, depth - 1);
        push(bracket, 'c-bracket' + (depth % 3));
        if (opening) depth += 1;
      } else {
        push(tok, 'c-op');
      }
      prevName = '';
    }
    push(code.slice(last));
    return frag;
  }

  function codeBlock(code) {
    const pre = el('pre', 't-code');
    const inner = el('code');
    inner.appendChild(colourPython(String(code)));
    pre.appendChild(inner);
    return pre;
  }

  function markdown(text) {
    const root = el('div', 't-md');
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
          const h = el('h4');
          h.appendChild(inline(heading[1]));
          root.appendChild(h);
        } else if (bullet) {
          if (!list) {
            list = el('ul');
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
  const results = el('section', 't-results');
  results.id = 'llm-response';
  results.hidden = true;
  const greeting = content.querySelector('.greeting');
  if (greeting) greeting.after(results);
  else content.prepend(results);

  const AGENTS = [
    { key: 'explainer', number: 1, title: 'Why it went wrong', hint: 'Explanation agent' },
    { key: 'solver', number: 2, title: 'The correct answer', hint: 'Solution agent' },
    { key: 'practice', number: 3, title: 'Practice for you', hint: 'Practice agent' },
    { key: 'reviewer', number: 4, title: 'Review', hint: 'Review agent' },
  ];
  let panels = {};

  function buildPanels(question) {
    results.replaceChildren();
    panels = {};
    const head = el('div', 't-results-head');
    head.appendChild(el('div', 'eyebrow', 'YOUR QUESTION'));
    head.appendChild(el('p', 't-question', question));
    const close = el('button', 't-link', 'Clear');
    close.type = 'button';
    close.addEventListener('click', resetResults);
    head.appendChild(close);
    results.appendChild(head);
    const banner = el('div', 't-banner');
    banner.id = 'result-banner';
    banner.hidden = true;
    results.appendChild(banner);
    AGENTS.forEach((agent) => {
      const card = el('div', 't-card');
      const top = el('div', 't-card-head');
      const left = el('div', 't-card-title');
      left.appendChild(el('span', 't-num', String(agent.number)));
      left.appendChild(el('span', '', agent.title));
      const chip = el('span', 't-chip', 'Waiting');
      top.appendChild(left);
      top.appendChild(chip);
      const body = el('div', 't-body t-muted', agent.hint + ' will appear here.');
      card.appendChild(top);
      card.appendChild(body);
      results.appendChild(card);
      panels[agent.key] = { card, chip, body };
    });
    results.hidden = false;
  }

  function resetResults() {
    if (currentController) currentController.abort();
    results.hidden = true;
    results.replaceChildren();
    setHint('Choose a learning path or type your question');
  }

  function setChip(key, label, tone) {
    const chip = panels[key] && panels[key].chip;
    if (!chip) return;
    chip.textContent = label;
    chip.className = 't-chip' + (tone && tone !== 'idle' ? ' is-' + tone : '');
  }

  function showBanner(message, kind) {
    const banner = document.getElementById('result-banner');
    if (!banner) return;
    banner.className = 't-banner' + (kind === 'info' ? ' is-info' : '');
    banner.textContent = message;
    banner.hidden = false;
  }

  function freshBody(key) {
    const body = panels[key].body;
    body.replaceChildren();
    body.className = 't-body';
    return body;
  }

  // ---------------------------------------------------------------- agent renderers
  function labelled(label, text) {
    const wrap = el('div', 't-section');
    wrap.appendChild(el('div', 't-label', label));
    wrap.appendChild(markdown(text));
    return wrap;
  }

  function renderExplanation(data) {
    const body = freshBody('explainer');
    const s = data.sections || {};
    const order = [
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

  function renderSolution(data) {
    const body = freshBody('solver');
    if (data.kind === 'code') {
      if (data.code) body.appendChild(codeBlock(data.code));
      if (data.what_changed) body.appendChild(labelled('What changed', data.what_changed));
      if (data.run) {
        const ok = data.run.success;
        const out = el('div', 't-run' + (ok ? '' : ' is-bad'));
        out.appendChild(el('div', 't-label', ok ? 'Output when this code was actually run' : 'Running this code failed'));
        out.appendChild(el('pre', 't-run-out',
          ok ? ((data.run.stdout || '').trim() || '(no output)') : `${data.run.error_type}: ${data.run.error_message}`));
        body.appendChild(out);
      }
      if (!data.code) body.appendChild(markdown(data.text));
    } else {
      if (data.final_answer) {
        const box = el('div', 't-final');
        box.appendChild(el('div', 't-label', 'Final answer'));
        box.appendChild(el('div', 't-final-value', data.final_answer));
        body.appendChild(box);
      }
      body.appendChild(markdown(data.steps || data.text));
    }
    setChip('solver', 'Done', 'done');
  }

  function renderReview(review) {
    const body = freshBody('reviewer');
    const verdict = review.approved
      ? (review.verified ? 'Checked - the answer and the code match exact computation.' : 'Approved, but some parts could not be machine-verified.')
      : 'Not fully verified - treat the answer with caution.';
    body.appendChild(el('p', 't-verdict', verdict));
    const icons = { pass: '✓', fail: '✕', warn: '!', skip: '–' };
    const list = el('ul', 't-checks');
    (review.checks || []).forEach((check) => {
      const li = el('li');
      li.appendChild(el('span', 't-check-icon is-' + (check.status || 'skip'), icons[check.status] || '•'));
      li.appendChild(el('span', '', check.detail));
      list.appendChild(li);
    });
    body.appendChild(list);
    if (review.model_notes) body.appendChild(labelled('Reviewer model notes', review.model_notes));
    if (review.revisions) body.appendChild(el('p', 't-muted', `${review.revisions} automatic revision(s) were needed.`));
    setChip('reviewer', review.approved ? 'Done' : 'Needs care', review.approved ? 'done' : 'warn');
  }

  // ---- practice ------------------------------------------------------------------------
  function renderPractice(set) {
    const body = freshBody('practice');
    const questions = (set && set.questions) || [];
    if (!questions.length) {
      body.appendChild(el('p', 't-muted', 'The model did not produce usable practice problems this time. Ask again to retry.'));
      setChip('practice', 'None', 'warn');
      return;
    }
    body.appendChild(el('p', 't-muted',
      `Problems built from your question and your mistake (${set.misconception}). Get ${Math.round((set.mastery_threshold || 0.8) * 100)}% of a round right to finish; otherwise you get a new round of different problems.`));
    const rounds = el('div', 't-rounds');
    body.appendChild(rounds);
    renderRound(set, rounds);
    setChip('practice', 'Done', 'done');
  }

  const LEVEL_LABEL = { start: 'Starting level', easier: 'Easier', same: 'Same level, new problems', harder: 'Harder' };

  function renderRound(set, rounds) {
    const section = el('div', 't-round');
    const head = el('div', 't-round-head');
    head.appendChild(el('span', '', `Round ${set.round || 1} · ${LEVEL_LABEL[set.level] || 'Practice'}`));
    const score = el('span', 't-muted', `0 / ${set.questions.length} answered`);
    head.appendChild(score);
    section.appendChild(head);
    if (set.previous) {
      section.appendChild(el('p', 't-muted',
        `Last round: ${set.previous.correct}/${set.previous.total} correct (${Math.round(set.previous.accuracy * 100)}%). These are new problems for the same mistake.`));
    }
    const list = el('div', 't-practice-list');
    set.questions.forEach((q, index) => list.appendChild(practiceCard(q, index, (info) => onGraded(info, section, score, rounds))));
    section.appendChild(list);
    rounds.appendChild(section);
  }

  function onGraded(info, section, score, rounds) {
    if (!info) return;
    score.textContent = `${info.correct} correct, ${info.answered} / ${info.total} answered`;
    if (!info.complete || section.dataset.done) return;
    section.dataset.done = '1';
    const pct = Math.round(info.accuracy * 100);
    if (info.mastered) {
      section.appendChild(el('div', 't-note is-good',
        `Mastered: ${info.correct}/${info.total} correct (${pct}%). You have fixed this misconception - no more practice needed.`));
      setChip('practice', 'Mastered', 'done');
      return;
    }
    const note = el('div', 't-note',
      `${info.correct}/${info.total} correct (${pct}%), below ${Math.round(info.threshold * 100)}%. Making new problems (${(LEVEL_LABEL[info.next_level] || info.next_level).toLowerCase()})...`);
    section.appendChild(note);
    setChip('practice', 'New round...', 'work');
    nextRound(info.set_id, note, rounds);
  }

  async function nextRound(setId, note, rounds) {
    try {
      const res = await apiFetch('/api/practice/next', {
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
      const retry = el('button', 't-btn', 'Try again');
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

  function practiceCard(q, index, onRound) {
    const isCode = q.type === 'code';
    const card = el('div', 't-practice');
    const top = el('div', 't-practice-head');
    top.appendChild(el('span', 't-label', `Practice ${index + 1}`));
    top.appendChild(el('span', q.verified ? 't-verified' : 't-muted',
      q.verified ? '✓ answer machine-verified' : 'answer not machine-verified'));
    card.appendChild(top);
    card.appendChild(el('p', 't-prompt', q.prompt));
    if (isCode && q.code) card.appendChild(codeBlock(q.code));

    const input = el(isCode ? 'textarea' : 'input', 't-input');
    input.placeholder = isCode ? 'Paste your corrected Python code here...' : 'Type your answer, for example 5/12';
    input.setAttribute('aria-label', `Answer for practice ${index + 1}`);
    if (isCode) {
      input.rows = 4;
      input.spellcheck = false;
    } else {
      input.type = 'text';
    }
    card.appendChild(input);

    const row = el('div', 't-practice-row');
    const submit = el('button', 't-btn', 'Check answer');
    submit.type = 'button';
    const verdict = el('span', 't-muted');
    row.appendChild(submit);
    row.appendChild(verdict);
    card.appendChild(row);

    submit.addEventListener('click', async () => {
      if (!input.value.trim()) return;
      submit.disabled = true;
      const old = card.querySelector('[data-solution]');
      if (old) old.remove();
      try {
        const res = await apiFetch('/api/practice/submit', {
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
        verdict.className = payload.correct ? 't-good' : 't-bad';
        const box = el('div', 't-solution');
        box.setAttribute('data-solution', '1');
        box.appendChild(el('div', 't-label', isCode ? 'Correct code' : 'Correct answer'));
        if (isCode) {
          box.appendChild(codeBlock(payload.correct_code || q.correct_code || 'No reference solution available.'));
          if (payload.error) box.appendChild(el('p', 't-bad', `Your code failed: ${payload.error}`));
          else if (payload.your_output !== undefined && !payload.correct) {
            box.appendChild(el('p', 't-muted', `Your output: ${payload.your_output || '(nothing)'}  |  expected: ${payload.expected_output || '(nothing)'}`));
          }
        } else {
          box.appendChild(el('p', 't-final-inline', payload.correct_answer || q.correct_answer || ''));
        }
        if (payload.explanation) box.appendChild(el('p', 't-muted', payload.explanation));
        card.appendChild(box);
        if (auth) {
          auth.savePracticeAttempt({
            session_id: currentSessionId,
            practice_id: q.id,
            set_id: q.set_id,
            misconception: q.target_misconception,
            answer: input.value,
            correct: payload.correct,
          });
        }
        if (onRound && payload.round) onRound(payload.round);
      } catch (error) {
        verdict.textContent = `Could not grade: ${error.message}`;
        verdict.className = 't-bad';
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
    const wrap = el('div', 't-feedback');
    wrap.appendChild(document.createTextNode('Was this helpful?'));
    ['helpful', 'unhelpful'].forEach((value) => {
      const b = el('button', 't-btn is-ghost', value === 'helpful' ? '👍' : '👎');
      b.type = 'button';
      b.setAttribute('aria-label', value === 'helpful' ? 'Helpful' : 'Not helpful');
      b.addEventListener('click', async () => {
        b.disabled = true;
        try {
          await apiFetch('/api/llm/feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sample_id: result.sample_id, feedback: value }),
          });
          if (auth) auth.saveFeedback(currentSessionId, value);
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

  function stopPanels() {
    AGENTS.forEach((a) => {
      const chip = panels[a.key] && panels[a.key].chip;
      if (chip && (chip.textContent === 'Working...' || chip.textContent === 'Waiting')) {
        setChip(a.key, 'Stopped', 'warn');
        panels[a.key].body.textContent = 'Not generated because the tutor stopped.';
      }
    });
  }

  async function ask() {
    const question = textarea.value.trim().slice(0, MAX_CHARS);
    if (!question) { textarea.focus(); return; }
    if (busy) return;
    const subject = activeSubject();
    currentSessionId = null;
    textarea.value = '';
    textarea.dispatchEvent(new Event('input')); // index.html resizes the box and greys out Send
    setBusy(true);
    buildPanels(question);
    results.scrollIntoView({ behavior: 'smooth', block: 'start' });
    setHint('Your tutor is working through it…');
    currentController = new AbortController();
    const state = { result: null, error: null };
    try {
      const response = await apiFetch('/api/tutor/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, subject, mode: 'diagnostic', learner_id: learnerId() }),
        signal: currentController.signal,
      });
      if (!response.ok) {
        let payload = {};
        try { payload = await response.json(); } catch (e) { /* not JSON */ }
        const err = new Error(payload.error || payload.answer || `The server answered with an error (${response.status}).`);
        err.fromServer = response.status < 500; // e.g. an empty or refused question: show the message as is
        throw err;
      }
      await readStream(response, state);
      if (state.error) {
        const offline = state.error.status === 'model_unavailable';
        showBanner(offline
          ? `Your tutor model is offline, so nothing was generated. ${state.error.message || ''}`
          : (state.error.message || 'Something went wrong.'));
        stopPanels();
        setHint('The tutor stopped · Try again in a minute');
      } else if (state.result) {
        history.unshift({ question, subject });
        renderHistory();
        if (auth) {
          const r = state.result;
          currentSessionId = await auth.saveSession({
            question,
            subject,
            misconception: r.misconception,
            sample_id: r.sample_id,
            result: {
              agents: r.agents || null,
              practice_set: r.practice_set || null,
              answer: r.answer || null,
              model: r.model || null,
            },
          });
        }
        setHint('Done · Ask a follow-up or try the practice problems');
      }
    } catch (error) {
      if (error.name !== 'AbortError') {
        showBanner(error.fromServer ? error.message : `Service unavailable: ${error.message}`);
        stopPanels();
        setHint(error.fromServer ? 'Edit your question and send it again' : 'Could not reach the tutor');
      }
    } finally {
      setBusy(false);
      refreshBackendStatus();
    }
  }

  function setBusy(value) {
    busy = value;
    sendButton.disabled = value;
    sendButton.classList.toggle('is-busy', value);
  }

  // ---------------------------------------------------------------- sidebar + status
  function renderHistory() {
    const box = document.querySelector('.recent');
    if (!box || !history.length) return; // keeps the design's sample sessions until there is real history
    box.replaceChildren();
    history.slice(0, 8).forEach((item) => {
      const b = el('button', '', item.question.split('\n')[0]);
      b.type = 'button';
      b.title = item.question;
      b.addEventListener('click', () => {
        textarea.value = item.question;
        textarea.dispatchEvent(new Event('input'));
        textarea.focus();
      });
      box.appendChild(b);
    });
  }

  async function refreshBackendStatus() {
    if (!modelStatus) return;
    try {
      const res = await fetch('/api/backend-status', { cache: 'no-store' });
      const s = await res.json();
      const agents = s.agents || {};
      const online = Boolean(s.llmLoaded);
      modelStatus.textContent = online ? 'Sikora ready' : 'Tutor offline';
      if (modelPill) {
        modelPill.classList.toggle('is-offline', !online);
        modelPill.title = online ? String(s.model || 'fine-tuned model').split(' - ')[0] : (agents.error || s.llmError || '');
      }
    } catch (e) {
      modelStatus.textContent = 'Server unreachable';
      if (modelPill) modelPill.classList.add('is-offline');
    }
  }

  async function loadAccount() {
    if (!auth || !user) return;
    const p = await auth.profile(user);
    const nameEl = document.getElementById('profile-name');
    const avatar = document.getElementById('profile-avatar');
    if (nameEl) {
      nameEl.textContent = p.name;
      nameEl.title = p.email;
    }
    if (avatar) {
      const parts = p.name.trim().split(/\s+/);
      avatar.textContent = ((parts[0] || '?')[0] + (parts.length > 1 ? parts[parts.length - 1][0] : '')).toUpperCase();
    }
    ['sign-out', 'sign-out-top'].forEach((id) => {
      const button = document.getElementById(id);
      if (button) button.addEventListener('click', () => auth.signOut());
    });
    const past = await auth.recentSessions(8);
    const box = document.querySelector('.recent');
    if (box) {
      box.replaceChildren();
      if (!past.length) box.appendChild(el('p', 't-muted t-recent-empty', 'Your questions will appear here.'));
    }
    past.reverse().forEach((row) => history.unshift({ question: row.question, subject: row.subject }));
    renderHistory();
  }

  // ---------------------------------------------------------------- wiring
  // index.html's Send button and Enter key call the global sendPrompt(); route them to the tutor.
  window.sendPrompt = ask;
  textarea.maxLength = MAX_CHARS;

  loadAccount();
  refreshBackendStatus();
  setInterval(refreshBackendStatus, 30000);
})();
