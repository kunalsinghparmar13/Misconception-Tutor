import express from 'express';
import path from 'path';
import { GoogleGenAI } from '@google/genai';
import dotenv from 'dotenv';

dotenv.config();

const app = express();
const PORT = 3000;

app.use(express.json({ limit: '10mb' }));

// Initialize GoogleGenAI SDK on server-side only
const apiKey = process.env.GEMINI_API_KEY || '';
let aiClient: GoogleGenAI | null = null;

if (apiKey) {
  aiClient = new GoogleGenAI({
    apiKey,
    httpOptions: {
      headers: {
        'User-Agent': 'aistudio-build',
      },
    },
  });
}

// 1. Health & Backend Capabilities Status
app.get('/api/backend-status', (req, res) => {
  res.json({
    status: 'online',
    hasApiKey: Boolean(apiKey),
    liveAiEnabled: Boolean(aiClient),
    model: 'gemini-3.8-flash',
    supportedSubjects: [
      'mathematics',
      'programming',
      'physics',
      'chemistry',
      'biology',
      'english',
      'history',
      'geography',
      'economics',
      'civics',
      'environmental',
      'custom',
    ],
    timestamp: new Date().toISOString(),
  });
});

// 2. Universal AI Doubt Solver Endpoint
app.post('/api/ai/doubt', async (req, res) => {
  const {
    subject,
    question,
    codeSnippet,
    mode, // 'normal' | 'simpler' | 'deeper' | 'step-by-step' | 'analogy' | 'code-debug' | 'summary'
    history, // array of { role: 'user' | 'assistant', content: string }
  } = req.body;

  if (!question || typeof question !== 'string') {
    return res.status(400).json({ error: 'Question text is required' });
  }

  if (!aiClient) {
    return res.status(503).json({
      error: 'Gemini AI service is not initialized on the server. Please verify your GEMINI_API_KEY in Settings.',
      fallback: true,
    });
  }

  try {
    let modeInstruction = '';
    switch (mode) {
      case 'simpler':
        modeInstruction = 'Explain in very simple, intuitive language suitable for a beginner. Use a clear analogy.';
        break;
      case 'deeper':
        modeInstruction = 'Provide an in-depth, rigorous, first-principles explanation with formal terminology, derivations, or advanced nuances.';
        break;
      case 'step-by-step':
        modeInstruction = 'Break the answer down into numbered, logical steps. Show every intermediate reasoning step clearly.';
        break;
      case 'analogy':
        modeInstruction = 'Center the explanation around an intuitive real-world analogy before connecting it back to the academic concept.';
        break;
      case 'code-debug':
        modeInstruction = 'Carefully inspect the provided code snippet. Pinpoint the exact line of the bug, explain why it fails, and provide the corrected code block with an explanation.';
        break;
      case 'summary':
        modeInstruction = 'Provide a concise executive summary followed by key bullet-point takeaways and formula/rule reminders.';
        break;
      default:
        modeInstruction = 'Provide a clear, pedagogical answer tailored to the subject with examples and step-by-step reasoning where suitable.';
    }

    const systemInstruction = `You are an elite, patient, pedagogical AI Tutor for an all-subject learning platform.
Current Subject: ${subject || 'General Knowledge'}.
Pedagogical Directives:
- Address the user's specific query directly and warmly.
- ${modeInstruction}
- For Mathematics/Physics/Chemistry: Show formulas, step-by-step numerical calculations, and units clearly.
- For Programming/CS: Format code in markdown with syntax highlighting, explain time/space complexity when relevant, and explain why errors occur.
- For History/Civics: Distinguish established historical facts from historical interpretations; explain cause-and-effect relationships and chronological timelines.
- For English/Languages: Provide sentence examples, grammar rules, and vocabulary in context.
- Format your response with clear markdown headings (##, ###), bullet points, and code blocks where appropriate.
- Conclude with a brief "Key Takeaway" and one helpful follow-up question to test the student's understanding.`;

    const contents: any[] = [];

    // Include previous dialogue turns if available for context preservation
    if (Array.isArray(history) && history.length > 0) {
      for (const turn of history.slice(-6)) {
        contents.push({
          role: turn.role === 'assistant' ? 'model' : 'user',
          parts: [{ text: turn.content }],
        });
      }
    }

    let currentPrompt = `Subject: ${subject || 'Universal'}\n\nQuestion: ${question}`;
    if (codeSnippet) {
      currentPrompt += `\n\nCode Snippet:\n\`\`\`\n${codeSnippet}\n\`\`\``;
    }

    contents.push({
      role: 'user',
      parts: [{ text: currentPrompt }],
    });

    const response = await aiClient.models.generateContent({
      model: 'gemini-3.8-flash',
      contents,
      config: {
        systemInstruction,
        temperature: 0.7,
      },
    });

    const text = response.text || '';
    res.json({
      answer: text,
      subject: subject || 'General',
      mode: mode || 'normal',
      timestamp: new Date().toISOString(),
    });
  } catch (error: any) {
    console.error('Error in /api/ai/doubt:', error);
    res.status(500).json({
      error: error.message || 'Failed to generate explanation from AI model',
    });
  }
});

// 3. Universal Answer Evaluation Endpoint
app.post('/api/ai/evaluate-answer', async (req, res) => {
  const { question, studentAnswer, subject } = req.body;

  if (!question || !studentAnswer) {
    return res.status(400).json({ error: 'Question and studentAnswer are required' });
  }

  if (!aiClient) {
    return res.status(503).json({
      error: 'Gemini AI service unavailable on server',
      fallback: true,
    });
  }

  try {
    const prompt = `Evaluate the student's answer to the following academic question.
Subject: ${subject || 'General'}
Question: ${typeof question === 'string' ? question : JSON.stringify(question)}
Student Answer: ${studentAnswer}

Provide evaluation in structured JSON format with:
- isCorrect: boolean (true if mathematically/conceptually sound, false if contains significant error)
- scoreOutOf10: number
- feedback: string (concise encouraging feedback)
- stepByStepSolution: string[] (correct reasoning steps)
- identifiedMisconception: string (name of mental gap or error, or empty if correct)
- commonPitfall: string (pitfall students often hit on this problem)`;

    const response = await aiClient.models.generateContent({
      model: 'gemini-3.8-flash',
      contents: prompt,
      config: {
        responseMimeType: 'application/json',
        temperature: 0.2,
      },
    });

    const jsonStr = response.text || '{}';
    let data = {};
    try {
      data = JSON.parse(jsonStr);
    } catch {
      data = { isCorrect: true, feedback: jsonStr, scoreOutOf10: 10 };
    }

    res.json(data);
  } catch (error: any) {
    console.error('Error in /api/ai/evaluate-answer:', error);
    res.status(500).json({ error: error.message || 'Failed to evaluate answer' });
  }
});

// 4. Dynamic Practice Question Generator Endpoint
app.post('/api/ai/generate-practice', async (req, res) => {
  const { subject, topic, difficulty } = req.body;

  if (!aiClient) {
    return res.status(503).json({ error: 'AI client not initialized on server' });
  }

  try {
    const prompt = `Generate 1 fresh, high-quality educational practice problem for:
Subject: ${subject || 'Mathematics'}
Topic: ${topic || 'Core Concepts'}
Difficulty: ${difficulty || 'medium'}

Return ONLY a valid JSON object matching this schema:
{
  "prompt": "The question prompt",
  "format": "multiple-choice",
  "difficulty": "${difficulty || 'medium'}",
  "codeSnippet": "optional code snippet if programming",
  "options": [
    {"id": "a", "text": "Option text", "isCorrect": false, "explanation": "Why this is wrong"},
    {"id": "b", "text": "Option text", "isCorrect": true, "explanation": "Why this is correct"},
    {"id": "c", "text": "Option text", "isCorrect": false, "explanation": "Why this is wrong"},
    {"id": "d", "text": "Option text", "isCorrect": false, "explanation": "Why this is wrong"}
  ],
  "correctAnswer": "The correct option text",
  "stepByStepSolution": ["Step 1...", "Step 2..."],
  "explanation": "Clear explanation of the concept",
  "commonPitfalls": "Common mistake to avoid",
  "hint": "Helpful nudge without giving away the answer",
  "followUpQuestion": "A related thought-provoking question"
}`;

    const response = await aiClient.models.generateContent({
      model: 'gemini-3.8-flash',
      contents: prompt,
      config: {
        responseMimeType: 'application/json',
        temperature: 0.7,
      },
    });

    const jsonStr = response.text || '{}';
    const qData = JSON.parse(jsonStr);
    res.json({
      ...qData,
      id: `ai-gen-${Date.now()}`,
      subjectId: (subject || 'math').toLowerCase().replace(/\s+/g, '-'),
      topicId: (topic || 'general').toLowerCase().replace(/\s+/g, '-'),
      topicTitle: topic || 'Custom Practice',
    });
  } catch (error: any) {
    console.error('Error generating practice question:', error);
    res.status(500).json({ error: error.message || 'Failed to generate question' });
  }
});

// Development vs Production static/Vite mounting
async function startServer() {
  const isDev = process.env.NODE_ENV !== 'production';

  if (isDev) {
    const { createServer } = await import('vite');
    const vite = await createServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.resolve('dist');
    app.use(express.static(distPath));
    app.get('*', (req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`Server listening on port ${PORT} (devMode: ${isDev})`);
  });
}

startServer().catch((err) => {
  console.error('Failed to start server:', err);
  process.exit(1);
});
