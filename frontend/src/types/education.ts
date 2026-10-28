export type Difficulty = 'Fundamental' | 'Intermediate' | 'Advanced';

export type QuestionTopic = 'fractions-addition' | 'fractions-subtraction' | 'fractions-multiplication' | 'fractions-division' | 'mixed-operations';

export interface Question {
  id: string;
  topic: QuestionTopic;
  topicTitle: string;
  difficulty: Difficulty;
  prompt: string;
  expression: {
    firstOperand: { num: number; den: number };
    operator: '+' | '-' | '×' | '÷';
    secondOperand: { num: number; den: number };
  };
  correctAnswer: string;
  correctAnswerDecimal: number;
  hint?: string;
  conceptualContext?: string;
}

export interface Misconception {
  id: string;
  code: string;
  subjectId?: string;
  title: string;
  friendlyDescription: string;
  explanation: string;
  severity: 'low' | 'medium' | 'high';
  remedyStrategy: string;
  examplePattern: string;
}

export interface DiagnosisResult {
  questionId: string;
  originalQuestion: Question;
  studentAnswer: string;
  correctAnswer: string;
  isCorrect: boolean;
  misconception: Misconception | null;
  confidence: number; // 0.0 to 1.0
  isLowConfidence: boolean;
  explanation: string;
  whyWeThinkThis: {
    observedPattern: string;
    studentMentalStep: string;
    underlyingGap: string;
    counterExample: string;
  } | null;
  targetedQuestion: Question | null;
  timestamp: string;
}

export interface LearnerSession {
  id: string;
  date: string;
  questionsAttempted: number;
  correctAnswers: number;
  accuracy: number;
  topMisconceptions: string[];
}

export interface MisconceptionBugRate {
  misconceptionId: string;
  code: string;
  name: string;
  category: string;
  historicalRates: { session: string; bugRate: number }[];
  currentBugRate: number; // percentage 0-100
  trend: 'improving' | 'stable' | 'regressing';
  status: 'Mastered' | 'Improving' | 'Needs Practice';
}

export interface LearnerProgress {
  totalAttempted: number;
  totalCorrect: number;
  accuracy: number;
  activeStreakDays: number;
  recentSessions: LearnerSession[];
  misconceptionBugRates: MisconceptionBugRate[];
  focusAreas: {
    misconceptionId: string;
    title: string;
    recommendedPracticeTopic: string;
    priority: 'high' | 'medium' | 'low';
  }[];
}

export interface TeacherLearnerData {
  anonymousId: string;
  gradeLevel: string;
  questionsAttempted: number;
  accuracy: number;
  activeMisconceptions: Record<string, number>; // misconceptionCode -> error rate 0-100
  lastActive: string;
}

export interface TeacherInsights {
  classSize: number;
  activeSessionName: string;
  averageAccuracy: number;
  mostPrevalentMisconception: string;
  learners: TeacherLearnerData[];
  misconceptionColumns: { code: string; title: string; category: string }[];
  cohortRecommendations: string[];
}
