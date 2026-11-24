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
const history = [];   // {role:'user'|'assistant', content} turns sent back so Humo remembers the problem

viewer.addEventListener('load', () => viewer.parentElement.classList.add('loaded'));
viewer.addEventListener('error', () => viewer.parentElement.classList.remove('loaded'));

function update() {
  status.textContent = pending ? 'Thinking and checking…' : listening ? 'Listening…' : speaking ? 'Humo is speaking' : 'Ready to chat';
  el('sound').textContent = voice ? 'Voice on' : 'Voice off';
  el('sound').setAttribute('aria-pressed', String(voice));
  el('mic').textContent = listening ? '■ Finish recording' : '◉ Microphone';
  el('mic').disabled = pending || !Recognition;
  el('send').disabled = pending;
  for (const button of document.querySelectorAll('[data-start]')) button.disabled = pending;
}

// The model carries two looping ActorCore mocap clips: "Idle" (5.7 s) and "Talk" ("Stand Talk", 28 s, plus lip shapes).
function talk(on) {
  if (!viewer.availableAnimations?.includes('Talk')) return;
  const name = on ? 'Talk' : 'Idle';
  if (viewer.animationName === name) return;
  viewer.animationName = name;
  viewer.play();
  // Start the long talk clip at a random point so each reply shows different gestures.
  if (on) requestAnimationFrame(() => { viewer.currentTime = Math.random() * Math.max(0, viewer.duration - 6); });
}

// Speech starts the moment Humo's reply arrives:
// - voices are loaded up front and the engine is woken on the learner's first click, so nothing loads on demand;
// - cancel() runs only when something is actually playing (Chrome delays or drops speech queued right after it);
// - the reply is spoken sentence by sentence, so the first sentence starts sooner and long replies never stall;
// - the talking animation starts together with the speech request instead of waiting for the engine's start event.
let voices = [];
function loadVoices() { voices = synth?.getVoices() || []; }
if (synth) { loadVoices(); synth.addEventListener?.('voiceschanged', loadVoices); }
function pickVoice(lang) {
  const base = lang.split('-')[0];
  return voices.find(v => v.lang === lang) || voices.find(v => v.lang?.startsWith(base)) || null;
}
let warmed = false;
function warmUp() {
  if (warmed || !synth || !voice) return;
  warmed = true;
  const wake = new SpeechSynthesisUtterance(' ');
  wake.volume = 0;
  synth.speak(wake);
}
function sentences(text) {
  return (text.match(/[^.!?।]+[.!?।]*/g) || [text]).map(part => part.trim()).filter(Boolean);
}

function silence() {
  speaking = null;
  if (synth && (synth.speaking || synth.pending)) synth.cancel();
  talk(false);
}
function speak(text) {
  silence();
  if (!voice || !synth) { update(); return; }
  const turn = {};
  speaking = turn;
  const lang = el('lang').value;
  const chosen = pickVoice(lang);
  const done = () => { if (speaking === turn) { speaking = null; talk(false); update(); } };
  const parts = sentences(text);
  parts.forEach((part, i) => {
    const speech = new SpeechSynthesisUtterance(part);
    speech.lang = lang;
    if (chosen) speech.voice = chosen;
    if (i === parts.length - 1) speech.onend = done;
    speech.onerror = event => { if (event.error !== 'interrupted' && event.error !== 'canceled') done(); };
    synth.speak(speech);
  });
  talk(true);
  update();
}

function add(who, text, note) {
  const entry = document.createElement('article');
  const label = document.createElement('b');
  const body = document.createElement('p');
  entry.classList.toggle('user', who === 'You');
  label.textContent = who;
  body.textContent = text;
  entry.append(label, body);
  if (note) {
    const tag = document.createElement('small');
    tag.className = 'reviewed';
    tag.textContent = note;
    entry.append(tag);
  }
  messages.append(entry);
  messages.scrollTop = messages.scrollHeight;
  history.push({role: who === 'You' ? 'user' : 'assistant', content: text});
}

// What the reviewer did with Humo's draft, shown under the reply.
function reviewNote(review) {
  if (!review) return '';
  if (review.verdict === 'PASS') return '✓ Checked by reviewer';
  if (review.verdict === 'REVISED') return '✓ Improved by reviewer';
  if (review.verdict === 'FALLBACK') return '✓ Reviewer kept the answer hidden';
  return '';
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
  const past = history.slice(-10);
  add('You', text);
  field.value = '';
  pending = true;
  el('notice').textContent = '';
  update();
  let reply, note = '';
  try {
    const request = window.tutorAuth?.apiFetch || window.fetch.bind(window);
    // Humo only gives hints and guiding questions; the server's reviewer checks every reply before it is spoken.
    const response = await request('/api/humex/chat', {
      method:'POST', headers:{'Content-Type':'application/json'},
      signal:AbortSignal.timeout(60000),
      body:JSON.stringify({message:text, history:past, language:el('lang').value.split('-')[0],
        subject:/python|code|error|def |print\(/i.test(text) ? 'Python' : ''})
    });
    const data = await response.json();
    if (!response.ok || typeof data.reply !== 'string' || !data.reply.trim()) throw new Error();
    reply = data.reply;
    note = reviewNote(data.review);
    puzzle = false;
  } catch {
    reply = guided(text);
    el('notice').textContent = 'Guided demo · Live tutor unavailable';
  }
  pending = false;
  add('Humo', reply, note);
  speak(reply);
}
document.querySelector('form').onsubmit = event => { event.preventDefault(); warmUp(); send(field.value); };
document.querySelectorAll('[data-start]').forEach(button => button.onclick = () => { warmUp(); send(button.dataset.start); });
el('sound').disabled = !synth;
el('sound').onclick = () => { voice = !voice; if (!voice) silence(); update(); };
el('mic').onclick = () => {
  warmUp();
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

// Ask the Humex backend whether Humo's model is connected, so learners know if they get the live tutor or the demo.
fetch('/api/humex/health', {signal: AbortSignal.timeout(10000)})
  .then(response => response.json())
  .then(health => {
    if (!health.ready && !el('notice').textContent) el('notice').textContent = 'Guided demo · Humo’s model is offline right now';
  })
  .catch(() => {});
window.addEventListener('pagehide', () => { listening?.abort(); silence(); });
update();
