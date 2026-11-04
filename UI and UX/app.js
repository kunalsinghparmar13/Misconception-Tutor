(function () {
  const textarea = document.querySelector('textarea');
  const sendButton = document.querySelector('button[aria-label="Send"]');
  const counter = document.querySelector('.text-outline');
  const subjectCards = {
    math: document.getElementById('tab-math'),
    python: document.getElementById('tab-python'),
  };
  let activeSubject = 'python';

  const response = document.createElement('section');
  response.id = 'llm-response';
  response.className =
    'hidden w-full max-w-3xl mx-auto mb-6 rounded-2xl bg-surface-container-lowest p-5 shadow-sm ring-1 ring-outline-variant/30';
  response.innerHTML =
    '<div class="flex items-center justify-between mb-3">' +
    '<span class="font-label-sm text-label-sm uppercase tracking-wider text-outline">Tutor response</span>' +
    '<span id="llm-model" class="font-label-sm text-label-sm text-outline"></span>' +
    '</div>' +
    '<pre id="llm-answer" class="whitespace-pre-wrap font-body-md text-body-md text-on-surface"></pre>' +
    '<div id="targeted-practice" class="mt-6"></div>';
  document.querySelector('main > div')?.prepend(response);

  async function refreshBackendStatus() {
    const modelLabel = document.querySelector('header > div:first-child > span:last-child');
    if (!modelLabel) return;
    try {
      const result = await fetch('/api/backend-status');
      if (!result.ok) return;
      const status = await result.json();
      modelLabel.textContent = status.model
        ? `Active Model: ${status.model}`
        : 'Active Model: Local Tutor';
    } catch (error) {
      console.warn('Unable to read backend status.', error);
    }
  }

  function setLoading(loading) {
    sendButton.disabled = loading;
    sendButton.classList.toggle('opacity-50', loading);
    sendButton.querySelector('.material-symbols-outlined').textContent = loading ? 'hourglass_top' : 'arrow_upward';
  }

  function showResponse(answer, model) {
    response.classList.remove('hidden');
    document.getElementById('llm-answer').textContent = answer;
    document.getElementById('llm-model').textContent = model || 'Local Gemma adapter';
    response.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  function renderPracticeSet(practiceSet) {
    const container = document.getElementById('targeted-practice');
    if (!container || !practiceSet?.questions?.length) return;
    container.replaceChildren();

    const title = document.createElement('h2');
    title.className = 'font-headline-md text-headline-md text-on-surface mb-1';
    title.textContent = `6 targeted ${practiceSet.subject} practice questions`;
    container.appendChild(title);

    const subtitle = document.createElement('p');
    subtitle.className = 'font-body-sm text-body-sm text-on-surface-variant mb-4';
    subtitle.textContent = `These questions focus on: ${practiceSet.misconception}. Submit each answer to measure improvement.`;
    container.appendChild(subtitle);

    const list = document.createElement('div');
    list.className = 'space-y-3';
    practiceSet.questions.forEach((question, index) => {
      const card = document.createElement('div');
      card.className = 'rounded-xl bg-surface-container-low p-4';

      const label = document.createElement('div');
      label.className = 'font-label-sm text-label-sm uppercase tracking-wider text-outline mb-2';
      label.textContent = `Practice ${index + 1}`;
      card.appendChild(label);

      const prompt = document.createElement('p');
      prompt.className = 'font-body-md text-body-md text-on-surface mb-2';
      prompt.textContent = question.prompt;
      card.appendChild(prompt);

      if (question.type === 'code') {
        const code = document.createElement('pre');
        code.className = 'whitespace-pre-wrap rounded-lg bg-surface-container-lowest p-3 font-code-block text-code-block text-on-surface mb-3 overflow-x-auto';
        code.textContent = question.code;
        card.appendChild(code);
      }

      const answer = document.createElement(question.type === 'code' ? 'textarea' : 'input');
      answer.className = 'w-full rounded-lg bg-surface-container-lowest px-3 py-2 font-code-block text-code-block text-on-surface ring-1 ring-outline-variant/50 focus:ring-2 focus:ring-primary';
      answer.placeholder = question.type === 'code' ? 'Paste your corrected Python code here...' : 'Type your answer, for example 5/12';
      if (question.type === 'code') {
        answer.rows = 4;
      } else {
        answer.type = 'text';
      }
      card.appendChild(answer);

      const actionRow = document.createElement('div');
      actionRow.className = 'mt-3 flex items-center gap-3';
      const submit = document.createElement('button');
      submit.className = 'rounded-full bg-primary px-4 py-2 font-label-md text-label-md text-on-primary';
      submit.textContent = 'Check answer';
      const result = document.createElement('span');
      result.className = 'font-body-sm text-body-sm text-on-surface-variant';
      submit.addEventListener('click', async () => {
        if (!answer.value.trim()) return;
        submit.disabled = true;
        try {
          const response = await fetch('/api/practice/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              learner_id: localStorage.getItem('learner_id') || 'student_demo',
              session_id: `practice_${Date.now()}`,
              practice_id: question.id,
              subject: question.subject,
              misconception: question.target_misconception,
              answer: answer.value,
              correct_answer: question.correct_answer,
              reference_code: question.code,
            }),
          });
          const payload = await response.json();
          if (!response.ok) throw new Error(payload.error || 'Unable to grade practice');
          result.textContent = payload.correct ? 'Correct — this misconception is getting weaker.' : 'Not yet — compare your answer with the solution below.';
          result.className = `font-body-sm text-body-sm ${payload.correct ? 'text-on-tertiary-container' : 'text-error'}`;
          const solution = document.createElement('div');
          solution.className = 'mt-3 rounded-lg bg-surface-container-lowest p-3 text-on-surface';
          const heading = document.createElement('p');
          heading.className = 'font-label-md text-label-md mb-2';
          heading.textContent = question.type === 'code' ? 'Correct code and explanation' : 'Correct answer and explanation';
          solution.appendChild(heading);
          if (question.type === 'code') {
            const correctCode = document.createElement('pre');
            correctCode.className = 'whitespace-pre-wrap overflow-x-auto font-code-block text-code-block mb-2';
            correctCode.textContent = payload.correct_code || question.correct_code || 'No reference solution available.';
            solution.appendChild(correctCode);
          } else {
            const correctAnswer = document.createElement('p');
            correctAnswer.className = 'font-body-md text-body-md mb-2';
            correctAnswer.textContent = `Answer: ${payload.correct_answer || question.correct_answer}`;
            solution.appendChild(correctAnswer);
          }
          const explanation = document.createElement('p');
          explanation.className = 'font-body-sm text-body-sm text-on-surface-variant';
          explanation.textContent = payload.explanation || question.explanation || 'Review the tutor response and apply the same correction.';
          solution.appendChild(explanation);
          card.appendChild(solution);
        } catch (error) {
          result.textContent = `Could not grade: ${error.message}`;
          result.className = 'font-body-sm text-body-sm text-error';
        } finally {
          submit.disabled = false;
        }
      });
      actionRow.appendChild(submit);
      actionRow.appendChild(result);
      card.appendChild(actionRow);
      list.appendChild(card);
    });
    container.appendChild(list);
  }

  function updateCounter() {
    const count = textarea.value.length;
    if (counter) counter.textContent = `${count} / 4000`;
  }

  textarea.addEventListener('input', updateCounter);
  Object.entries(subjectCards).forEach(([subject, card]) => {
    card?.addEventListener('click', () => {
      activeSubject = subject === 'math' ? 'Mathematics' : 'Python';
    });
  });

  sendButton.addEventListener('click', async () => {
    const question = textarea.value.trim();
    if (!question) {
      textarea.focus();
      return;
    }
    setLoading(true);
    try {
      const result = await fetch('/api/llm/answer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ subject: activeSubject, question, mode: 'diagnostic' }),
      });
      const payload = await result.json();
      if (!result.ok) throw new Error(payload.error || `Backend error (${result.status})`);
      showResponse(payload.answer, payload.model);
      renderPracticeSet(payload.practice_set);
    } catch (error) {
      showResponse(`Service unavailable: ${error.message}`, 'LLM backend');
    } finally {
      setLoading(false);
    }
  });

  textarea.addEventListener('keydown', (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
      event.preventDefault();
      sendButton.click();
    }
  });
  updateCounter();
  refreshBackendStatus();
})();
