const el = id => document.getElementById(id);
const messages = el('messages');
const field = el('message');
const status = el('state');
const synth = window.speechSynthesis;
const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const viewer = document.querySelector('model-viewer');
let voice = Boolean(synth);
let listening = null;
let speaking = null;
let pending = false;
let puzzle = false;
const history = [];

viewer.addEventListener('load', () => viewer.parentElement.classList.add('loaded'));
viewer.addEventListener('error', () => viewer.parentElement.classList.remove('loaded'));

// Small camera offsets make the character turn towards the mouse.
const neutralOrbit = viewer.getAttribute('camera-orbit');
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
let followFrame = 0;
let following = false;

function restCamera() {
  cancelAnimationFrame(followFrame);
  followFrame = 0;
  if (following) viewer.cameraOrbit = neutralOrbit;
  following = false;
}

document.addEventListener('pointermove', event => {
  if (event.pointerType !== 'mouse' || event.buttons || reducedMotion.matches) return;
  cancelAnimationFrame(followFrame);
  followFrame = requestAnimationFrame(() => {
    const box = viewer.getBoundingClientRect();
    if (!box.width || !box.height || !viewer.loaded) return;
    const x = (event.clientX - box.left - box.width / 2) / (box.width / 2);
    const y = (event.clientY - box.top - box.height / 2) / (box.height / 2);
    const yaw = -22 * Math.tanh(x);
    const pitch = 86 - 9 * Math.tanh(y);
    viewer.cameraOrbit = yaw.toFixed(2) + 'deg ' + pitch.toFixed(2) + 'deg 1.92m';
    following = true;
  });
}, {passive: true});
viewer.addEventListener('pointerdown', () => {
  cancelAnimationFrame(followFrame);
  following = false;
});
document.documentElement.addEventListener('pointerleave', restCamera);
window.addEventListener('blur', restCamera);
reducedMotion.addEventListener('change', restCamera);

function update() {
  status.textContent = pending ? 'Thinking…' : listening ? 'Listening…' : speaking ? 'Humo is speaking' : 'Ready to chat';
  el('sound').textContent = voice ? 'Voice on' : 'Voice off';
  el('sound').setAttribute('aria-pressed', String(voice));
  el('mic').textContent = listening ? '■ Finish recording' : '◉ Microphone';
  el('mic').disabled = pending || !Recognition;
  el('send').disabled = pending;
  for (const button of document.querySelectorAll('[data-start]')) button.disabled = pending;
}

function silence() {
  speaking = null;
  synth?.cancel();
}
function speak(text) {
  silence();
  if (voice) {
    const speech = new SpeechSynthesisUtterance(text);
    speaking = speech;
    speech.lang = el('lang').value;
    speech.onend = speech.onerror = () => {
      if (speaking === speech) { speaking = null; update(); }
    };
    synth.speak(speech);
  }
  update();
}

function add(who, text) {
  const entry = document.createElement('article');
  const label = document.createElement('b');
  const body = document.createElement('p');
  entry.classList.toggle('user', who === 'You');
  label.textContent = who;
  body.textContent = text;
  entry.append(label, body);
  messages.append(entry);
  messages.scrollTop = messages.scrollHeight;
  history.push(who + ': ' + text);
}
function guided(text) {
  const hi = el('lang').value === 'hi-IN';
  if (/puzzle|पहेली/i.test(text)) {
    puzzle = true;
    return hi ? 'तीन डिब्बों में चार-चार पेंसिल हैं। कुल कितनी पेंसिल हैं?' : 'Three boxes each hold four pencils. How many pencils are there altogether?';
  }
  if (puzzle) {
    if (/\b12\b|twelve|बारह|१२/i.test(text)) {
      puzzle = false;
      return hi ? 'सही! तीन बार चार जोड़ने पर बारह होते हैं।' : 'Exactly! Four plus four plus four makes twelve.';
    }
    return hi ? 'चार से शुरू करो। फिर चार दो बार और जोड़ो। कितना हुआ?' : 'Start with four. Add another four for each of the other two boxes. What do you get?';
  }
  if (/study|पढ़/i.test(text)) return hi ? 'कोई सवाल और अपनी पहली कोशिश बताओ। किस कदम पर अटके?' : 'Tell me your study question and the first step you tried. Where did you get stuck?';
  if (/^(hi|hey|hello|नमस्ते)\b/i.test(text)) return hi ? 'नमस्ते! एक छोटी पहेली आज़माएँ?' : 'Hey! Want to try a quick puzzle with me?';
  return hi ? 'अभी मेरा लाइव ट्यूटर उपलब्ध नहीं है। हम एक छोटी पहेली खेल सकते हैं।' : 'My live tutor is unavailable right now. We can still work through the quick puzzle together.';
}

async function send(text) {
  text = text.trim();
  if (!text || pending) return;
  listening?.abort();
  silence();
  const context = history.slice(-4).join('\n').slice(-1500);
  add('You', text);
  field.value = '';
  pending = true;
  el('notice').textContent = '';
  update();
  let reply;
  try {
    const request = window.tutorAuth?.apiFetch || window.fetch.bind(window);
    const response = await request('/api/llm/answer', {
      method:'POST', headers:{'Content-Type':'application/json'},
      signal:AbortSignal.timeout(30000),
      body:JSON.stringify({question: context ? context + '\nCurrent question: ' + text : text,
        subject:/python|code/i.test(text) ? 'Python' : 'Mathematics', language:el('lang').value.split('-')[0]})
    });
    const data = await response.json();
    if (!response.ok && !data.answer) throw new Error();
    reply = data.answer || data.agents?.explainer?.text || data.agents?.explainer?.sections?.correct_thinking;
    if (typeof reply !== 'string' || !reply.trim()) throw new Error();
    puzzle = false;
  } catch {
    reply = guided(text);
    el('notice').textContent = 'Guided demo · Live tutor unavailable';
  }
  pending = false;
  add('Humo', reply);
  speak(reply);
}
document.querySelector('form').onsubmit = event => { event.preventDefault(); send(field.value); };
document.querySelectorAll('[data-start]').forEach(button => button.onclick = () => send(button.dataset.start));
el('sound').disabled = !synth;
el('sound').onclick = () => { voice = !voice; if (!voice) silence(); update(); };
el('mic').onclick = () => {
  if (listening) { listening.stop(); return; }
  silence();
  const session = new Recognition();
  session.lang = el('lang').value;
  session.onresult = event => {
    const text = event.results[0][0].transcript;
    listening = null;
    send(text);
  };
  session.onerror = event => {
    if (event.error !== 'aborted') el('notice').textContent = 'Microphone unavailable. Type your message or check browser microphone access.';
  };
  session.onend = () => { if (listening === session) listening = null; update(); };
  try { session.start(); listening = session; } catch { el('notice').textContent = 'Could not start the microphone. You can type below.'; }
  update();
};
if (!Recognition) el('notice').textContent = 'Voice input is unavailable in this browser. You can type a message.';
window.addEventListener('pagehide', () => { listening?.abort(); silence(); });
update();
