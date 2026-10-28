import React, { useState, useEffect } from 'react';
import { motion } from 'motion/react';
import { LearnerProgress } from '../types/education';
import { ALL_SUBJECTS } from '../data/subjects';
import { aiService } from '../services/aiService';
import { MistakeReviewItem, DoubtConversation } from '../types/subjects';
import { ProgressChart } from '../components/ProgressChart';
import { ProgressRing } from '../components/ProgressRing';
import { TiltCard } from '../components/TiltCard';
import {
  TrendingUp,
  Award,
  Calendar,
  CheckCircle,
  AlertCircle,
  Clock,
  Sparkles,
  BookOpen,
  MessageSquare,
  AlertTriangle,
  RotateCcw,
  Check,
  ChevronRight,
  Filter,
} from 'lucide-react';

interface ProgressProps {
  initialProgress: LearnerProgress;
  onPracticeTopic?: (topic?: string) => void;
  onNavigateToDoubtSolver?: (subjectId?: string, questionText?: string) => void;
}

export const Progress: React.FC<ProgressProps> = ({
  initialProgress: progress,
  onPracticeTopic,
  onNavigateToDoubtSolver,
}) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'mistakes' | 'doubts'>('overview');
  const [mistakes, setMistakes] = useState<MistakeReviewItem[]>([]);
  const [mistakeSubjectFilter, setMistakeSubjectFilter] = useState<string>('all');
  const [savedDoubts, setSavedDoubts] = useState<DoubtConversation[]>([]);

  useEffect(() => {
    setMistakes(aiService.getMistakes());
    setSavedDoubts(aiService.getStoredConversations());
  }, []);

  const masteredBugs = progress.misconceptionBugRates.filter((m) => m.status === 'Mastered');
  const activeBugs = progress.misconceptionBugRates.filter((m) => m.status !== 'Mastered');

  return (
    <div className="space-y-8 text-left">
      {/* Header Banner */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-[#222823] via-[#1D221E] to-[#171A18] border border-[#353C36] p-6 lg:p-8 backdrop-blur-xl shadow-xl">
        <div className="absolute top-0 right-0 w-80 h-80 bg-[#A3B5A0]/5 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#283329] border border-[#A3B5A0]/30 text-xs font-semibold text-[#A3B5A0]">
              <TrendingUp className="w-3.5 h-3.5 text-[#A3B5A0]" />
              <span>Cross-Discipline Learning Analytics & Mistake Audit</span>
            </div>
            <h1 className="text-3xl font-extrabold text-[#F1F0E9] tracking-tight">
              Learning History &{' '}
              <span className="bg-gradient-to-r from-[#A3B5A0] to-[#B7C7B2] bg-clip-text text-transparent">
                Mastery Trajectory
              </span>
            </h1>
            <p className="text-sm text-[#B5B9B0] max-w-xl">
              Inspect your verified accuracy rate, review past questions you missed, and explore stored AI doubt resolutions.
            </p>
          </div>

          <div className="p-4 rounded-2xl bg-[#1D221E] border border-[#353C36] flex items-center gap-4 shrink-0 shadow-inner">
            <ProgressRing
              percentage={Math.round(progress.accuracy)}
              size={64}
              strokeWidth={5}
              color="#A3B5A0"
              trackColor="#353C36"
            />
            <div>
              <div className="text-[10px] text-[#858D83] font-semibold uppercase tracking-wider">
                Overall Accuracy
              </div>
              <div className="text-xl font-bold text-[#F1F0E9]">{Math.round(progress.accuracy)}%</div>
              <div className="text-[11px] text-[#8FBF9B] font-medium">{progress.totalAttempted} problems evaluated</div>
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <div className="flex border-b border-[#353C36] gap-6 text-xs font-semibold">
        <button
          onClick={() => setActiveTab('overview')}
          className={`pb-3 transition-colors relative ${
            activeTab === 'overview' ? 'text-[#A3B5A0]' : 'text-[#858D83] hover:text-[#F1F0E9]'
          }`}
        >
          <span>Progress Overview & Misconception Curves</span>
          {activeTab === 'overview' && (
            <motion.div
              layoutId="prog-tab"
              className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#A3B5A0]"
            />
          )}
        </button>

        <button
          onClick={() => setActiveTab('mistakes')}
          className={`pb-3 transition-colors relative flex items-center gap-1.5 ${
            activeTab === 'mistakes' ? 'text-[#A3B5A0]' : 'text-[#858D83] hover:text-[#F1F0E9]'
          }`}
        >
          <span>Mistake Review Log</span>
          <span className="px-1.5 py-0.5 rounded-full bg-[#1D221E] border border-[#353C36] text-[10px]">
            {mistakes.length}
          </span>
          {activeTab === 'mistakes' && (
            <motion.div
              layoutId="prog-tab"
              className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#A3B5A0]"
            />
          )}
        </button>

        <button
          onClick={() => setActiveTab('doubts')}
          className={`pb-3 transition-colors relative flex items-center gap-1.5 ${
            activeTab === 'doubts' ? 'text-[#A3B5A0]' : 'text-[#858D83] hover:text-[#F1F0E9]'
          }`}
        >
          <span>Recent Doubts & Solutions</span>
          <span className="px-1.5 py-0.5 rounded-full bg-[#1D221E] border border-[#353C36] text-[10px]">
            {savedDoubts.length}
          </span>
          {activeTab === 'doubts' && (
            <motion.div
              layoutId="prog-tab"
              className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#A3B5A0]"
            />
          )}
        </button>
      </div>

      {/* Tab 1: Overview */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Longitudinal Chart */}
          <ProgressChart bugRates={progress.misconceptionBugRates} />

          {/* Subject Competence Breakdown Matrix */}
          <div className="p-6 rounded-3xl bg-[#222823] border border-[#353C36] space-y-4 shadow-md">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-[#F1F0E9] flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-[#A3B5A0]" />
                Subject Practice Distribution
              </h2>
              <span className="text-xs text-[#858D83]">Across all connected subjects</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {ALL_SUBJECTS.slice(0, 6).map((sub) => (
                <div
                  key={sub.id}
                  className="p-3.5 rounded-xl bg-[#1D221E] border border-[#353C36] flex items-center justify-between gap-3"
                >
                  <div className="space-y-0.5 truncate">
                    <div className="text-xs font-bold text-[#F1F0E9] truncate">{sub.name}</div>
                    <div className="text-[10px] text-[#858D83] font-mono">{sub.categoryLabel}</div>
                  </div>
                  {onPracticeTopic && (
                    <button
                      onClick={() => onPracticeTopic(sub.id)}
                      className="px-2.5 py-1 rounded-lg bg-[#283329] hover:bg-[#A3B5A0] text-[#A3B5A0] hover:text-[#171A18] text-[11px] font-semibold transition-colors shrink-0"
                    >
                      Practice
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Active vs Mastered Cognitive Divergence Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Mastered */}
            <TiltCard
              glowColor="rgba(143, 191, 155, 0.12)"
              className="p-6 rounded-2xl bg-[#222823] border border-[#353C36] space-y-4 shadow-md"
            >
              <div className="flex items-center justify-between">
                <h3 className="text-base font-bold text-[#F1F0E9] flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-[#8FBF9B]" />
                  Mastered Mental Models ({masteredBugs.length})
                </h3>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-[#8FBF9B]/15 text-[#8FBF9B] border border-[#8FBF9B]/30">
                  Cured
                </span>
              </div>

              <div className="space-y-2.5">
                {masteredBugs.length === 0 ? (
                  <p className="text-xs text-[#858D83] py-4">Keep practicing to transition focus areas to Mastered status!</p>
                ) : (
                  masteredBugs.map((item) => (
                    <div
                      key={item.misconceptionId}
                      className="p-3.5 rounded-xl bg-[#1D221E] border border-[#353C36] space-y-1"
                    >
                      <div className="flex items-center justify-between text-xs font-bold text-[#F1F0E9]">
                        <span>{item.name}</span>
                        <span className="text-[10px] text-[#8FBF9B] font-mono">
                          {item.currentBugRate}% error rate
                        </span>
                      </div>
                      <p className="text-[11px] text-[#858D83] line-clamp-1">
                        Category: {item.category} • Trend: {item.trend}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </TiltCard>

            {/* In Progress */}
            <TiltCard
              glowColor="rgba(216, 188, 134, 0.12)"
              className="p-6 rounded-2xl bg-[#222823] border border-[#353C36] space-y-4 shadow-md"
            >
              <div className="flex items-center justify-between">
                <h3 className="text-base font-bold text-[#F1F0E9] flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-[#D8BC86]" />
                  Active Focus Areas ({activeBugs.length})
                </h3>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-[#D8BC86]/15 text-[#D8BC86] border border-[#D8BC86]/30">
                  Targeted
                </span>
              </div>

              <div className="space-y-2.5">
                {activeBugs.map((item) => (
                  <div
                    key={item.misconceptionId}
                    className="p-3.5 rounded-xl bg-[#1D221E] border border-[#353C36] space-y-1.5 flex items-start justify-between gap-3"
                  >
                    <div className="space-y-0.5 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-[#F1F0E9]">
                          {item.name}
                        </span>
                        <span className="text-[10px] font-mono text-[#D8BC86]">
                          ({item.currentBugRate}% rate)
                        </span>
                      </div>
                      <p className="text-[11px] text-[#858D83] line-clamp-1">
                        Category: {item.category} • Status: {item.status}
                      </p>
                    </div>
                    {onPracticeTopic && (
                      <button
                        onClick={() => onPracticeTopic(item.misconceptionId)}
                        className="shrink-0 px-2.5 py-1 rounded-lg bg-[#283329] hover:bg-[#A3B5A0] text-[#A3B5A0] hover:text-[#171A18] text-xs font-medium transition-colors"
                      >
                        Remediate
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </TiltCard>
          </div>
        </div>
      )}

      {/* Tab 2: Mistake Review Log */}
      {activeTab === 'mistakes' && (
        <div className="space-y-4">
          <div className="p-4 rounded-2xl bg-[#222823] border border-[#353C36] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
            <span className="text-[#B5B9B0]">
              Every missed question is preserved here with the student's submission, model answer, and explanation.
            </span>
            <div className="flex items-center gap-2">
              <span className="text-[#858D83]">Subject:</span>
              <select
                value={mistakeSubjectFilter}
                onChange={(e) => setMistakeSubjectFilter(e.target.value)}
                className="px-2.5 py-1 rounded-xl bg-[#1D221E] border border-[#353C36] text-xs text-[#F1F0E9] focus:outline-none focus:border-[#A3B5A0]"
              >
                <option value="all">All Subjects ({mistakes.length})</option>
                {ALL_SUBJECTS.map((s) => {
                  const count = mistakes.filter((m) => m.subjectId === s.id).length;
                  if (count === 0) return null;
                  return (
                    <option key={s.id} value={s.id}>
                      {s.name} ({count})
                    </option>
                  );
                })}
              </select>
            </div>
          </div>

          {mistakes.filter(m => mistakeSubjectFilter === 'all' || m.subjectId === mistakeSubjectFilter).length === 0 ? (
            <div className="text-center py-16 p-6 rounded-3xl bg-[#222823] border border-[#353C36] space-y-2">
              <CheckCircle className="w-8 h-8 text-[#8FBF9B] mx-auto" />
              <p className="text-sm font-semibold text-[#F1F0E9]">No mistakes found for this subject!</p>
              <p className="text-xs text-[#858D83]">
                As you practice questions across subjects, any incorrect answers will be logged here for self-review.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {mistakes
                .filter(m => mistakeSubjectFilter === 'all' || m.subjectId === mistakeSubjectFilter)
                .map((item) => (
                <div
                  key={item.id}
                  className="p-5 rounded-2xl bg-[#222823] border border-[#353C36] hover:border-[#A3B5A0]/40 transition-colors space-y-3"
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="px-2.5 py-0.5 rounded bg-[#1D221E] border border-[#353C36] text-[#A3B5A0] font-mono font-semibold">
                      {item.subjectName}
                    </span>
                    <span className="text-[#858D83] text-[11px] font-mono">
                      {new Date(item.date).toLocaleDateString()}
                    </span>
                  </div>

                  <h3 className="text-sm font-bold text-[#F1F0E9]">{item.prompt}</h3>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                    <div className="p-3 rounded-xl bg-[#D98E8E]/10 border border-[#D98E8E]/25 text-[#D98E8E] space-y-1">
                      <div className="font-bold uppercase text-[10px]">Your Answer:</div>
                      <div className="font-mono text-xs">{item.studentAnswer}</div>
                    </div>

                    <div className="p-3 rounded-xl bg-[#8FBF9B]/10 border border-[#8FBF9B]/25 text-[#8FBF9B] space-y-1">
                      <div className="font-bold uppercase text-[10px]">Model Correct Answer:</div>
                      <div className="font-mono text-xs">{item.correctAnswer}</div>
                    </div>
                  </div>

                  <p className="text-xs text-[#B5B9B0] leading-relaxed">
                    <span className="font-bold text-[#F1F0E9]">Explanation: </span>
                    {item.explanation}
                  </p>

                  {item.misconceptionOrPitfall && (
                    <div className="p-2.5 rounded-lg bg-[#D8BC86]/10 border border-[#D8BC86]/25 text-xs text-[#D8BC86]">
                      <span className="font-bold">Avoid this pitfall: </span>
                      {item.misconceptionOrPitfall}
                    </div>
                  )}

                  <div className="pt-2 flex items-center justify-between border-t border-[#353C36] text-xs">
                    <button
                      onClick={() => {
                        const updated = mistakes.filter((m) => m.id !== item.id);
                        setMistakes(updated);
                        localStorage.setItem('ai_that_teaches_mistake_review', JSON.stringify(updated));
                      }}
                      className="text-[11px] text-[#8FBF9B] hover:underline font-medium flex items-center gap-1"
                    >
                      <Check className="w-3.5 h-3.5" />
                      <span>Mark Resolved</span>
                    </button>

                    <div className="flex items-center gap-2">
                      {onNavigateToDoubtSolver && (
                        <button
                          onClick={() => onNavigateToDoubtSolver(item.subjectId, `Can you explain how to solve: ${item.prompt}`)}
                          className="px-2.5 py-1 rounded-lg bg-[#1D221E] hover:bg-[#283329] border border-[#353C36] text-[#A3B5A0] text-[11px] font-medium transition-colors"
                        >
                          Ask Doubt
                        </button>
                      )}
                      {onPracticeTopic && (
                        <button
                          onClick={() => onPracticeTopic(item.subjectId)}
                          className="px-2.5 py-1 rounded-lg bg-[#A3B5A0] hover:bg-[#B7C7B2] text-[#171A18] font-bold text-[11px] transition-colors"
                        >
                          Practice Subject
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Recent Doubts & Solutions */}
      {activeTab === 'doubts' && (
        <div className="space-y-4">
          <div className="p-4 rounded-2xl bg-[#222823] border border-[#353C36] text-xs text-[#B5B9B0]">
            Review your saved AI doubt sessions and concepts discussed with the AI tutor.
          </div>

          {savedDoubts.length === 0 ? (
            <div className="text-center py-16 p-6 rounded-3xl bg-[#222823] border border-[#353C36] space-y-2">
              <MessageSquare className="w-8 h-8 text-[#A3B5A0] mx-auto" />
              <p className="text-sm font-semibold text-[#F1F0E9]">No previous doubts saved</p>
              <p className="text-xs text-[#858D83]">
                Ask any question in the Doubt Solver tab to automatically save your learning discussions here.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {savedDoubts.map((conv) => (
                <div
                  key={conv.id}
                  className="p-5 rounded-2xl bg-[#222823] border border-[#353C36] hover:border-[#A3B5A0]/40 transition-colors space-y-3"
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-sm font-bold text-[#F1F0E9]">{conv.title}</span>
                    <span className="text-[#858D83] font-mono text-[11px]">
                      {new Date(conv.updatedAt).toLocaleDateString()}
                    </span>
                  </div>

                  <div className="text-xs text-[#B5B9B0] line-clamp-2">
                    {conv.messages[conv.messages.length - 1]?.content.replace(/#|\*|`/g, '')}
                  </div>

                  <div className="pt-2 flex justify-end">
                    {onNavigateToDoubtSolver && (
                      <button
                        onClick={() => onNavigateToDoubtSolver(conv.subjectId)}
                        className="text-xs text-[#A3B5A0] hover:text-[#F1F0E9] font-medium flex items-center gap-1 transition-colors"
                      >
                        <span>Resume Doubt Session</span>
                        <ChevronRight className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
