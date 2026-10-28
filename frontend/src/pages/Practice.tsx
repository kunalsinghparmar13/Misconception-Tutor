import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import confetti from 'canvas-confetti';
import { ALL_SUBJECTS, INITIAL_UNIVERSAL_QUESTIONS } from '../data/subjects';
import { UniversalQuestion, SubjectDifficulty } from '../types/subjects';
import { aiService } from '../services/aiService';
import { SolutionRenderer } from '../components/SolutionRenderer';
import {
  CheckCircle2,
  XCircle,
  Lightbulb,
  ArrowRight,
  Sparkles,
  AlertCircle,
  HelpCircle,
  RotateCcw,
  BookOpen,
  Timer,
  Award,
  Layers,
  Terminal,
  Send,
  RefreshCw,
  Zap,
} from 'lucide-react';

interface PracticeProps {
  onCompleteAnswer?: (diagOrResult: any) => void;
  targetTopic?: string;
  onNavigateToDiagnosis?: () => void;
  onAskDoubtAboutQuestion?: (subject: string, questionText: string) => void;
}

export const Practice: React.FC<PracticeProps> = ({
  onCompleteAnswer,
  targetTopic,
  onNavigateToDiagnosis,
  onAskDoubtAboutQuestion,
}) => {
  const [selectedSubjectId, setSelectedSubjectId] = useState<string>(() => {
    if (targetTopic && ALL_SUBJECTS.some((s) => s.id === targetTopic)) {
      return targetTopic;
    }
    return ALL_SUBJECTS[0].id;
  });
  const [selectedDifficulty, setSelectedDifficulty] = useState<SubjectDifficulty>('medium');
  const [questions, setQuestions] = useState<UniversalQuestion[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedOptionId, setSelectedOptionId] = useState<string | null>(null);
  const [freeformAnswer, setFreeformAnswer] = useState('');
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [evaluationResult, setEvaluationResult] = useState<{
    isCorrect: boolean;
    feedback: string;
    scoreOutOf10?: number;
    stepByStepSolution?: string[];
  } | null>(null);

  const [showHint, setShowHint] = useState(false);
  const [timedMode, setTimedMode] = useState(false);
  const [timerSeconds, setTimerSeconds] = useState(0);
  const [sessionScore, setSessionScore] = useState({ correct: 0, total: 0 });
  const [showSessionSummary, setShowSessionSummary] = useState(false);
  const [isGeneratingAiQuestion, setIsGeneratingAiQuestion] = useState(false);

  // Timer interval
  useEffect(() => {
    let interval: any = null;
    if (timedMode && !isSubmitted && !showSessionSummary) {
      interval = setInterval(() => {
        setTimerSeconds((prev) => prev + 1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [timedMode, isSubmitted, showSessionSummary]);

  // Sync targetTopic prop into selectedSubjectId
  useEffect(() => {
    if (targetTopic && ALL_SUBJECTS.some((s) => s.id === targetTopic)) {
      setSelectedSubjectId(targetTopic);
    }
  }, [targetTopic]);

  // Load questions for subject
  useEffect(() => {
    loadQuestionsForSubject(selectedSubjectId, selectedDifficulty);
  }, [selectedSubjectId, selectedDifficulty]);

  const loadQuestionsForSubject = (subjectId: string, diff: SubjectDifficulty) => {
    setIsSubmitted(false);
    setEvaluationResult(null);
    setSelectedOptionId(null);
    setFreeformAnswer('');
    setShowHint(false);
    setTimerSeconds(0);

    const subjectQuestions = INITIAL_UNIVERSAL_QUESTIONS.filter(
      (q) => q.subjectId === subjectId
    );

    if (subjectQuestions.length > 0) {
      setQuestions(subjectQuestions);
    } else {
      // Use fallback question for this subject
      const subObj = ALL_SUBJECTS.find((s) => s.id === subjectId);
      const fallbackQ: UniversalQuestion = {
        id: `q-${subjectId}-custom`,
        subjectId,
        topicId: subObj?.topics[0]?.id || 'general',
        topicTitle: subObj?.topics[0]?.title || 'Core Foundations',
        prompt: `Explain the fundamental governing rule or equation in ${subObj?.name || 'this discipline'} with a concise example.`,
        format: 'conceptual-short',
        difficulty: diff,
        correctAnswer: 'Answers will be evaluated by the cognitive diagnostic parser.',
        stepByStepSolution: [
          'State the central principle or definition',
          'Identify key assumptions or boundary conditions',
          'Provide a concrete real-world illustration',
        ],
        explanation: `In ${subObj?.name}, core principles anchor all analytical derivations and practical problem solving.`,
        commonPitfalls: 'Overlooking edge cases or confusing correlated phenomena with causative factors.',
        hint: 'Focus on primary definitions rather than secondary derivations.',
        followUpQuestion: 'How does this principle adapt in non-ideal or extreme conditions?',
      };
      setQuestions([fallbackQ]);
    }
    setCurrentIndex(0);
  };

  const currentQ = questions[currentIndex];

  const handleSubmit = async () => {
    if (!currentQ || isSubmitted) return;

    setIsEvaluating(true);

    try {
      if (currentQ.options && currentQ.options.length > 0) {
        // Deterministic Multiple Choice Evaluation
        const selectedOpt = currentQ.options.find((o) => o.id === selectedOptionId);
        const isCorrect = selectedOpt ? selectedOpt.isCorrect : false;

        setEvaluationResult({
          isCorrect,
          feedback: isCorrect
            ? 'Correct! Your reasoning is accurate.'
            : selectedOpt?.explanation || 'Incorrect. Review the step-by-step breakdown.',
          stepByStepSolution: currentQ.stepByStepSolution,
        });

        if (isCorrect) {
          setSessionScore((prev) => ({ correct: prev.correct + 1, total: prev.total + 1 }));
          confetti({
            particleCount: 60,
            spread: 60,
            origin: { y: 0.6 },
            colors: ['#A3B5A0', '#8FBF9B', '#F1F0E9'],
          });
        } else {
          setSessionScore((prev) => ({ ...prev, total: prev.total + 1 }));
          aiService.recordMistake({
            questionId: currentQ.id,
            subjectId: currentQ.subjectId,
            subjectName: ALL_SUBJECTS.find((s) => s.id === currentQ.subjectId)?.name || 'General',
            prompt: currentQ.prompt,
            studentAnswer: selectedOpt?.text || 'Unselected',
            correctAnswer: currentQ.correctAnswer,
            explanation: currentQ.explanation,
            misconceptionOrPitfall: currentQ.commonPitfalls,
          });
        }
      } else {
        // Freeform / Coding Evaluation
        const evalData = await aiService.evaluateFreeformAnswer({
          question: currentQ.prompt,
          studentAnswer: freeformAnswer,
          subject: ALL_SUBJECTS.find((s) => s.id === currentQ.subjectId)?.name,
        });

        setEvaluationResult(evalData);
        if (evalData.isCorrect) {
          setSessionScore((prev) => ({ correct: prev.correct + 1, total: prev.total + 1 }));
          confetti({
            particleCount: 60,
            spread: 60,
            origin: { y: 0.6 },
            colors: ['#A3B5A0', '#8FBF9B', '#F1F0E9'],
          });
        } else {
          setSessionScore((prev) => ({ ...prev, total: prev.total + 1 }));
          aiService.recordMistake({
            questionId: currentQ.id,
            subjectId: currentQ.subjectId,
            subjectName: ALL_SUBJECTS.find((s) => s.id === currentQ.subjectId)?.name || 'General',
            prompt: currentQ.prompt,
            studentAnswer: freeformAnswer,
            correctAnswer: currentQ.correctAnswer,
            explanation: currentQ.explanation,
            misconceptionOrPitfall: evalData.identifiedMisconception || currentQ.commonPitfalls,
          });
        }
      }

      setIsSubmitted(true);
      if (onCompleteAnswer) {
        onCompleteAnswer({ isCorrect: true, questionId: currentQ.id });
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsEvaluating(false);
    }
  };

  const handleNext = () => {
    if (currentIndex < questions.length - 1) {
      setCurrentIndex((prev) => prev + 1);
      setSelectedOptionId(null);
      setFreeformAnswer('');
      setIsSubmitted(false);
      setEvaluationResult(null);
      setShowHint(false);
    } else {
      setShowSessionSummary(true);
    }
  };

  const handlePracticeSimilar = async () => {
    if (!currentQ) return;
    setIsEvaluating(true);
    try {
      const generated = await aiService.fetchAdaptiveQuestion({
        subject: ALL_SUBJECTS.find((s) => s.id === currentQ.subjectId)?.name || 'Mathematics',
        topic: currentQ.topicTitle,
        difficulty: selectedDifficulty,
      });
      setQuestions([generated]);
      setCurrentIndex(0);
      setSelectedOptionId(null);
      setFreeformAnswer('');
      setIsSubmitted(false);
      setEvaluationResult(null);
      setShowHint(false);
    } catch (e) {
      console.error(e);
    } finally {
      setIsEvaluating(false);
    }
  };

  const handleGenerateAiQuestion = async () => {
    setIsGeneratingAiQuestion(true);
    try {
      const subjectObj = ALL_SUBJECTS.find((s) => s.id === selectedSubjectId);
      const generated = await aiService.fetchAdaptiveQuestion({
        subject: subjectObj?.name || 'Mathematics',
        topic: currentQ?.topicTitle || subjectObj?.popularTopics[0] || 'Core Concepts',
        difficulty: selectedDifficulty,
      });

      setQuestions((prev) => [generated, ...prev]);
      setCurrentIndex(0);
      setSelectedOptionId(null);
      setFreeformAnswer('');
      setIsSubmitted(false);
      setEvaluationResult(null);
      setShowHint(false);
    } catch (err) {
      console.error('Failed to generate AI question:', err);
    } finally {
      setIsGeneratingAiQuestion(false);
    }
  };

  const handleRetry = () => {
    setIsSubmitted(false);
    setEvaluationResult(null);
    setSelectedOptionId(null);
    setFreeformAnswer('');
    setShowHint(false);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 text-left">
      {/* Session Controls & Discipline Switcher Bar */}
      <div className="p-4 sm:p-5 rounded-2xl bg-[#222823] border border-[#353C36] flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-md">
        <div className="flex flex-wrap items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-[#283329] border border-[#A3B5A0]/30 flex items-center justify-center text-[#A3B5A0]">
            <BookOpen className="w-4 h-4" />
          </div>

          <div>
            <div className="text-[10px] uppercase font-bold tracking-wider text-[#858D83]">
              Practice Session Subject
            </div>
            <select
              value={selectedSubjectId}
              onChange={(e) => setSelectedSubjectId(e.target.value)}
              className="bg-transparent font-bold text-sm text-[#F1F0E9] focus:outline-none cursor-pointer pr-2"
            >
              {ALL_SUBJECTS.map((s) => (
                <option key={s.id} value={s.id} className="bg-[#1D221E] text-[#F1F0E9]">
                  {s.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Difficulty, Timed Mode & AI Generator Toggles */}
        <div className="flex flex-wrap items-center gap-3">
          {/* AI Generator Button */}
          <button
            onClick={handleGenerateAiQuestion}
            disabled={isGeneratingAiQuestion}
            className="px-3 py-1.5 rounded-xl bg-[#283329] hover:bg-[#343E34] border border-[#A3B5A0]/40 text-xs font-semibold text-[#A3B5A0] hover:text-[#F1F0E9] flex items-center gap-1.5 transition-all shadow-sm disabled:opacity-50"
            title="Generate a brand new practice problem with Gemini 3.8 Flash"
          >
            <Sparkles className={`w-3.5 h-3.5 text-[#A3B5A0] ${isGeneratingAiQuestion ? 'animate-spin' : ''}`} />
            <span>{isGeneratingAiQuestion ? 'Generating AI Problem...' : 'Generate AI Problem'}</span>
          </button>

          {/* Difficulty pills */}
          <div className="flex items-center rounded-xl bg-[#1D221E] border border-[#353C36] p-0.5 text-xs">
            {(['easy', 'medium', 'hard'] as SubjectDifficulty[]).map((d) => (
              <button
                key={d}
                onClick={() => setSelectedDifficulty(d)}
                className={`px-2.5 py-1 rounded-lg capitalize transition-colors ${
                  selectedDifficulty === d
                    ? 'bg-[#292F2A] text-[#A3B5A0] font-bold shadow-sm'
                    : 'text-[#858D83] hover:text-[#F1F0E9]'
                }`}
              >
                {d}
              </button>
            ))}
          </div>

          {/* Timed Mode Toggle */}
          <button
            onClick={() => setTimedMode(!timedMode)}
            className={`px-3 py-1.5 rounded-xl border text-xs font-mono flex items-center gap-1.5 transition-colors ${
              timedMode
                ? 'bg-[#283329] border-[#A3B5A0] text-[#A3B5A0]'
                : 'bg-[#1D221E] border-[#353C36] text-[#858D83] hover:text-[#F1F0E9]'
            }`}
          >
            <Timer className="w-3.5 h-3.5" />
            <span>
              {timedMode ? `${Math.floor(timerSeconds / 60)}:${('0' + (timerSeconds % 60)).slice(-2)}` : 'Untimed'}
            </span>
          </button>

          {/* Score Counter */}
          <div className="px-3 py-1.5 rounded-xl bg-[#1D221E] border border-[#353C36] text-xs font-mono">
            <span className="text-[#858D83]">Score: </span>
            <span className="font-bold text-[#8FBF9B]">
              {sessionScore.correct}/{sessionScore.total}
            </span>
          </div>
        </div>
      </div>

      {/* Adaptive Difficulty & Mastery Indicator Banner */}
      {sessionScore.total >= 3 && (
        <motion.div
          initial={{ opacity: 0, y: -5 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-3.5 rounded-2xl bg-[#1D221E] border border-[#353C36] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
        >
          {Math.round((sessionScore.correct / sessionScore.total) * 100) >= 75 ? (
            <div className="flex items-center gap-2 text-[#8FBF9B]">
              <Zap className="w-4 h-4 text-[#8FBF9B] shrink-0" />
              <span>
                <strong>High Accuracy Streak!</strong> You are at {Math.round((sessionScore.correct / sessionScore.total) * 100)}% ({sessionScore.correct}/{sessionScore.total}). Ready for harder challenges?
              </span>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-[#D8BC86]">
              <Lightbulb className="w-4 h-4 text-[#D8BC86] shrink-0" />
              <span>
                <strong>Conceptual Calibration:</strong> Take time with each problem and review the step-by-step solutions below.
              </span>
            </div>
          )}
          <div className="flex items-center gap-1 shrink-0">
            <span className="text-[10px] text-[#858D83] uppercase mr-1">Switch:</span>
            {(['easy', 'medium', 'hard'] as SubjectDifficulty[]).map((d) => (
              <button
                key={d}
                onClick={() => setSelectedDifficulty(d)}
                className={`px-2 py-0.5 rounded text-[11px] capitalize transition-colors ${
                  selectedDifficulty === d
                    ? 'bg-[#A3B5A0] text-[#171A18] font-bold'
                    : 'text-[#858D83] hover:text-[#F1F0E9] bg-[#222823]'
                }`}
              >
                {d}
              </button>
            ))}
          </div>
        </motion.div>
      )}

      {/* Main Question Card */}
      {currentQ && (
        <motion.div
          key={currentQ.id}
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-6 sm:p-8 rounded-3xl bg-[#222823] border border-[#353C36] shadow-xl space-y-6"
        >
          {/* Topic & Format Badge */}
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <span className="px-3 py-1 rounded-full bg-[#283329] border border-[#A3B5A0]/30 text-[#A3B5A0] font-medium inline-flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5" />
                {currentQ.topicTitle}
              </span>
              <span className="text-[#858D83] font-mono capitalize">
                • {currentQ.format}
              </span>
            </div>

            <span className="px-2.5 py-0.5 rounded bg-[#1D221E] border border-[#353C36] font-mono text-[#858D83] uppercase">
              {currentQ.difficulty}
            </span>
          </div>

          {/* Question Prompt */}
          <div className="space-y-3">
            <h2 className="text-lg sm:text-xl font-bold text-[#F1F0E9] leading-snug">
              {currentQ.prompt}
            </h2>

            {/* Code Snippet if present */}
            {currentQ.codeSnippet && (
              <div className="rounded-xl overflow-hidden border border-[#353C36] bg-[#121413]">
                <div className="px-3 py-1 bg-[#1A1E1B] border-b border-[#353C36] text-[10px] font-mono text-[#A3B5A0] flex items-center gap-1">
                  <Terminal className="w-3 h-3" />
                  <span>Code Context:</span>
                </div>
                <pre className="p-3 text-xs font-mono text-[#F1F0E9] overflow-x-auto">
                  <code>{currentQ.codeSnippet}</code>
                </pre>
              </div>
            )}
          </div>

          {/* Answer Interaction Options */}
          {currentQ.options && currentQ.options.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
              {currentQ.options.map((opt) => {
                const isSelected = selectedOptionId === opt.id;
                let cardStyle =
                  'bg-[#1D221E] border-[#353C36] text-[#B5B9B0] hover:bg-[#292F2A] hover:border-[#A3B5A0]/40';

                if (isSelected && !isSubmitted) {
                  cardStyle =
                    'bg-[#283329] border-[#A3B5A0] text-[#A3B5A0] ring-1 ring-[#A3B5A0]/30';
                } else if (isSubmitted) {
                  if (opt.isCorrect) {
                    cardStyle =
                      'bg-[#8FBF9B]/15 border-[#8FBF9B] text-[#8FBF9B] ring-1 ring-[#8FBF9B]/30';
                  } else if (isSelected && !opt.isCorrect) {
                    cardStyle =
                      'bg-[#D98E8E]/15 border-[#D98E8E] text-[#D98E8E] ring-1 ring-[#D98E8E]/30';
                  } else {
                    cardStyle = 'bg-[#1D221E]/50 border-[#353C36]/40 text-[#858D83]';
                  }
                }

                return (
                  <button
                    key={opt.id}
                    onClick={() => !isSubmitted && setSelectedOptionId(opt.id)}
                    disabled={isSubmitted}
                    className={`p-4 rounded-2xl border text-left transition-all flex items-start gap-3 ${cardStyle}`}
                  >
                    <span className="w-6 h-6 rounded-lg bg-[#121413] border border-current/30 flex items-center justify-center font-mono text-xs font-bold shrink-0 mt-0.5">
                      {opt.id.toUpperCase()}
                    </span>
                    <span className="text-xs sm:text-sm leading-relaxed">{opt.text}</span>
                  </button>
                );
              })}
            </div>
          ) : (
            /* Freeform Conceptual / Coding / Equation input */
            <div className="space-y-3 pt-2">
              <label className="block text-xs font-semibold text-[#858D83]">
                Your Solution / Explanation:
              </label>
              <textarea
                rows={4}
                value={freeformAnswer}
                onChange={(e) => setFreeformAnswer(e.target.value)}
                disabled={isSubmitted}
                placeholder="Type your mathematical derivation, code solution, or conceptual analysis..."
                className="w-full p-4 rounded-2xl bg-[#1D221E] border border-[#353C36] focus:border-[#A3B5A0] focus:outline-none text-xs sm:text-sm text-[#F1F0E9] font-mono placeholder-[#858D83]"
              />
            </div>
          )}

          {/* Hint Disclosure */}
          {currentQ.hint && !isSubmitted && (
            <div>
              <button
                type="button"
                onClick={() => setShowHint(!showHint)}
                className="text-xs text-[#858D83] hover:text-[#A3B5A0] inline-flex items-center gap-1 transition-colors"
              >
                <HelpCircle className="w-3.5 h-3.5" />
                <span>{showHint ? 'Hide Hint' : 'Need a Hint?'}</span>
              </button>
              {showHint && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  className="mt-2 p-3 rounded-xl bg-[#283329]/50 border border-[#A3B5A0]/30 text-xs text-[#A3B5A0]"
                >
                  <Lightbulb className="w-3.5 h-3.5 inline mr-1 text-[#D8BC86]" />
                  {currentQ.hint}
                </motion.div>
              )}
            </div>
          )}

          {/* Submit Action */}
          {!isSubmitted && (
            <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
              {onAskDoubtAboutQuestion ? (
                <button
                  type="button"
                  onClick={() =>
                    onAskDoubtAboutQuestion(
                      currentQ.subjectId,
                      `I am working on this question in ${currentQ.topicTitle}: "${currentQ.prompt}". Could you help explain the core concept without spoiling the answer?`
                    )
                  }
                  className="px-4 py-2 rounded-xl bg-[#1D221E] hover:bg-[#292F2A] border border-[#353C36] text-xs font-semibold text-[#B5B9B0] hover:text-[#F1F0E9] flex items-center gap-1.5 transition-colors"
                >
                  <HelpCircle className="w-3.5 h-3.5 text-[#A3B5A0]" />
                  <span>Ask Doubt AI for a Concept Nudge</span>
                </button>
              ) : <div />}

              <button
                onClick={handleSubmit}
                disabled={
                  isEvaluating ||
                  (currentQ.options && !selectedOptionId) ||
                  (!currentQ.options && !freeformAnswer.trim())
                }
                className={`px-8 py-3 rounded-xl font-bold text-xs sm:text-sm flex items-center gap-2 transition-all ${
                  (selectedOptionId || freeformAnswer.trim()) && !isEvaluating
                    ? 'bg-[#A3B5A0] text-[#171A18] hover:bg-[#B7C7B2] shadow-md shadow-[#A3B5A0]/20'
                    : 'bg-[#1D221E] text-[#858D83] cursor-not-allowed border border-[#353C36]'
                }`}
              >
                <span>{isEvaluating ? 'Evaluating Answer...' : 'Submit Answer'}</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* Comprehensive Solution & Feedback Panel */}
          <AnimatePresence>
            {isSubmitted && evaluationResult && (
              <motion.div
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                className={`p-6 rounded-2xl border space-y-5 ${
                  evaluationResult.isCorrect
                    ? 'bg-[#8FBF9B]/10 border-[#8FBF9B]/30'
                    : 'bg-[#D98E8E]/10 border-[#D98E8E]/30'
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div
                      className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
                        evaluationResult.isCorrect
                          ? 'bg-[#8FBF9B]/20 text-[#8FBF9B]'
                          : 'bg-[#D98E8E]/20 text-[#D98E8E]'
                      }`}
                    >
                      {evaluationResult.isCorrect ? (
                        <CheckCircle2 className="w-5 h-5" />
                      ) : (
                        <AlertCircle className="w-5 h-5" />
                      )}
                    </div>
                    <div>
                      <h3 className="font-bold text-sm sm:text-base text-[#F1F0E9]">
                        {evaluationResult.isCorrect
                          ? 'Mastery Confirmed! Excellent Work.'
                          : 'Calculation Divergence Detected'}
                      </h3>
                      <p className="text-xs text-[#B5B9B0]">{evaluationResult.feedback}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {!evaluationResult.isCorrect && (
                      <button
                        onClick={handleRetry}
                        className="px-3.5 py-2 rounded-xl bg-[#222823] hover:bg-[#292F2A] border border-[#353C36] text-xs text-[#F1F0E9] flex items-center gap-1.5 transition-colors"
                      >
                        <RotateCcw className="w-3.5 h-3.5" />
                        <span>Retry</span>
                      </button>
                    )}
                    <button
                      onClick={handleNext}
                      className="px-5 py-2 rounded-xl bg-[#A3B5A0] hover:bg-[#B7C7B2] text-[#171A18] font-bold text-xs flex items-center gap-1.5 shadow-md transition-all"
                    >
                      <span>Next Question</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                {/* Model Solution & Steps */}
                <div className="p-4 rounded-xl bg-[#171A18]/80 border border-[#353C36] space-y-3">
                  <div className="flex items-center justify-between text-xs font-semibold text-[#A3B5A0]">
                    <span className="flex items-center gap-1.5">
                      <BookOpen className="w-3.5 h-3.5" />
                      Model Solution & Reasoning:
                    </span>
                    <span className="font-mono text-[#F1F0E9]">
                      Target: {currentQ.correctAnswer}
                    </span>
                  </div>

                  <SolutionRenderer
                    content={currentQ.explanation}
                    steps={currentQ.stepByStepSolution}
                    subject={currentQ.subjectId}
                  />

                  {currentQ.commonPitfalls && (
                    <div className="mt-3 p-3 rounded-lg bg-[#D8BC86]/10 border border-[#D8BC86]/30 text-xs text-[#D8BC86]">
                      <span className="font-bold">Common Pitfall: </span>
                      {currentQ.commonPitfalls}
                    </div>
                  )}

                  {currentQ.followUpQuestion && (
                    <div className="mt-2 text-xs text-[#B5B9B0] italic">
                      <span className="font-bold text-[#A3B5A0]">Follow-Up Reflection: </span>
                      {currentQ.followUpQuestion}
                    </div>
                  )}
                </div>

                {/* Bottom Action Strip: Ask Doubt / Practice Similar */}
                <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-[#353C36]/60">
                  <button
                    onClick={handlePracticeSimilar}
                    className="text-xs font-medium text-[#A3B5A0] hover:text-[#F1F0E9] flex items-center gap-1.5 transition-colors"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    <span>Practice a Similar Adaptive Question</span>
                  </button>

                  {onAskDoubtAboutQuestion && (
                    <button
                      onClick={() =>
                        onAskDoubtAboutQuestion(
                          currentQ.subjectId,
                          `In ${currentQ.topicTitle}, I had trouble understanding: ${currentQ.prompt}`
                        )
                      }
                      className="text-xs font-medium text-[#B5B9B0] hover:text-[#F1F0E9] flex items-center gap-1 transition-colors"
                    >
                      <Sparkles className="w-3.5 h-3.5 text-[#A3B5A0]" />
                      <span>Ask AI Doubt Solver About This Problem</span>
                    </button>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      )}

      {/* Session Summary Modal */}
      <AnimatePresence>
        {showSessionSummary && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="w-full max-w-md p-6 rounded-3xl bg-[#222823] border border-[#353C36] space-y-5 shadow-2xl text-center"
            >
              <div className="w-12 h-12 rounded-2xl bg-[#283329] border border-[#A3B5A0]/30 flex items-center justify-center text-[#A3B5A0] mx-auto">
                <Award className="w-6 h-6" />
              </div>

              <div className="space-y-1">
                <h3 className="text-xl font-bold text-[#F1F0E9]">Practice Set Completed!</h3>
                <p className="text-xs text-[#B5B9B0]">
                  {ALL_SUBJECTS.find((s) => s.id === selectedSubjectId)?.name} • {selectedDifficulty.toUpperCase()}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3 p-4 rounded-2xl bg-[#1D221E] border border-[#353C36]">
                <div>
                  <div className="text-xs text-[#858D83]">Accuracy</div>
                  <div className="text-2xl font-bold text-[#8FBF9B]">
                    {sessionScore.total > 0
                      ? `${Math.round((sessionScore.correct / sessionScore.total) * 100)}%`
                      : '0%'}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-[#858D83]">Correct Answers</div>
                  <div className="text-2xl font-bold text-[#F1F0E9]">
                    {sessionScore.correct} / {sessionScore.total}
                  </div>
                </div>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => {
                    setShowSessionSummary(false);
                    loadQuestionsForSubject(selectedSubjectId, selectedDifficulty);
                  }}
                  className="flex-1 py-2.5 rounded-xl bg-[#292F2A] hover:bg-[#343E34] border border-[#353C36] text-xs font-semibold text-[#F1F0E9] transition-colors"
                >
                  Restart Set
                </button>
                <button
                  onClick={() => setShowSessionSummary(false)}
                  className="flex-1 py-2.5 rounded-xl bg-[#A3B5A0] text-[#171A18] font-bold text-xs hover:bg-[#B7C7B2] transition-colors"
                >
                  Done
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};
