import {
  Question,
  DiagnosisResult,
  LearnerProgress,
  TeacherInsights,
  Misconception,
} from '../types/education';
import {
  INITIAL_QUESTIONS,
  KNOWN_MISCONCEPTIONS,
  INITIAL_LEARNER_PROGRESS,
  INITIAL_TEACHER_INSIGHTS,
} from './mockData';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

const STORAGE_KEYS = {
  PROGRESS: 'ai_that_teaches_progress',
  HISTORY: 'ai_that_teaches_diagnosis_history',
  QUESTION_INDEX: 'ai_that_teaches_q_index',
};

// Helper to parse student answer string like "3/4", "5 / 6", "1.5", "2", "-1/3"
function parseFractionOrNumber(input: string): { num: number; den: number; value: number } | null {
  const clean = input.trim().replace(/\s+/g, '');
  if (!clean) return null;

  if (clean.includes('/')) {
    const parts = clean.split('/');
    if (parts.length === 2) {
      const num = Number(parts[0]);
      const den = Number(parts[1]);
      if (!isNaN(num) && !isNaN(den) && den !== 0) {
        return { num, den, value: num / den };
      }
    }
  }

  const numVal = Number(clean);
  if (!isNaN(numVal)) {
    return { num: numVal, den: 1, value: numVal };
  }

  return null;
}

// Simplify fraction helper
function gcd(a: number, b: number): number {
  return b === 0 ? Math.abs(a) : gcd(b, a % b);
}

function reduceFraction(num: number, den: number): { num: number; den: number; str: string } {
  if (den === 0) return { num, den, str: `${num}/${den}` };
  const divisor = gcd(num, den);
  const sNum = num / divisor;
  const sDen = den / divisor;
  return {
    num: sNum,
    den: sDen,
    str: sDen === 1 ? `${sNum}` : `${sNum}/${sDen}`,
  };
}

export const api = {
  isConfiguredWithExternalBackend(): boolean {
    return Boolean(API_BASE_URL && API_BASE_URL.trim().length > 0);
  },

  getBaseUrl(): string {
    return API_BASE_URL;
  },

  async fetchNextQuestion(topic?: string, difficulty?: string): Promise<Question> {
    if (this.isConfiguredWithExternalBackend()) {
      try {
        const query = new URLSearchParams();
        if (topic) query.set('topic', topic);
        if (difficulty) query.set('difficulty', difficulty);
        const res = await fetch(`${API_BASE_URL}/api/question/next?${query.toString()}`, { credentials: 'omit' });
        if (res.ok) {
          return await res.json();
        }
      } catch (err) {
        console.warn('External API call failed, falling back to local diagnostic engine:', err);
      }
    }

    // Local fallback generator/sequencer
    const storedIndex = Number(localStorage.getItem(STORAGE_KEYS.QUESTION_INDEX) || 0);
    const nextIndex = (storedIndex + 1) % INITIAL_QUESTIONS.length;
    localStorage.setItem(STORAGE_KEYS.QUESTION_INDEX, String(nextIndex));

    return INITIAL_QUESTIONS[storedIndex % INITIAL_QUESTIONS.length];
  },

  async submitAnswer(question: Question, rawAnswer: string): Promise<DiagnosisResult> {
    if (this.isConfiguredWithExternalBackend()) {
      try {
        const res = await fetch(`${API_BASE_URL}/api/diagnosis/evaluate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            question_id: question.id,
            answer: rawAnswer,
          }),
        });
        if (res.ok) {
          const data = await res.json();
          return data;
        }
      } catch (err) {
        console.warn('External submitAnswer API call failed, using local diagnostic engine:', err);
      }
    }

    // High-fidelity mathematical misconception diagnosis engine
    const parsedStudent = parseFractionOrNumber(rawAnswer);
    const parsedCorrect = parseFractionOrNumber(question.correctAnswer);

    const isMatch = Boolean(
      parsedStudent &&
      parsedCorrect &&
      Math.abs(parsedStudent.value - parsedCorrect.value) < 0.0001
    );

    let predictedMisconception: Misconception | null = null;
    let confidence = 0.95;
    let isLowConfidence = false;
    let explanation = '';
    let whyWeThinkThis: DiagnosisResult['whyWeThinkThis'] = null;
    let targetedQuestion: Question | null = null;

    if (isMatch) {
      explanation = 'Excellent work! Your answer is mathematically exact and properly simplified.';
      confidence = 1.0;
    } else if (!parsedStudent) {
      isLowConfidence = true;
      confidence = 0.25;
      explanation = "We couldn't parse your input as a valid fraction or number (e.g., 3/4 or 5).";
    } else {
      const { firstOperand, operator, secondOperand } = question.expression;
      const stNum = parsedStudent.num;
      const stDen = parsedStudent.den;

      // Misconception Rule 1: Adding tops and bottoms (1/2 + 1/3 => 2/5)
      if (operator === '+') {
        const directNum = firstOperand.num + secondOperand.num;
        const directDen = firstOperand.den + secondOperand.den;
        const reducedDirect = reduceFraction(directNum, directDen);
        const reducedStudent = reduceFraction(stNum, stDen);

        if (
          (stNum === directNum && stDen === directDen) ||
          reducedStudent.str === reducedDirect.str
        ) {
          predictedMisconception = KNOWN_MISCONCEPTIONS.ADD_NUMS_AND_DENS;
          confidence = 0.96;
          explanation = `You added the numerators (${firstOperand.num} + ${secondOperand.num} = ${directNum}) and the denominators (${firstOperand.den} + ${secondOperand.den} = ${directDen}) directly.`;
          whyWeThinkThis = {
            observedPattern: `Input ${rawAnswer} strictly equals (${firstOperand.num}+${secondOperand.num})/(${firstOperand.den}+${secondOperand.den}) = ${directNum}/${directDen}.`,
            studentMentalStep: 'Treated fraction components as independent integers instead of equal unit partitions.',
            underlyingGap: 'Denominator denotes the partition size, not an addable count. Slices must be converted to equal scale first.',
            counterExample: 'Consider 1/2 of a pie plus 1/2 of a pie: adding tops and bottoms gives 2/4 = 1/2 of a pie instead of 1 whole pie!',
          };
          targetedQuestion = {
            id: `targeted-${Date.now()}`,
            topic: 'fractions-addition',
            topicTitle: 'Targeted Practice: Converting to Shared Denominators',
            difficulty: 'Fundamental',
            prompt: 'Step-by-step recovery: Add these fractions after noticing the common denominator of 4:',
            expression: {
              firstOperand: { num: 1, den: 4 },
              operator: '+',
              secondOperand: { num: 2, den: 4 },
            },
            correctAnswer: '3/4',
            correctAnswerDecimal: 0.75,
            hint: 'Since both denominators are already 4, keep the denominator 4 and simply add the numerators 1 + 2.',
            conceptualContext: 'Re-anchoring common denominator addition rule.',
          };
        }
      }

      // Misconception Rule 2: Subtracting denominators directly
      if (!predictedMisconception && operator === '-') {
        const directNum = Math.abs(firstOperand.num - secondOperand.num);
        const directDen = Math.abs(firstOperand.den - secondOperand.den);
        if (directDen > 0 && stNum === directNum && stDen === directDen) {
          predictedMisconception = KNOWN_MISCONCEPTIONS.SUBTRACT_DENOMS_DIRECTLY;
          confidence = 0.94;
          explanation = `You subtracted the numerators (${firstOperand.num} - ${secondOperand.num}) and denominators (${firstOperand.den} - ${secondOperand.den}) directly.`;
          whyWeThinkThis = {
            observedPattern: `Result matched (${firstOperand.num}-${secondOperand.num})/(${firstOperand.den}-${secondOperand.den}).`,
            studentMentalStep: 'Subtracted bottom numbers without finding a common baseline.',
            underlyingGap: 'Denominators define the unit slice size and cannot be subtracted.',
            counterExample: '3/4 - 1/4 is 2/4. If we subtracted denominators, 4-4=0 which is undefined!',
          };
          targetedQuestion = {
            id: `targeted-${Date.now()}`,
            topic: 'fractions-subtraction',
            topicTitle: 'Targeted Practice: Subtracting Like Fractions',
            difficulty: 'Fundamental',
            prompt: 'Subtract these fractions with identical denominators:',
            expression: {
              firstOperand: { num: 5, den: 8 },
              operator: '-',
              secondOperand: { num: 2, den: 8 },
            },
            correctAnswer: '3/8',
            correctAnswerDecimal: 3 / 8,
            hint: 'The denominator stays 8. Only subtract the numerators 5 - 2.',
          };
        }
      }

      // Misconception Rule 3: Cross multiplying during fraction multiplication
      if (!predictedMisconception && operator === '×') {
        const crossNum = firstOperand.num * secondOperand.den;
        const crossDen = firstOperand.den * secondOperand.num;
        const reducedCross = reduceFraction(crossNum, crossDen);
        const reducedStudent = reduceFraction(stNum, stDen);

        if (reducedStudent.str === reducedCross.str) {
          predictedMisconception = KNOWN_MISCONCEPTIONS.MULTIPLY_CROSSWISE;
          confidence = 0.93;
          explanation = 'You cross-multiplied the terms instead of multiplying straight across.';
          whyWeThinkThis = {
            observedPattern: `Result produced ${crossNum}/${crossDen}, which corresponds to (${firstOperand.num}×${secondOperand.den})/(${firstOperand.den}×${secondOperand.num}).`,
            studentMentalStep: 'Cross-multiplication rule was misapplied from proportion solving.',
            underlyingGap: 'Fraction multiplication scales straight across: (numerator × numerator) / (denominator × denominator).',
            counterExample: 'Half of a half (1/2 × 1/2) is 1/4. Cross-multiplying would give (1×2)/(2×1) = 2/2 = 1.',
          };
          targetedQuestion = {
            id: `targeted-${Date.now()}`,
            topic: 'fractions-multiplication',
            topicTitle: 'Targeted Practice: Straight-Across Multiplication',
            difficulty: 'Fundamental',
            prompt: 'Multiply straight across (top × top, bottom × bottom):',
            expression: {
              firstOperand: { num: 1, den: 3 },
              operator: '×',
              secondOperand: { num: 2, den: 5 },
            },
            correctAnswer: '2/15',
            correctAnswerDecimal: 2 / 15,
            hint: 'Multiply 1 × 2 for the numerator, and 3 × 5 for the denominator.',
          };
        }
      }

      // Misconception Rule 4: Division without reciprocal
      if (!predictedMisconception && operator === '÷') {
        const directMultNum = firstOperand.num * secondOperand.num;
        const directMultDen = firstOperand.den * secondOperand.den;
        const reducedDirect = reduceFraction(directMultNum, directMultDen);
        const reducedStudent = reduceFraction(stNum, stDen);

        if (reducedStudent.str === reducedDirect.str) {
          predictedMisconception = KNOWN_MISCONCEPTIONS.FORGOT_RECIPROCAL_DIVISION;
          confidence = 0.92;
          explanation = 'You multiplied the fractions directly without inverting the divisor.';
          whyWeThinkThis = {
            observedPattern: `Result matched direct multiplication (${firstOperand.num}×${secondOperand.num})/(${firstOperand.den}×${secondOperand.den}).`,
            studentMentalStep: 'Forgot the "Keep-Change-Flip" transformation required for fraction division.',
            underlyingGap: 'Dividing by a fraction is equivalent to multiplying by its reciprocal.',
            counterExample: 'How many halves (1/2) fit into 2? The answer is 4. Direct multiplication would give 2/2 = 1.',
          };
          targetedQuestion = {
            id: `targeted-${Date.now()}`,
            topic: 'fractions-division',
            topicTitle: 'Targeted Practice: Keep, Change, Flip Reciprocal',
            difficulty: 'Intermediate',
            prompt: 'Apply the reciprocal rule: Flip 1/3 to 3/1 before multiplying:',
            expression: {
              firstOperand: { num: 2, den: 5 },
              operator: '÷',
              secondOperand: { num: 1, den: 3 },
            },
            correctAnswer: '6/5',
            correctAnswerDecimal: 1.2,
            hint: 'Rewrite as 2/5 × 3/1, then multiply straight across.',
          };
        }
      }

      // Low confidence fallback if no deterministic misconception matched
      if (!predictedMisconception) {
        isLowConfidence = true;
        confidence = 0.42; // Below 0.5 threshold
        explanation = "The submitted answer does not clearly match a known computational error pattern.";
        whyWeThinkThis = {
          observedPattern: `Result ${rawAnswer} does not align with typical misconception models for this operation.`,
          studentMentalStep: 'Possible calculation slip or multi-step mental arithmetic error.',
          underlyingGap: 'More observational evidence is needed before confirming the root cause.',
          counterExample: `The target correct result is ${question.correctAnswer}.`,
        };
        targetedQuestion = {
          id: `targeted-${Date.now()}`,
          topic: question.topic,
          topicTitle: 'Diagnostic Follow-up: Core Foundation Check',
          difficulty: 'Fundamental',
          prompt: 'Let us isolate the arithmetic step with this simplified problem:',
          expression: question.expression,
          correctAnswer: question.correctAnswer,
          correctAnswerDecimal: question.correctAnswerDecimal,
          hint: question.hint,
        };
      }
    }

    const diagnosis: DiagnosisResult = {
      questionId: question.id,
      originalQuestion: question,
      studentAnswer: rawAnswer,
      correctAnswer: question.correctAnswer,
      isCorrect: isMatch,
      misconception: predictedMisconception,
      confidence,
      isLowConfidence,
      explanation,
      whyWeThinkThis,
      targetedQuestion,
      timestamp: new Date().toISOString(),
    };

    // Update learner progress in localStorage
    this.recordDiagnosis(diagnosis);

    return diagnosis;
  },

  async fetchTargetedQuestion(misconceptionCode?: string): Promise<Question> {
    if (this.isConfiguredWithExternalBackend() && misconceptionCode) {
      try {
        const res = await fetch(`${API_BASE_URL}/api/question/targeted?code=${encodeURIComponent(misconceptionCode)}`);
        if (res.ok) {
          return await res.json();
        }
      } catch (err) {
        console.warn('External targeted question API failed, using local generator:', err);
      }
    }

    // Default targeted question addressing unlike denominator addition
    return {
      id: `targeted-${Date.now()}`,
      topic: 'fractions-addition',
      topicTitle: 'Targeted Intervention: Finding Equivalent Common Partitions',
      difficulty: 'Fundamental',
      prompt: 'Add these fractions by first converting 1/3 into sixths (2/6):',
      expression: {
        firstOperand: { num: 1, den: 6 },
        operator: '+',
        secondOperand: { num: 2, den: 6 },
      },
      correctAnswer: '3/6',
      correctAnswerDecimal: 0.5,
      hint: 'The denominators are both 6. Simply add 1 + 2 over 6, which reduces to 1/2.',
      conceptualContext: 'Validating partition invariance.',
    };
  },

  recordDiagnosis(diagnosis: DiagnosisResult) {
    const raw = localStorage.getItem(STORAGE_KEYS.PROGRESS);
    let progress: LearnerProgress = raw ? JSON.parse(raw) : INITIAL_LEARNER_PROGRESS;

    progress.totalAttempted += 1;
    if (diagnosis.isCorrect) {
      progress.totalCorrect += 1;
    }
    progress.accuracy = Math.round((progress.totalCorrect / progress.totalAttempted) * 100);

    // Update misconception bug rate
    if (diagnosis.misconception) {
      const code = diagnosis.misconception.code;
      const targetRate = progress.misconceptionBugRates.find((m) => m.code === code);
      if (targetRate) {
        targetRate.currentBugRate = Math.min(100, Math.round(targetRate.currentBugRate + (diagnosis.isCorrect ? -8 : 12)));
        if (targetRate.currentBugRate <= 15) {
          targetRate.status = 'Mastered';
          targetRate.trend = 'improving';
        } else if (targetRate.currentBugRate <= 40) {
          targetRate.status = 'Improving';
        } else {
          targetRate.status = 'Needs Practice';
        }
      }
    }

    localStorage.setItem(STORAGE_KEYS.PROGRESS, JSON.stringify(progress));

    // Store diagnosis in history
    const rawHistory = localStorage.getItem(STORAGE_KEYS.HISTORY);
    const history: DiagnosisResult[] = rawHistory ? JSON.parse(rawHistory) : [];
    history.unshift(diagnosis);
    localStorage.setItem(STORAGE_KEYS.HISTORY, JSON.stringify(history.slice(0, 20)));
  },

  async fetchLearnerProgress(): Promise<LearnerProgress> {
    if (this.isConfiguredWithExternalBackend()) {
      try {
        const res = await fetch(`${API_BASE_URL}/api/learner/progress`);
        if (res.ok) {
          return await res.json();
        }
      } catch (err) {
        console.warn('External learner progress API failed, using local progress store:', err);
      }
    }

    const raw = localStorage.getItem(STORAGE_KEYS.PROGRESS);
    if (raw) {
      try {
        return JSON.parse(raw);
      } catch {
        // fallback
      }
    }
    return INITIAL_LEARNER_PROGRESS;
  },

  async fetchTeacherInsights(): Promise<TeacherInsights> {
    if (this.isConfiguredWithExternalBackend()) {
      try {
        const res = await fetch(`${API_BASE_URL}/api/teacher/insights`);
        if (res.ok) {
          return await res.json();
        }
      } catch (err) {
        console.warn('External teacher insights API failed, using class data model:', err);
      }
    }

    return INITIAL_TEACHER_INSIGHTS;
  },

  async resetLearnerProgress(): Promise<boolean> {
    if (this.isConfiguredWithExternalBackend()) {
      try {
        await fetch(`${API_BASE_URL}/api/learner/reset`, { method: 'POST' });
      } catch (err) {
        console.warn('External reset API failed, resetting local store:', err);
      }
    }

    localStorage.removeItem(STORAGE_KEYS.PROGRESS);
    localStorage.removeItem(STORAGE_KEYS.HISTORY);
    localStorage.removeItem(STORAGE_KEYS.QUESTION_INDEX);
    return true;
  },
};
