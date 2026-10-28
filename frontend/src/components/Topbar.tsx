import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { NavTab } from './Sidebar';
import { api } from '../services/api';
import { ALL_SUBJECTS } from '../data/subjects';
import {
  Play,
  Menu,
  Flame,
  ChevronDown,
  Layers,
  Search,
  X,
  Code2,
  Atom,
  FlaskConical,
  Dna,
  Landmark,
  Globe2,
  TrendingUp,
  Languages,
  Scale,
  Leaf,
  BookOpen,
  Sparkles,
} from 'lucide-react';

interface TopbarProps {
  currentTab: NavTab;
  activeSubjectId?: string;
  onSelectSubject?: (id: string) => void;
  onOpenPractice: () => void;
  onToggleMobileMenu: () => void;
  accuracy: number;
  streakDays: number;
}

export const Topbar: React.FC<TopbarProps> = ({
  currentTab,
  activeSubjectId = 'mathematics',
  onSelectSubject,
  onOpenPractice,
  onToggleMobileMenu,
  accuracy,
  streakDays,
}) => {
  const [showSubjectDropdown, setShowSubjectDropdown] = useState(false);
  const [subjectSearch, setSubjectSearch] = useState('');

  const titles: Record<NavTab, { title: string; subtitle: string }> = {
    dashboard: {
      title: 'Universal Learning Dashboard',
      subtitle: 'Overview of learning state & multi-subject activity',
    },
    doubts: {
      title: 'AI Doubt Solver & Concept Explainer',
      subtitle: 'Ask questions, debug code, and explore step-by-step solutions',
    },
    subjects: {
      title: 'Subject Library & Syllabus Explorer',
      subtitle: 'Browse 11 core disciplines, chapters, formulas, and learning objectives',
    },
    practice: {
      title: 'Multi-Subject Practice Engine',
      subtitle: 'Adaptive problem solving with step-by-step feedback and review',
    },
    diagnosis: {
      title: 'Cognitive Misconception Diagnosis',
      subtitle: 'Dissecting root causes behind computational and conceptual errors',
    },
    progress: {
      title: 'Learning History & Mistake Audit',
      subtitle: 'Tracking mastery trajectory, mistake logs, and saved doubts',
    },
    teacher: {
      title: 'Teacher Cohort Insights',
      subtitle: 'Anonymous student performance heatmaps across disciplines',
    },
    settings: {
      title: 'Platform Preferences & Engine Settings',
      subtitle: 'Manage sensitivity thresholds, audio cues, and diagnostic data',
    },
  };

  const currentSubject =
    ALL_SUBJECTS.find((s) => s.id === activeSubjectId) || ALL_SUBJECTS[0];

  const filteredSubjects = ALL_SUBJECTS.filter((s) => {
    const q = subjectSearch.toLowerCase();
    return (
      s.name.toLowerCase().includes(q) ||
      s.categoryLabel.toLowerCase().includes(q) ||
      s.popularTopics.some((t) => t.toLowerCase().includes(q))
    );
  });

  const renderSubjectIcon = (iconName: string, className = 'w-4 h-4') => {
    switch (iconName) {
      case 'Code2':
        return <Code2 className={className} />;
      case 'Atom':
        return <Atom className={className} />;
      case 'FlaskConical':
        return <FlaskConical className={className} />;
      case 'Dna':
        return <Dna className={className} />;
      case 'Landmark':
        return <Landmark className={className} />;
      case 'Globe2':
        return <Globe2 className={className} />;
      case 'TrendingUp':
        return <TrendingUp className={className} />;
      case 'Languages':
        return <Languages className={className} />;
      case 'Scale':
        return <Scale className={className} />;
      case 'Leaf':
        return <Leaf className={className} />;
      default:
        return <BookOpen className={className} />;
    }
  };

  const isExternal = api.isConfiguredWithExternalBackend();

  return (
    <header className="h-16 bg-[#171A18]/90 backdrop-blur-xl border-b border-[#353C36] px-4 md:px-8 flex items-center justify-between gap-4 sticky top-0 z-30">
      {/* Left: Mobile menu toggle & page title */}
      <div className="flex items-center gap-3 text-left">
        <motion.button
          whileTap={{ scale: 0.92 }}
          onClick={onToggleMobileMenu}
          className="lg:hidden p-2 text-[#B5B9B0] hover:text-[#F1F0E9] rounded-lg hover:bg-white/5 transition-colors"
          aria-label="Toggle navigation"
        >
          <Menu className="w-5 h-5" />
        </motion.button>

        <div>
          <h2 className="text-sm md:text-base font-bold text-[#F1F0E9] tracking-tight flex items-center gap-2">
            <span>{titles[currentTab]?.title || 'AI That Teaches'}</span>
          </h2>
          <p className="text-xs text-[#858D83] hidden sm:block">
            {titles[currentTab]?.subtitle || ''}
          </p>
        </div>
      </div>

      {/* Middle/Right: Universal Subject Switcher & Status */}
      <div className="flex items-center gap-3">
        {/* Prominent Universal Subject Switcher Accessible from Any Screen */}
        <div className="relative">
          <motion.button
            whileTap={{ scale: 0.96 }}
            onClick={() => setShowSubjectDropdown(!showSubjectDropdown)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[#1D221E] hover:bg-[#222823] border border-[#353C36] hover:border-[#A3B5A0]/50 transition-all text-xs text-[#F1F0E9] group shadow-sm"
            title="Switch Active Academic Subject"
          >
            <span className="text-[#A3B5A0]">
              {renderSubjectIcon(currentSubject.icon, 'w-3.5 h-3.5')}
            </span>
            <span className="font-semibold text-xs hidden sm:inline">
              {currentSubject.name}
            </span>
            <span className="text-[10px] text-[#858D83] uppercase tracking-wider hidden md:inline px-1.5 py-0.5 rounded bg-[#222823] border border-[#353C36]">
              {currentSubject.categoryLabel}
            </span>
            <ChevronDown
              className={`w-3.5 h-3.5 text-[#858D83] group-hover:text-[#F1F0E9] transition-transform ${
                showSubjectDropdown ? 'rotate-180 text-[#A3B5A0]' : ''
              }`}
            />
          </motion.button>

          {/* Quick Subject Switcher Dropdown */}
          <AnimatePresence>
            {showSubjectDropdown && (
              <>
                <div
                  className="fixed inset-0 z-40"
                  onClick={() => setShowSubjectDropdown(false)}
                />
                <motion.div
                  initial={{ opacity: 0, scale: 0.96, y: 8 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.96, y: 8 }}
                  transition={{ duration: 0.18 }}
                  className="absolute right-0 top-12 w-80 md:w-96 rounded-2xl bg-[#1D221E] border border-[#353C36] shadow-2xl p-4 z-50 backdrop-blur-2xl text-left"
                >
                  <div className="flex items-center justify-between pb-3 border-b border-[#353C36]">
                    <div className="flex items-center gap-2 text-xs font-bold text-[#F1F0E9]">
                      <Layers className="w-4 h-4 text-[#A3B5A0]" />
                      <span>Universal Subject Switcher</span>
                    </div>
                    <button
                      onClick={() => setShowSubjectDropdown(false)}
                      className="p-1 rounded-lg text-[#858D83] hover:text-[#F1F0E9] hover:bg-white/5"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  {/* Search box inside dropdown */}
                  <div className="relative mt-3 mb-3">
                    <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-[#858D83]" />
                    <input
                      type="text"
                      value={subjectSearch}
                      onChange={(e) => setSubjectSearch(e.target.value)}
                      placeholder="Search subjects or topics..."
                      className="w-full pl-8 pr-3 py-1.5 rounded-xl bg-[#171A18] border border-[#353C36] text-xs text-[#F1F0E9] placeholder-[#858D83] focus:outline-none focus:border-[#A3B5A0]"
                      autoFocus
                    />
                  </div>

                  {/* Recent chips */}
                  <div className="flex items-center gap-1.5 mb-3 flex-wrap">
                    <span className="text-[10px] text-[#858D83] uppercase tracking-wider font-semibold">
                      Quick:
                    </span>
                    {['mathematics', 'programming', 'physics', 'history'].map(
                      (sId) => {
                        const sObj = ALL_SUBJECTS.find((x) => x.id === sId);
                        if (!sObj) return null;
                        const isSelected = activeSubjectId === sId;
                        return (
                          <button
                            key={sId}
                            onClick={() => {
                              onSelectSubject?.(sId);
                              setShowSubjectDropdown(false);
                            }}
                            className={`px-2 py-0.5 rounded-lg text-[10px] font-medium transition-colors ${
                              isSelected
                                ? 'bg-[#A3B5A0] text-[#171A18] font-bold'
                                : 'bg-[#222823] text-[#B5B9B0] hover:text-[#F1F0E9] border border-[#353C36]'
                            }`}
                          >
                            {sObj.name}
                          </button>
                        );
                      }
                    )}
                  </div>

                  {/* Subject List Grid */}
                  <div className="max-h-64 overflow-y-auto space-y-1.5 pr-1">
                    {filteredSubjects.map((sub) => {
                      const isSelected = activeSubjectId === sub.id;
                      return (
                        <button
                          key={sub.id}
                          onClick={() => {
                            onSelectSubject?.(sub.id);
                            setShowSubjectDropdown(false);
                          }}
                          className={`w-full flex items-center justify-between p-2 rounded-xl text-xs transition-all ${
                            isSelected
                              ? 'bg-[#283329] border border-[#A3B5A0]/40 text-[#F1F0E9]'
                              : 'hover:bg-[#222823] text-[#B5B9B0] hover:text-[#F1F0E9] border border-transparent'
                          }`}
                        >
                          <div className="flex items-center gap-2.5">
                            <span
                              className={`p-1.5 rounded-lg ${
                                isSelected
                                  ? 'bg-[#A3B5A0]/20 text-[#A3B5A0]'
                                  : 'bg-[#171A18] text-[#858D83]'
                              }`}
                            >
                              {renderSubjectIcon(sub.icon, 'w-3.5 h-3.5')}
                            </span>
                            <div className="text-left">
                              <div className="font-semibold text-xs leading-tight">
                                {sub.name}
                              </div>
                              <div className="text-[10px] text-[#858D83] truncate max-w-[190px]">
                                {sub.popularTopics.slice(0, 2).join(', ')}
                              </div>
                            </div>
                          </div>
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#171A18] text-[#858D83] border border-[#353C36]">
                            {sub.categoryLabel}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </motion.div>
              </>
            )}
          </AnimatePresence>
        </div>

        {/* Backend status badge */}
        <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[#1D221E] border border-[#353C36] text-xs backdrop-blur-md">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#8FBF9B] opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-[#8FBF9B]" />
          </span>
          <span className="text-[#858D83]">Engine:</span>
          <span className="text-[#F1F0E9] font-medium font-mono text-[11px]">
            {isExternal ? 'Python AI Server' : 'All-Subject AI'}
          </span>
        </div>

        {/* Streak indicator badge */}
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#1D221E] border border-[#D8BC86]/30 text-xs">
          <Flame className="w-3.5 h-3.5 text-[#D8BC86] fill-[#D8BC86]/30" />
          <span className="font-mono font-bold text-[#D8BC86] tabular-nums">
            {streakDays}d Streak
          </span>
        </div>

        {/* Learner accuracy badge */}
        <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[#1D221E] border border-[#8FBF9B]/30 text-xs font-mono">
          <span className="text-[#858D83]">Accuracy:</span>
          <span className="text-[#8FBF9B] font-semibold tabular-nums">
            {Math.round(accuracy)}%
          </span>
        </div>

        {/* Start Practice CTA */}
        {currentTab !== 'practice' && (
          <motion.button
            whileHover={{ scale: 1.03, y: -1 }}
            whileTap={{ scale: 0.97 }}
            onClick={onOpenPractice}
            className="px-4 py-2 bg-[#A3B5A0] hover:bg-[#B7C7B2] text-[#171A18] text-xs font-bold rounded-xl transition-all shadow-md flex items-center gap-1.5 whitespace-nowrap"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>Practice</span>
          </motion.button>
        )}
      </div>
    </header>
  );
};
