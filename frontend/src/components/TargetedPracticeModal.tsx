import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import confetti from 'canvas-confetti';
import { Question, DiagnosisResult } from '../types/education';
import { MathExpression } from './FractionDisplay';
import { api } from '../services/api';
import { Check, X, ArrowRight, Target, HelpCircle, Loader2 } from 'lucide-react';

interface TargetedPracticeModalProps {
  initialQuestion: Question;
  misconceptionTitle: string;
  onClose: () => void;
  onComplete: () => void;
}

export const TargetedPracticeModal: React.FC<TargetedPracticeModalProps> = ({
  initialQuestion,
  misconceptionTitle,
  onClose,
  onComplete,
}) => {
  const [currentQuestion] = useState<Question>(initialQuestion);
  const [studentAnswer, setStudentAnswer] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [result, setResult] = useState<DiagnosisResult | null>(null);
  const [showHint, setShowHint] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string>('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!studentAnswer.trim()) {
      setErrorMsg('Please enter your answer before checking.');
      return;
    }
    setErrorMsg('');
    setIsSubmitting(true);

    try {
      const evaluation = await api.submitAnswer(currentQuestion, studentAnswer.trim());
      setResult(evaluation);

      if (evaluation.isCorrect) {
        confetti({
          particleCount: 50,
          spread: 70,
          origin: { y: 0.5 },
          colors: ['#A3B5A0', '#8FBF9B', '#F1F0E9'],
          disableForReducedMotion: true,
        });
      }
    } catch {
      setErrorMsg('Failed to evaluate answer. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/80 backdrop-blur-md"
        onClick={onClose}
      />

      {/* Modal Dialog */}
      <motion.div
        initial={{ opacity: 0, scale: 0.94, y: 15 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.94, y: 15 }}
        transition={{ type: 'spring', damping: 25, stiffness: 300 }}
        className="bg-[#1D221E] border border-[#353C36] rounded-3xl w-full max-w-xl p-6 md:p-8 shadow-2xl relative z-10 max-h-[90vh] overflow-y-auto backdrop-blur-2xl text-left"
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-4 mb-6">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-2xl bg-[#283329] border border-[#A3B5A0]/40 flex items-center justify-center text-[#A3B5A0] shadow-sm">
              <Target className="w-5 h-5 text-[#A3B5A0]" />
            </div>
            <div>
              <span className="text-xs font-bold text-[#A3B5A0] uppercase tracking-wider block">
                Targeted Remediation
              </span>
              <h3 className="text-lg md:text-xl font-bold text-[#F1F0E9] tracking-tight">
                {currentQuestion.topicTitle}
              </h3>
            </div>
          </div>
          <motion.button
            whileTap={{ scale: 0.9 }}
            onClick={onClose}
            className="text-[#858D83] hover:text-[#F1F0E9] p-2 rounded-xl hover:bg-white/5 transition-colors"
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </motion.button>
        </div>

        {/* Misconception Badge */}
        <div className="mb-6 p-3.5 rounded-2xl bg-[#222823] border border-[#353C36] flex items-center justify-between text-xs">
          <span className="text-[#858D83]">Targeting Misconception:</span>
          <span className="text-[#A3B5A0] font-semibold">{misconceptionTitle}</span>
        </div>

        {/* Question Prompt */}
        <div className="text-center mb-6">
          <p className="text-sm text-[#B5B9B0] mb-4">{currentQuestion.prompt}</p>

          <div className="p-6 md:p-8 rounded-2xl bg-[#171A18] border border-[#353C36] inline-block shadow-inner">
            <MathExpression
              firstOperand={currentQuestion.expression.firstOperand}
              operator={currentQuestion.expression.operator}
              secondOperand={currentQuestion.expression.secondOperand}
              size="lg"
            />
          </div>
        </div>

        {/* Hint toggle */}
        {currentQuestion.hint && (
          <div className="mb-6 text-center">
            <button
              type="button"
              onClick={() => setShowHint(!showHint)}
              className="text-xs text-[#8FBF9B] hover:underline inline-flex items-center gap-1.5"
            >
              <HelpCircle className="w-3.5 h-3.5" />
              {showHint ? 'Hide Guidance Hint' : 'Need a step hint?'}
            </button>
            <AnimatePresence>
              {showHint && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="mt-2 p-3.5 rounded-xl bg-[#171A18] border border-[#8FBF9B]/20 text-xs text-[#B5B9B0] text-left leading-relaxed overflow-hidden"
                >
                  {currentQuestion.hint}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}

        {/* Input Form or Result View */}
        {!result ? (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="flex-1 relative">
                <input
                  type="text"
                  value={studentAnswer}
                  onChange={(e) => setStudentAnswer(e.target.value)}
                  placeholder="e.g. 5/6 or 3"
                  className="w-full bg-[#171A18] border-2 border-[#353C36] focus:border-[#A3B5A0] rounded-2xl px-4 py-3.5 text-xl font-mono text-[#F1F0E9] placeholder-[#858D83] focus:outline-none focus:ring-2 focus:ring-[#A3B5A0]/20 transition-all text-center shadow-inner"
                  disabled={isSubmitting}
                  autoFocus
                />
              </div>
              <motion.button
                type="submit"
                disabled={isSubmitting || !studentAnswer.trim()}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="px-6 py-3.5 bg-[#A3B5A0] hover:bg-[#B7C7B2] text-[#171A18] font-bold rounded-2xl shadow-md flex items-center justify-center gap-2 whitespace-nowrap transition-all"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Evaluating...</span>
                  </>
                ) : (
                  <>
                    <span>Check Answer</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </motion.button>
            </div>

            {errorMsg && (
              <p className="text-xs text-[#D98E8E] text-center">{errorMsg}</p>
            )}
          </form>
        ) : (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-5"
          >
            <div
              className={`p-5 rounded-2xl border text-left ${
                result.isCorrect
                  ? 'bg-[#8FBF9B]/15 border-[#8FBF9B]/30 text-[#8FBF9B]'
                  : 'bg-[#D98E8E]/15 border-[#D98E8E]/30 text-[#D98E8E]'
              }`}
            >
              <div className="flex items-center gap-2 font-bold text-base mb-1">
                {result.isCorrect ? (
                  <>
                    <Check className="w-5 h-5 text-[#8FBF9B]" />
                    <span className="text-[#8FBF9B]">Brilliant! Misconception Corrected.</span>
                  </>
                ) : (
                  <>
                    <X className="w-5 h-5 text-[#D98E8E]" />
                    <span className="text-[#D98E8E]">Still working through it.</span>
                  </>
                )}
              </div>
              <p className="text-xs text-[#F1F0E9] leading-relaxed">
                {result.explanation}
              </p>
              <div className="mt-3 pt-3 border-t border-white/10 flex items-center justify-between text-xs text-[#858D83]">
                <span>Your Answer: <strong className="text-[#F1F0E9] font-mono">{studentAnswer}</strong></span>
                <span>Target Correct: <strong className="text-[#8FBF9B] font-mono">{result.correctAnswer}</strong></span>
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <motion.button
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                onClick={onComplete}
                className="px-6 py-3 bg-[#A3B5A0] hover:bg-[#B7C7B2] text-[#171A18] font-bold rounded-xl text-sm transition-all shadow-md"
              >
                Return to Dashboard
              </motion.button>
            </div>
          </motion.div>
        )}
      </motion.div>
    </div>
  );
};
