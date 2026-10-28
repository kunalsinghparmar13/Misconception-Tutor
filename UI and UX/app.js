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
    '<pre id="llm-answer" class="whitespace-pre-wrap font-body-md text-body-md text-on-surface"></pre>';
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
