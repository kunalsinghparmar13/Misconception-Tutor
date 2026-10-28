import React, { useState } from 'react';
import { motion } from 'motion/react';
import { LearnerProgress } from '../types/education';
import { ALL_SUBJECTS } from '../data/subjects';
import { Subject, SubjectCategory } from '../types/subjects';
import { AnimatedCounter } from '../components/AnimatedCounter';
import { ProgressRing } from '../components/ProgressRing';
import { TiltCard } from '../components/TiltCard';
import {
  Sparkles,
  Zap,
  Target,
  Flame,
  CheckCircle2,
  Clock,
  ArrowRight,
  TrendingUp,
  Award,
  Search,
  BookOpen,
  Code2,
  Atom,
  FlaskConical,
  Dna,
  Landmark,
  Globe2,
  Languages,
  Scale,
  Leaf,
  Layers,
  HelpCircle,
  MessageSquareQuote,
  RotateCcw,
} from 'lucide-react';

interface DashboardProps {
  progress: LearnerProgress;
  onStartPractice: (topicOrSubject?: string) => void;
  onNavigateToProgress: () => void;
  onNavigateToDiagnosis: () => void;
  onNavigateToDoubtSolver: (subjectId?: string) => void;
  onNavigateToSubjects: () => void;
  hasActiveDiagnosis: boolean;
}

export const Dashboard: React.FC<DashboardProps> = ({
  progress,
  onStartPractice,
  onNavigateToProgress,
  onNavigateToDiagnosis,
  onNavigateToDoubtSolver,
  onNavigateToSubjects,
  hasActiveDiagnosis,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<SubjectCategory | 'all'>('all');

  const filteredSubjects = ALL_SUBJECTS.filter((s) => {
    const matchesCat = selectedCategory === 'all' || s.category === selectedCategory;
    const matchesSearch =
      s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.popularTopics.some((t) => t.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesCat && matchesSearch;
  });

  const renderSubjectIcon = (iconName: string) => {
    switch (iconName) {
      case 'Code2':
        return <Code2 className="w-5 h-5 text-[#8CC8FF]" />;
      case 'Atom':
        return <Atom className="w-5 h-5 text-[#D8BC86]" />;
      case 'FlaskConical':
        return <FlaskConical className="w-5 h-5 text-[#8FBF9B]" />;
      case 'Dna':
        return <Dna className="w-5 h-5 text-[#A3B5A0]" />;
      case 'Landmark':
        return <Landmark className="w-5 h-5 text-[#D8BC86]" />;
      case 'Globe2':
        return <Globe2 className="w-5 h-5 text-[#9EB8CC]" />;
      case 'TrendingUp':
        return <TrendingUp className="w-5 h-5 text-[#8FBF9B]" />;
      case 'Languages':
        return <Languages className="w-5 h-5 text-[#B7C7B2]" />;
      case 'Scale':
        return <Scale className="w-5 h-5 text-[#D98E8E]" />;
      case 'Leaf':
        return <Leaf className="w-5 h-5 text-[#8FBF9B]" />;
      default:
        return <BookOpen className="w-5 h-5 text-[#A3B5A0]" />;
    }
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.06 },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 14 },
    show: { opacity: 1, y: 0, transition: { duration: 0.4 } },
  };

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="space-y-8"
    >
      {/* Hero Welcome & Search Banner */}
      <motion.div
        variants={itemVariants}
        className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-[#222823] via-[#1D221E] to-[#171A18] border border-[#353C36] p-6 lg:p-8 backdrop-blur-xl shadow-xl"
      >
        <div className="absolute top-0 right-0 w-96 h-96 bg-[#A3B5A0]/5 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 space-y-6 max-w-4xl">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#283329] border border-[#A3B5A0]/30 text-xs font-semibold text-[#A3B5A0]">
            <Sparkles className="w-3.5 h-3.5 animate-pulse text-[#A3B5A0]" />
            <span>Comprehensive Academic AI Learning Platform 2030</span>
          </div>

          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-[#F1F0E9] leading-tight">
            Learn Anything with{' '}
            <span className="bg-gradient-to-r from-[#A3B5A0] via-[#B7C7B2] to-[#A3B5A0] bg-clip-text text-transparent">
              Adaptive AI Guidance
            </span>
          </h1>

          <p className="text-sm text-[#B5B9B0] max-w-2xl leading-relaxed">
            Ask doubts across 11 major academic disciplines, practice step-by-step problem solving,
            debug computer code, inspect historical timelines, and eliminate cognitive misconceptions.
          </p>

          {/* Global Search Bar */}
          <div className="relative max-w-2xl">
            <Search className="w-5 h-5 text-[#858D83] absolute left-4 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="What do you want to learn today? (e.g. Newton's laws, Python recursion, French revolution...)"
              className="w-full pl-12 pr-4 py-3.5 rounded-2xl bg-[#1D221E] border border-[#353C36] focus:border-[#A3B5A0] focus:ring-4 focus:ring-[#A3B5A0]/15 text-xs sm:text-sm text-[#F1F0E9] placeholder-[#858D83] focus:outline-none transition-all shadow-inner"
            />
          </div>

          {/* Quick Action Buttons */}
          <div className="flex flex-wrap gap-3 pt-1">
            <button
              onClick={() => onNavigateToDoubtSolver()}
              className="px-5 py-2.5 rounded-xl bg-[#A3B5A0] hover:bg-[#B7C7B2] text-[#171A18] font-bold text-xs flex items-center gap-2 shadow-md transition-all duration-200"
            >
              <MessageSquareQuote className="w-4 h-4 fill-current" />
              <span>Ask an AI Doubt</span>
            </button>

            <button
              onClick={() => onStartPractice()}
              className="px-5 py-2.5 rounded-xl bg-[#292F2A] hover:bg-[#343E34] border border-[#353C36] text-[#F1F0E9] font-medium text-xs flex items-center gap-2 transition-all duration-200"
            >
              <Zap className="w-4 h-4 text-[#A3B5A0]" />
              <span>Practice Questions</span>
            </button>

            <button
              onClick={onNavigateToSubjects}
              className="px-5 py-2.5 rounded-xl bg-[#292F2A] hover:bg-[#343E34] border border-[#353C36] text-[#F1F0E9] font-medium text-xs flex items-center gap-2 transition-all duration-200"
            >
              <Layers className="w-4 h-4 text-[#A3B5A0]" />
              <span>Explore All Subjects</span>
            </button>
          </div>
        </div>
      </motion.div>

      {/* Real Progress Metrics Row */}
      <motion.div variants={itemVariants} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1: Overall Accuracy */}
        <TiltCard
          glowColor="rgba(163, 181, 160, 0.12)"
          className="p-5 rounded-2xl bg-[#222823] border border-[#353C36] hover:border-[#A3B5A0]/35 transition-colors shadow-md text-left"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase tracking-wider font-semibold text-[#858D83]">
              Overall Accuracy
            </span>
            <div className="w-8 h-8 rounded-lg bg-[#283329] border border-[#A3B5A0]/30 flex items-center justify-center text-[#A3B5A0]">
              <Target className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-[#F1F0E9]">
              <AnimatedCounter value={Math.round(progress.accuracy)} />
            </span>
            <span className="text-xs font-semibold text-[#8FBF9B] flex items-center gap-0.5">
              <TrendingUp className="w-3.5 h-3.5" /> verified
            </span>
          </div>
          <div className="mt-3 h-1.5 w-full bg-[#1D221E] rounded-full overflow-hidden border border-[#353C36]/50">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${progress.accuracy}%` }}
              transition={{ duration: 1, ease: 'easeOut', delay: 0.3 }}
              className="h-full bg-gradient-to-r from-[#A3B5A0] to-[#8FBF9B] rounded-full"
            />
          </div>
        </TiltCard>

        {/* Metric 2: Daily Streak */}
        <TiltCard
          glowColor="rgba(163, 181, 160, 0.12)"
          className="p-5 rounded-2xl bg-[#222823] border border-[#353C36] hover:border-[#A3B5A0]/35 transition-colors shadow-md text-left"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase tracking-wider font-semibold text-[#858D83]">
              Daily Streak
            </span>
            <div className="w-8 h-8 rounded-lg bg-[#283329] border border-[#A3B5A0]/30 flex items-center justify-center text-[#A3B5A0]">
              <Flame className="w-4 h-4 fill-current animate-pulse" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-[#F1F0E9]">
              <AnimatedCounter value={progress.activeStreakDays} />
            </span>
            <span className="text-xs text-[#858D83]">active days</span>
          </div>
          <div className="mt-3 flex gap-1">
            {[1, 2, 3, 4, 5, 6, 7].map((day) => (
              <div
                key={day}
                className={`h-1.5 flex-1 rounded-full ${
                  day <= (progress.activeStreakDays % 7 || 7) ? 'bg-[#A3B5A0]' : 'bg-[#292F2A]'
                }`}
              />
            ))}
          </div>
        </TiltCard>

        {/* Metric 3: Problems Solved */}
        <TiltCard
          glowColor="rgba(143, 191, 155, 0.12)"
          className="p-5 rounded-2xl bg-[#222823] border border-[#353C36] hover:border-[#8FBF9B]/35 transition-colors shadow-md text-left"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase tracking-wider font-semibold text-[#858D83]">
              Problems Evaluated
            </span>
            <div className="w-8 h-8 rounded-lg bg-[#1D221E] border border-[#8FBF9B]/30 flex items-center justify-center text-[#8FBF9B]">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-[#F1F0E9]">
              <AnimatedCounter value={progress.totalAttempted} />
            </span>
            <span className="text-xs text-[#858D83]">({progress.totalCorrect} correct)</span>
          </div>
          <div className="mt-3 flex items-center gap-1.5 text-xs text-[#8FBF9B]">
            <Award className="w-3.5 h-3.5" />
            <span>Active cross-subject sessions</span>
          </div>
        </TiltCard>

        {/* Metric 4: Cognitive Diagnostics */}
        <TiltCard
          glowColor="rgba(216, 188, 134, 0.12)"
          className="p-5 rounded-2xl bg-[#222823] border border-[#353C36] hover:border-[#D8BC86]/40 transition-colors shadow-md text-left"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase tracking-wider font-semibold text-[#858D83]">
              Diagnostic Tracking
            </span>
            <div className="w-8 h-8 rounded-lg bg-[#D8BC86]/10 border border-[#D8BC86]/30 flex items-center justify-center text-[#D8BC86]">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-[#F1F0E9]">
              {progress.misconceptionBugRates.filter((m) => m.status !== 'Mastered').length}
            </span>
            <span className="text-xs text-[#D8BC86]">active focus points</span>
          </div>
          <div className="mt-3 flex items-center gap-1.5 text-xs text-[#858D83]">
            <span className="w-2 h-2 rounded-full bg-[#8FBF9B]" />
            <span>{progress.misconceptionBugRates.filter((m) => m.status === 'Mastered').length} mastered models</span>
          </div>
        </TiltCard>
      </motion.div>

      {/* Universal Subject Catalog Explorer */}
      <motion.div variants={itemVariants} className="space-y-4 text-left">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold text-[#F1F0E9] flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#A3B5A0]" />
              Subject Hub & Disciplines
            </h2>
            <p className="text-xs text-[#858D83]">
              Select a discipline to practice questions or ask AI doubts
            </p>
          </div>

          {/* Category filter pills */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
            {[
              { id: 'all', label: 'All' },
              { id: 'stem', label: 'STEM' },
              { id: 'coding', label: 'Programming' },
              { id: 'humanities', label: 'Humanities' },
              { id: 'languages', label: 'Languages' },
              { id: 'commerce', label: 'Commerce' },
            ].map((cat) => (
              <button
                key={cat.id}
                onClick={() => setSelectedCategory(cat.id as any)}
                className={`px-3 py-1 rounded-lg text-xs font-medium transition-all ${
                  selectedCategory === cat.id
                    ? 'bg-[#283329] text-[#A3B5A0] border border-[#A3B5A0]/40'
                    : 'text-[#858D83] hover:text-[#F1F0E9] bg-[#1D221E]'
                }`}
              >
                {cat.label}
              </button>
            ))}
          </div>
        </div>

        {/* Subjects Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredSubjects.map((sub) => (
            <motion.div
              key={sub.id}
              whileHover={{ y: -3 }}
              className="p-5 rounded-2xl bg-[#222823] border border-[#353C36] hover:border-[#A3B5A0]/40 transition-all shadow-md space-y-3 flex flex-col justify-between"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className="w-9 h-9 rounded-xl bg-[#1D221E] border border-[#353C36] flex items-center justify-center">
                      {renderSubjectIcon(sub.icon)}
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-[#F1F0E9]">{sub.name}</h3>
                      <span className="text-[10px] text-[#858D83] font-mono">{sub.categoryLabel}</span>
                    </div>
                  </div>
                  <span className="text-[11px] text-[#A3B5A0] font-mono">
                    {sub.topics.length} topics
                  </span>
                </div>

                <p className="text-xs text-[#B5B9B0] line-clamp-2 leading-relaxed">
                  {sub.description}
                </p>

                <div className="flex flex-wrap gap-1 pt-1">
                  {sub.popularTopics.slice(0, 2).map((top, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-0.5 rounded text-[10px] bg-[#1D221E] border border-[#353C36] text-[#858D83]"
                    >
                      {top}
                    </span>
                  ))}
                </div>
              </div>

              <div className="pt-2 flex items-center justify-between border-t border-[#353C36]/60">
                <button
                  onClick={() => onNavigateToDoubtSolver(sub.id)}
                  className="text-xs text-[#A3B5A0] hover:text-[#F1F0E9] font-medium flex items-center gap-1 transition-colors"
                >
                  <span>Ask Doubt</span>
                  <ArrowRight className="w-3 h-3" />
                </button>

                <button
                  onClick={() => onStartPractice(sub.id)}
                  className="px-3 py-1.5 rounded-lg bg-[#283329] hover:bg-[#A3B5A0] text-[#A3B5A0] hover:text-[#171A18] border border-[#A3B5A0]/30 text-xs font-semibold transition-all flex items-center gap-1.5"
                >
                  <Zap className="w-3 h-3 fill-current" />
                  <span>Practice</span>
                </button>
              </div>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </motion.div>
  );
};
