/* Sikora AI - Supabase sign-in shared by index.html and login.html.
 *
 * Needs (loaded before this file):
 *   https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.118.0/dist/umd/supabase.js
 *   /config.js   -> window.SUPABASE_CONFIG = { url, key }  (public project URL + publishable key)
 *
 * Exposes window.tutorAuth with the client, session helpers, an authenticated fetch for the Flask API,
 * and small helpers that save the learner's work to Supabase (rows are private to their owner).
 */
(function () {
  'use strict';

  const cfg = window.SUPABASE_CONFIG || {};
  if (!window.supabase || !cfg.url || !cfg.key) {
    console.error('Supabase is not configured: check /config.js and the supabase-js script tag.');
    return;
  }

  const client = window.supabase.createClient(cfg.url, cfg.key, {
    auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true },
  });

  const onLoginPage = () => location.pathname === '/login';

  async function session() {
    const { data } = await client.auth.getSession();
    return data.session || null;
  }

  /** The signed-in user; sends everyone else to the login page. */
  async function requireUser() {
    const s = await session();
    if (!s) {
      location.replace('/login?next=' + encodeURIComponent(location.pathname + location.search));
      return new Promise(() => {}); // the page is navigating away
    }
    return s.user;
  }

  /** fetch() for the Flask API with the user's access token; a 401 means the session ended. */
  async function apiFetch(url, options = {}) {
    const s = await session();
    const headers = new Headers(options.headers || {});
    if (s) headers.set('Authorization', 'Bearer ' + s.access_token);
    const res = await fetch(url, { ...options, headers });
    if (res.status === 401 && !onLoginPage()) {
      location.replace('/login?expired=1');
    }
    return res;
  }

  async function signOut() {
    await client.auth.signOut();
    location.replace('/login');
  }

  async function profile(user) {
    const { data } = await client.from('profiles').select('full_name').eq('id', user.id).maybeSingle();
    const meta = user.user_metadata || {};
    return { name: (data && data.full_name) || meta.full_name || user.email.split('@')[0], email: user.email };
  }

  // ---- saving the learner's work -------------------------------------------------------
  async function saveSession(entry) {
    const { data, error } = await client.from('tutor_sessions').insert({
      question: entry.question,
      subject: entry.subject,
      misconception: entry.misconception || null,
      result: entry.result || null,
      sample_id: entry.sample_id || null,
    }).select('id').single();
    if (error) {
      console.warn('Could not save this question:', error.message);
      return null;
    }
    return data.id;
  }

  async function recentSessions(limit = 8) {
    const { data, error } = await client.from('tutor_sessions')
      .select('id, question, subject, created_at').order('created_at', { ascending: false }).limit(limit);
    if (error) {
      console.warn('Could not load past questions:', error.message);
      return [];
    }
    return data || [];
  }

  async function savePracticeAttempt(attempt) {
    const { error } = await client.from('practice_attempts').insert({
      session_id: attempt.session_id || null,
      practice_id: attempt.practice_id,
      set_id: attempt.set_id || null,
      misconception: attempt.misconception || null,
      answer: (attempt.answer || '').slice(0, 4000),
      correct: Boolean(attempt.correct),
    });
    if (error) console.warn('Could not save this practice answer:', error.message);
  }

  async function saveFeedback(sessionId, rating) {
    const { error } = await client.from('feedback').insert({ session_id: sessionId || null, rating });
    if (error) console.warn('Could not save feedback:', error.message);
  }

  client.auth.onAuthStateChange((event) => {
    if (event === 'SIGNED_OUT' && !onLoginPage()) location.replace('/login');
  });

  window.tutorAuth = {
    client, session, requireUser, apiFetch, signOut, profile,
    saveSession, recentSessions, savePracticeAttempt, saveFeedback,
  };
})();
