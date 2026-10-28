export type SubjectCategory =
  | 'stem'
  | 'coding'
  | 'humanities'
  | 'languages'
  | 'commerce'
  | 'social'
  | 'other'
  | 'custom';

export type QuestionFormat =
  | 'multiple-choice'
  | 'coding'
  | 'step-by-step'
  | 'conceptual-short'
  | 'true-false'
  | 'fill-blank';

export type SubjectDifficulty = 'easy' | 'medium' | 'hard';

export interface SubjectTopic {
  id: string;
  title: string;
  description: string;
  subtopics: string[];
  difficulty: SubjectDifficulty;
  learningObjectives?: string[];
  keyRulesOrFormulas?: string[];
  estimatedMinutes?: number;
}

export interface Subject {
  id: string;
  name: string;
  category: SubjectCategory;
  categoryLabel: string;
  icon: string;
  description: string;
  tagline: string;
  accentColor: string;
  popularTopics: string[];
  topics: SubjectTopic[];
  isCustom?: boolean;
}

export interface UniversalQuestion {
  id: string;
  subjectId: string;
  topicId: string;
  topicTitle: string;
  prompt: string;
  format: QuestionFormat;
  difficulty: SubjectDifficulty;
  codeSnippet?: string;
  language?: string;
  options?: { id: string; text: string; isCorrect: boolean; explanation?: string }[];
  correctAnswer: string;
  stepByStepSolution: string[];
  explanation: string;
  commonPitfalls?: string;
  hint?: string;
  followUpQuestion?: string;
  sourceOrCitation?: string;
}

export interface DoubtMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  subjectId?: string;
  codeSnippet?: string;
  timestamp: string;
  solutionData?: {
    summary?: string;
    steps?: string[];
    codeSolution?: {
      language: string;
      code: string;
      explanation: string;
    };
    takeaways?: string[];
    comparisonTable?: {
      headers: string[];
      rows: string[][];
    };
    timelineEvents?: {
      date: string;
      title: string;
      description: string;
    }[];
    followUpSuggestions?: string[];
    citations?: string[];
  };
}

export interface DoubtConversation {
  id: string;
  title: string;
  subjectId: string;
  messages: DoubtMessage[];
  createdAt: string;
  updatedAt: string;
}

export interface SubjectProgressMetric {
  subjectId: string;
  subjectName: string;
  questionsAttempted: number;
  questionsCorrect: number;
  accuracy: number;
  lastStudied: string;
  masteredTopics: string[];
  difficultTopics: string[];
}

export interface MistakeReviewItem {
  id: string;
  questionId: string;
  subjectId: string;
  subjectName: string;
  prompt: string;
  studentAnswer: string;
  correctAnswer: string;
  explanation: string;
  misconceptionOrPitfall?: string;
  date: string;
  reviewed: boolean;
}
