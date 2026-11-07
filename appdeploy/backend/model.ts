// Client for the user's fine-tuned model on an OpenAI-compatible server
// (port of LLM/tutor_agents/model_client.py, remote mode only).
// LLM_BACKEND_URL and LLM_BACKEND_TOKEN are AppDeploy secrets; their values never leave the backend.

import { secrets } from '@appdeploy/sdk';

export const MODEL_NAME = 'misconception-tutor-gemma4-e4b (fine-tuned)';
const PUBLIC_MESSAGE = 'The tutor model is not reachable right now. Please try again in a minute.';
const RETRY_STATUS = new Set([502, 503, 504]);

/** Per-call budget. Each request runs one model call, so this stays below the platform's request limit. */
const CHAT_TIMEOUT_MS = 85000;

export class ModelUnavailable extends Error {
  readonly publicMessage = PUBLIC_MESSAGE;
}

export interface ChatMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

export interface ChatResult {
  text: string;
  model: string;
  seconds: number;
  backend: string;
}

interface ModelConfig {
  url: string | null;
  token: string | null;
}

async function readOptionalSecret(name: string, names: string[]): Promise<string | null> {
  if (!names.includes(name)) return null;
  try {
    const value = (await secrets.readSecret(name)).trim();
    return value || null;
  } catch {
    return null;
  }
}

async function config(): Promise<ModelConfig> {
  let names: string[] = [];
  try {
    names = await secrets.listSecretNames();
  } catch (e) {
    console.warn('could not list secrets', e instanceof Error ? e.message : 'unknown error');
  }
  const url = await readOptionalSecret('LLM_BACKEND_URL', names);
  const token = await readOptionalSecret('LLM_BACKEND_TOKEN', names);
  return { url: url ? url.replace(/\/+$/, '') : null, token };
}

function headers(token: string | null): Record<string, string> {
  // X-Keepalive: the user's model server trickles spaces while generating so tunnels don't time out.
  const h: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
    'X-Keepalive': '1',
  };
  if (token) h.Authorization = `Bearer ${token}`;
  return h;
}

type FetchInit = NonNullable<Parameters<typeof fetch>[1]>;
type FetchResponse = Awaited<ReturnType<typeof fetch>>;

async function fetchWithTimeout(url: string, init: FetchInit, ms: number): Promise<FetchResponse> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ms);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export interface Health {
  configured: boolean;
  reachable: boolean;
  mode: string;
  model?: string;
  modelLoaded?: boolean;
  error?: string;
}

/** Cheap readiness probe of the model server. Never includes the server address. */
export async function health(): Promise<Health> {
  const cfg = await config();
  if (!cfg.url) {
    return {
      configured: false,
      reachable: false,
      mode: 'none',
      error: 'No model configured. Set the LLM_BACKEND_URL secret to your model server.',
    };
  }
  let last = 'no response';
  for (const path of ['/health', '/api/health', '/api/ready', '/v1/models']) {
    try {
      const res = await fetchWithTimeout(`${cfg.url}${path}`, { headers: headers(cfg.token) }, 4000);
      if (res.status === 200) {
        let info: Record<string, unknown> = {};
        try {
          info = (await res.json()) as Record<string, unknown>;
        } catch {
          info = {};
        }
        return {
          configured: true,
          reachable: true,
          mode: 'remote',
          model: typeof info.model === 'string' ? info.model : MODEL_NAME,
          modelLoaded: info.model_loaded === undefined ? true : Boolean(info.model_loaded),
        };
      }
      last = `HTTP ${res.status} from ${path}`;
    } catch {
      last = 'no response';
    }
  }
  return { configured: true, reachable: false, mode: 'remote', error: `Model server not reachable (${last}).` };
}

export async function chat(messages: ChatMessage[], maxTokens = 512, temperature = 0.2): Promise<ChatResult> {
  const started = Date.now();
  const cfg = await config();
  if (!cfg.url) throw new ModelUnavailable('No model configured (LLM_BACKEND_URL secret missing).');
  const payload = JSON.stringify({
    model: MODEL_NAME,
    messages,
    max_tokens: Math.trunc(maxTokens),
    temperature,
    stream: false,
  });
  let lastError = 'unknown error';
  for (let attempt = 0; attempt < 2; attempt++) {
    const remaining = CHAT_TIMEOUT_MS - (Date.now() - started);
    if (remaining < 5000) break;
    let res: FetchResponse;
    try {
      res = await fetchWithTimeout(`${cfg.url}/v1/chat/completions`, { method: 'POST', headers: headers(cfg.token), body: payload }, remaining);
    } catch (e) {
      lastError = e instanceof Error ? `${e.name}: ${e.message}` : 'network error';
      await sleep(1500);
      continue;
    }
    const raw = await res.text();
    if (res.status === 200) {
      let body: unknown;
      try {
        body = JSON.parse(raw);
      } catch {
        throw new ModelUnavailable('Unexpected (non-JSON) response from model server.');
      }
      const obj = body as { error?: unknown; choices?: Array<{ message?: { content?: string } }> };
      if (obj && obj.error) {
        lastError = String(obj.error).slice(0, 200);
        break;
      }
      const text = (obj?.choices?.[0]?.message?.content || '').trim();
      if (!text) throw new ModelUnavailable('The model returned an empty response.');
      return { text, model: MODEL_NAME, seconds: (Date.now() - started) / 1000, backend: 'remote' };
    }
    lastError = `HTTP ${res.status}: ${raw.slice(0, 200)}`;
    if (RETRY_STATUS.has(res.status) && attempt === 0) {
      await sleep(2000);
      continue;
    }
    break;
  }
  console.warn('model server failed:', lastError);
  throw new ModelUnavailable(`Model server failed (${lastError}).`);
}
