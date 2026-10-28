import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { ALL_SUBJECTS } from '../data/subjects';
import { Subject, SubjectCategory, SubjectTopic } from '../types/subjects';
import {
  Search,
  Filter,
  BookOpen,
  ArrowRight,
  Sparkles,
  Zap,
  CheckCircle2,
  Plus,
  Layers,
  ChevronRight,
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
  X,
} from 'lucide-react';

interface SubjectsPageProps {
  onSelectTopicForPractice: (subjectId: string, topicId?: string) => void;
  onAskDoubtAboutTopic: (subjectId: string, topicTitle: string) => void;
}

export const SubjectsPage: React.FC<SubjectsPageProps> = ({
  onSelectTopicForPractice,
  onAskDoubtAboutTopic,
}) => {
  const [subjectsList, setSubjectsList] = useState<Subject[]>(ALL_SUBJECTS);
  const [selectedCategory, setSelectedCategory] = useState<SubjectCategory | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [activeSubject, setActiveSubject] = useState<Subject>(ALL_SUBJECTS[0]);
  const [activeTopic, setActiveTopic] = useState<SubjectTopic | null>(ALL_SUBJECTS[0].topics[0] || null);

  // Custom Subject Modal State
  const [showAddCustomModal, setShowAddCustomModal] = useState(false);
  const [customName, setCustomName] = useState('');
  const [customCategory, setCustomCategory] = useState<SubjectCategory>('custom');
  const [customDescription, setCustomDescription] = useState('');
  const [customTopicTitle, setCustomTopicTitle] = useState('');

  // Completed Topics stored in localStorage
  const [completedTopicIds, setCompletedTopicIds] = useState<string[]>(() => {
    try {
      const raw = localStorage.getItem('ai_that_teaches_completed_topics');
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  });

  const toggleTopicCompleted = (topicId: string) => {
    let updated: string[];
    if (completedTopicIds.includes(topicId)) {
      updated = completedTopicIds.filter((id) => id !== topicId);
    } else {
      updated = [...completedTopicIds, topicId];
    }
    setCompletedTopicIds(updated);
    localStorage.setItem('ai_that_teaches_completed_topics', JSON.stringify(updated));
  };

  const handleAddCustomSubject = (e: React.FormEvent) => {
    e.preventDefault();
    if (!customName.trim()) return;

    const newSub: Subject = {
      id: `custom-${Date.now()}`,
      name: customName.trim(),
      category: customCategory,
      categoryLabel: 'Custom Discipline',
      icon: 'BookOpen',
      description: customDescription.trim() || 'Custom academic domain configured by user.',
      tagline: 'Custom learning curriculum',
      accentColor: '#A3B5A0',
      popularTopics: [customTopicTitle.trim() || 'Core Foundations'],
      topics: [
        {
          id: `topic-${Date.now()}`,
          title: customTopicTitle.trim() || 'General Curriculum',
          description: 'User-specified study module.',
          subtopics: ['Concepts', 'Applications', 'Problem Solving'],
          difficulty: 'medium',
          learningObjectives: ['Explore fundamental mechanisms in this domain'],
        },
      ],
      isCustom: true,
    };

    const updated = [newSub, ...subjectsList];
    setSubjectsList(updated);
    setActiveSubject(newSub);
    setActiveTopic(newSub.topics[0]);
    setShowAddCustomModal(false);
    setCustomName('');
    setCustomDescription('');
    setCustomTopicTitle('');
  };

  const filteredSubjects = subjectsList.filter((s) => {
    const matchesCat = selectedCategory === 'all' || s.category === selectedCategory;
    const matchesQuery =
      s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.topics.some((t) => t.title.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesCat && matchesQuery;
  });

  const renderSubjectIcon = (iconName: string, sizeClass = 'w-5 h-5') => {
    switch (iconName) {
      case 'Code2':
        return <Code2 className={sizeClass} />;
      case 'Atom':
        return <Atom className={sizeClass} />;
      case 'FlaskConical':
        return <FlaskConical className={sizeClass} />;
      case 'Dna':
        return <Dna className={sizeClass} />;
      case 'Landmark':
        return <Landmark className={sizeClass} />;
      case 'Globe2':
        return <Globe2 className={sizeClass} />;
      case 'TrendingUp':
        return <TrendingUp className={sizeClass} />;
      case 'Languages':
        return <Languages className={sizeClass} />;
      case 'Scale':
        return <Scale className={sizeClass} />;
      case 'Leaf':
        return <Leaf className={sizeClass} />;
      default:
        return <BookOpen className={sizeClass} />;
    }
  };

  return (
    <div className="space-y-8">
      {/* Header Banner */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-[#222823] via-[#1D221E] to-[#171A18] border border-[#353C36] p-6 lg:p-8 backdrop-blur-xl shadow-xl">
        <div className="absolute top-0 right-0 w-80 h-80 bg-[#A3B5A0]/5 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#283329] border border-[#A3B5A0]/30 text-xs font-semibold text-[#A3B5A0]">
              <Layers className="w-3.5 h-3.5 text-[#A3B5A0]" />
              <span>Universal Academic Curriculum & Topic Explorer</span>
            </div>
            <h1 className="text-3xl font-extrabold text-[#F1F0E9] tracking-tight">
              Subject Library &{' '}
              <span className="bg-gradient-to-r from-[#A3B5A0] to-[#B7C7B2] bg-clip-text text-transparent">
                Syllabus Navigator
              </span>
            </h1>
            <p className="text-sm text-[#B5B9B0] max-w-xl">
              Browse structured chapters across 11 core disciplines, inspect learning objectives and formulas,
              and seamlessly launch practice sets or ask AI questions.
            </p>
          </div>

          <div className="flex gap-2.5">
            <button
              onClick={() => setShowAddCustomModal(true)}
              className="px-4 py-2.5 rounded-xl bg-[#292F2A] hover:bg-[#343E34] border border-[#353C36] text-[#F1F0E9] text-xs font-medium flex items-center gap-2 transition-colors shrink-0"
            >
              <Plus className="w-4 h-4 text-[#A3B5A0]" />
              <span>Add Custom Topic</span>
            </button>
          </div>
        </div>
      </div>

      {/* Search and Category Filter Bar */}
      <div className="flex flex-col md:flex-row items-center justify-between gap-4 p-4 rounded-2xl bg-[#222823] border border-[#353C36]">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-[#858D83] absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search subjects, chapters, formulas..."
            className="w-full pl-10 pr-4 py-2 rounded-xl bg-[#1D221E] border border-[#353C36] text-xs text-[#F1F0E9] placeholder-[#858D83] focus:border-[#A3B5A0] focus:outline-none transition-colors"
          />
        </div>

        {/* Category Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto w-full md:w-auto pb-1 md:pb-0 text-xs">
          {[
            { id: 'all', label: 'All Subjects' },
            { id: 'stem', label: 'STEM' },
            { id: 'coding', label: 'Programming' },
            { id: 'humanities', label: 'Humanities' },
            { id: 'languages', label: 'Languages' },
            { id: 'commerce', label: 'Commerce' },
            { id: 'social', label: 'Social Sciences' },
          ].map((cat) => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id as any)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all shrink-0 ${
                selectedCategory === cat.id
                  ? 'bg-[#283329] text-[#A3B5A0] border border-[#A3B5A0]/40'
                  : 'text-[#B5B9B0] hover:text-[#F1F0E9] hover:bg-[#1D221E]'
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main Two-Column Explorer: Subjects Column + Deep Topic Detail Column */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Subject Card Selection Grid */}
        <div className="lg:col-span-5 space-y-3">
          <h2 className="text-sm font-bold text-[#F1F0E9] flex items-center justify-between">
            <span>Disciplines ({filteredSubjects.length})</span>
            <span className="text-[11px] text-[#858D83]">Click to inspect syllabus</span>
          </h2>

          <div className="space-y-2.5 max-h-[640px] overflow-y-auto pr-1">
            {filteredSubjects.map((sub) => {
              const isSelected = activeSubject.id === sub.id;
              return (
                <motion.div
                  key={sub.id}
                  whileHover={{ scale: 1.01 }}
                  onClick={() => {
                    setActiveSubject(sub);
                    setActiveTopic(sub.topics[0] || null);
                  }}
                  className={`p-4 rounded-2xl border cursor-pointer transition-all ${
                    isSelected
                      ? 'bg-[#283329]/80 border-[#A3B5A0] shadow-md'
                      : 'bg-[#222823] border-[#353C36] hover:border-[#353C36]/90'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-9 h-9 rounded-xl flex items-center justify-center border ${
                          isSelected
                            ? 'bg-[#A3B5A0] text-[#171A18] border-[#A3B5A0]'
                            : 'bg-[#1D221E] text-[#A3B5A0] border-[#353C36]'
                        }`}
                      >
                        {renderSubjectIcon(sub.icon)}
                      </div>
                      <div>
                        <div className="text-xs font-semibold text-[#858D83] uppercase tracking-wider">
                          {sub.categoryLabel}
                        </div>
                        <h3 className="text-sm font-bold text-[#F1F0E9]">{sub.name}</h3>
                      </div>
                    </div>

                    <span className="text-[11px] font-mono text-[#858D83]">
                      {sub.topics.length} chapters
                    </span>
                  </div>

                  <p className="mt-2 text-xs text-[#B5B9B0] line-clamp-1">
                    {sub.description}
                  </p>
                </motion.div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Deep Topic Inspector & Chapter Syllabus */}
        <div className="lg:col-span-7 space-y-4">
          <div className="p-6 rounded-3xl bg-[#222823] border border-[#353C36] shadow-xl space-y-6 text-left">
            {/* Subject Overview Header */}
            <div className="flex items-start justify-between gap-4 pb-4 border-b border-[#353C36]">
              <div className="space-y-1">
                <span className="text-[11px] font-mono font-semibold text-[#A3B5A0] uppercase tracking-wider">
                  {activeSubject.categoryLabel} Syllabus
                </span>
                <h2 className="text-2xl font-bold text-[#F1F0E9]">{activeSubject.name}</h2>
                <p className="text-xs text-[#B5B9B0]">{activeSubject.description}</p>
              </div>

              <button
                onClick={() => onSelectTopicForPractice(activeSubject.id)}
                className="px-4 py-2.5 rounded-xl bg-[#A3B5A0] text-[#171A18] font-bold text-xs flex items-center gap-2 shadow-md hover:bg-[#B7C7B2] transition-colors shrink-0"
              >
                <Zap className="w-3.5 h-3.5 fill-current" />
                <span>Practice Subject</span>
              </button>
            </div>

            {/* Chapter Selection Pills */}
            <div className="space-y-2">
              <span className="text-xs font-semibold text-[#A3B5A0]">Available Chapters:</span>
              <div className="flex flex-wrap gap-2">
                {activeSubject.topics.map((t) => {
                  const isTopicActive = activeTopic?.id === t.id;
                  const isDone = completedTopicIds.includes(t.id);
                  return (
                    <button
                      key={t.id}
                      onClick={() => setActiveTopic(t)}
                      className={`px-3 py-1.5 rounded-xl text-xs transition-all flex items-center gap-1.5 ${
                        isTopicActive
                          ? 'bg-[#A3B5A0] text-[#171A18] font-bold'
                          : 'bg-[#1D221E] text-[#B5B9B0] border border-[#353C36] hover:text-[#F1F0E9]'
                      }`}
                    >
                      {isDone && <CheckCircle2 className="w-3.5 h-3.5 text-[#8FBF9B]" />}
                      <span>{t.title}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Selected Topic Detailed Overview */}
            {activeTopic && (
              <motion.div
                key={activeTopic.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-5 rounded-2xl bg-[#1D221E] border border-[#353C36] space-y-4"
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h3 className="text-base font-bold text-[#F1F0E9] flex items-center gap-2">
                      <span>{activeTopic.title}</span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-[#292F2A] text-[#A3B5A0] border border-[#353C36]">
                        {activeTopic.difficulty}
                      </span>
                    </h3>
                    <p className="text-xs text-[#B5B9B0] mt-1">{activeTopic.description}</p>
                  </div>

                  <button
                    onClick={() => toggleTopicCompleted(activeTopic.id)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium border flex items-center gap-1.5 transition-colors shrink-0 ${
                      completedTopicIds.includes(activeTopic.id)
                        ? 'bg-[#283329] border-[#8FBF9B] text-[#8FBF9B]'
                        : 'bg-[#222823] border-[#353C36] text-[#858D83] hover:text-[#F1F0E9]'
                    }`}
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>{completedTopicIds.includes(activeTopic.id) ? 'Mastered' : 'Mark Understood'}</span>
                  </button>
                </div>

                {/* Subtopic Modules */}
                <div className="space-y-1.5">
                  <div className="text-xs font-semibold text-[#A3B5A0]">Subtopics & Modules:</div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {activeTopic.subtopics.map((st, i) => (
                      <div
                        key={i}
                        className="p-2.5 rounded-xl bg-[#222823] border border-[#353C36] text-xs text-[#B5B9B0] flex items-center gap-2"
                      >
                        <span className="w-1.5 h-1.5 rounded-full bg-[#A3B5A0]" />
                        <span>{st}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Key Rules / Formulas if any */}
                {activeTopic.keyRulesOrFormulas && activeTopic.keyRulesOrFormulas.length > 0 && (
                  <div className="p-3.5 rounded-xl bg-[#222823] border border-[#353C36] space-y-1.5">
                    <div className="text-xs font-semibold text-[#D8BC86]">Key Rules & Formulas:</div>
                    <ul className="space-y-1">
                      {activeTopic.keyRulesOrFormulas.map((rule, idx) => (
                        <li key={idx} className="text-xs text-[#F1F0E9] font-mono flex items-start gap-2">
                          <span className="text-[#A3B5A0] font-bold">›</span>
                          <span>{rule}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Learning Objectives */}
                {activeTopic.learningObjectives && activeTopic.learningObjectives.length > 0 && (
                  <div className="space-y-1 text-xs">
                    <div className="font-semibold text-[#A3B5A0]">Learning Objectives:</div>
                    <ul className="space-y-1">
                      {activeTopic.learningObjectives.map((obj, i) => (
                        <li key={i} className="text-[#B5B9B0] flex items-start gap-2">
                          <span className="w-1.5 h-1.5 rounded-full bg-[#8FBF9B] mt-1.5 shrink-0" />
                          <span>{obj}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Action Launcher Bar */}
                <div className="pt-2 flex flex-wrap gap-2.5">
                  <button
                    onClick={() => onSelectTopicForPractice(activeSubject.id, activeTopic.id)}
                    className="px-4 py-2 rounded-xl bg-[#A3B5A0] hover:bg-[#B7C7B2] text-[#171A18] font-bold text-xs flex items-center gap-2 shadow-sm transition-colors"
                  >
                    <Zap className="w-3.5 h-3.5 fill-current" />
                    <span>Practice Questions for this Chapter</span>
                  </button>

                  <button
                    onClick={() => onAskDoubtAboutTopic(activeSubject.id, activeTopic.title)}
                    className="px-4 py-2 rounded-xl bg-[#222823] hover:bg-[#292F2A] border border-[#353C36] text-[#F1F0E9] text-xs font-medium flex items-center gap-2 transition-colors"
                  >
                    <Sparkles className="w-3.5 h-3.5 text-[#A3B5A0]" />
                    <span>Ask AI Doubt About this Chapter</span>
                  </button>
                </div>
              </motion.div>
            )}
          </div>
        </div>
      </div>

      {/* Custom Subject Modal */}
      <AnimatePresence>
        {showAddCustomModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="w-full max-w-md p-6 rounded-3xl bg-[#222823] border border-[#353C36] space-y-4 shadow-2xl text-left"
            >
              <div className="flex items-center justify-between">
                <h3 className="text-base font-bold text-[#F1F0E9] flex items-center gap-2">
                  <Plus className="w-4 h-4 text-[#A3B5A0]" />
                  Add Custom Subject / Module
                </h3>
                <button
                  onClick={() => setShowAddCustomModal(false)}
                  className="p-1 rounded-lg text-[#858D83] hover:text-[#F1F0E9]"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <form onSubmit={handleAddCustomSubject} className="space-y-3 text-xs">
                <div>
                  <label className="block text-[#B5B9B0] mb-1 font-medium">Subject / Topic Name:</label>
                  <input
                    type="text"
                    required
                    value={customName}
                    onChange={(e) => setCustomName(e.target.value)}
                    placeholder="e.g., Organic Reaction Mechanisms, Game Theory..."
                    className="w-full px-3 py-2 rounded-xl bg-[#1D221E] border border-[#353C36] text-xs text-[#F1F0E9] focus:border-[#A3B5A0] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-[#B5B9B0] mb-1 font-medium">Category:</label>
                  <select
                    value={customCategory}
                    onChange={(e) => setCustomCategory(e.target.value as any)}
                    className="w-full px-3 py-2 rounded-xl bg-[#1D221E] border border-[#353C36] text-xs text-[#F1F0E9] focus:border-[#A3B5A0] focus:outline-none"
                  >
                    <option value="custom">Custom / Interdisciplinary</option>
                    <option value="stem">STEM</option>
                    <option value="coding">Programming</option>
                    <option value="humanities">Humanities</option>
                    <option value="languages">Languages</option>
                    <option value="commerce">Commerce</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[#B5B9B0] mb-1 font-medium">Initial Chapter Name:</label>
                  <input
                    type="text"
                    value={customTopicTitle}
                    onChange={(e) => setCustomTopicTitle(e.target.value)}
                    placeholder="e.g., Chapter 1: Foundational Principles"
                    className="w-full px-3 py-2 rounded-xl bg-[#1D221E] border border-[#353C36] text-xs text-[#F1F0E9] focus:border-[#A3B5A0] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-[#B5B9B0] mb-1 font-medium">Description:</label>
                  <textarea
                    rows={3}
                    value={customDescription}
                    onChange={(e) => setCustomDescription(e.target.value)}
                    placeholder="Brief description of what you're studying in this custom subject..."
                    className="w-full px-3 py-2 rounded-xl bg-[#1D221E] border border-[#353C36] text-xs text-[#F1F0E9] focus:border-[#A3B5A0] focus:outline-none"
                  />
                </div>

                <div className="pt-2 flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setShowAddCustomModal(false)}
                    className="px-4 py-2 rounded-xl bg-[#1D221E] text-[#B5B9B0] text-xs"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 rounded-xl bg-[#A3B5A0] text-[#171A18] font-bold text-xs"
                  >
                    Create Subject
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};
