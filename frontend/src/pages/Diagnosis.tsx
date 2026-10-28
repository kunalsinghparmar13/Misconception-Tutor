import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Misconception, Question, DiagnosisResult } from '../types/education';
import { KNOWN_MISCONCEPTIONS } from '../services/mockData';
import { ALL_SUBJECTS } from '../data/subjects';
import { MisconceptionCard } from '../components/MisconceptionCard';
import { TargetedPracticeModal } from '../components/TargetedPracticeModal';
import { WhyWeThinkThisAccordion } from '../components/WhyWeThinkThisAccordion';
import { api } from '../services/api';
import {
  Brain,
  Sparkles,
  Zap,
  Filter,
  CheckCircle,
  AlertTriangle,
  Lightbulb,
  Search,
  BookOpen,
  ArrowRight,
  ArrowLeft,
  Layers,
  Code2,
  Atom,
} from 'lucide-react';

interface DiagnosisProps {
  diagnosis: DiagnosisResult | null;
  onContinuePractice: () => void;
  onReturnToDashboard: () => void;
}

export const Diagnosis: React.FC<DiagnosisProps> = ({
  diagnosis,
  onContinuePractice,
  onReturnToDashboard,
}) => {
  const [misconceptions, setMisconceptions] = useState<Misconception[]>([]);
  const [filterSeverity, setFilterSeverity] = useState<string>('all');
  const [filterSubject, setFilterSubject] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedForModal, setSelectedForModal] = useState<{
    misconception: Misconception;
    question: Question;
  } | null>(null);
  const [activeTab, setActiveTab] = useState<'latest' | 'catalog' | 'cognitive-lens' | 'simulator'>(
    diagnosis ? 'latest' : 'catalog'
  );
  const [simA, setSimA] = useState(1);
  const [simB, setSimB] = useState(4);
  const [simC, setSimC] = useState(1);
  const [simD, setSimD] = useState(6);
  const [simDomain, setSimDomain] = useState<'fractions' | 'python' | 'physics'>('fractions');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadCatalog();
  }, []);

  useEffect(() => {
    if (diagnosis) {
      setActiveTab('latest');
    }
  }, [diagnosis]);

  const loadCatalog = async () => {
    setIsLoading(true);
    try {
      const list = Object.values(KNOWN_MISCONCEPTIONS);
      setMisconceptions(list);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  const filtered = misconceptions.filter((m) => {
    const matchesSev =
      filterSeverity === 'all' || m.severity.toLowerCase() === filterSeverity.toLowerCase();
    const matchesSubj =
      filterSubject === 'all' ||
      (m.subjectId && m.subjectId.toLowerCase() === filterSubject.toLowerCase()) ||
      (!m.subjectId && filterSubject === 'mathematics');
    const matchesSearch =
      m.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.friendlyDescription.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.explanation.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSev && matchesSubj && matchesSearch;
  });

  const handleLaunchPractice = async (m: Misconception) => {
    const q = await api.fetchTargetedQuestion(m.code);
    setSelectedForModal({ misconception: m, question: q });
  };

  return (
    <div className="space-y-8 text-left">
      {/* Header Banner */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-[#222823] via-[#1D221E] to-[#171A18] border border-[#353C36] p-6 lg:p-8 backdrop-blur-xl shadow-xl">
        <div className="absolute top-0 right-0 w-80 h-80 bg-[#A3B5A0]/5 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-3 max-w-2xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#283329] border border-[#A3B5A0]/30 text-xs font-semibold text-[#A3B5A0]">
              <Brain className="w-3.5 h-3.5 text-[#A3B5A0]" />
              <span>Cross-Discipline Cognitive Diagnostics & Misconception Taxonomy</span>
            </div>
            <h1 className="text-3xl lg:text-4xl font-extrabold text-[#F1F0E9] tracking-tight">
              Cognitive{' '}
              <span className="bg-gradient-to-r from-[#A3B5A0] to-[#B7C7B2] bg-clip-text text-transparent">
                Diagnosis Hub
              </span>
            </h1>
            <p className="text-sm text-[#B5B9B0] leading-relaxed">
              Student errors across STEM, programming, languages, and humanities are rarely random slips.
              They reflect specific mental model divergences. Our diagnostic engine isolates these patterns,
              provides verifiable evidence traces, and prescribes targeted corrective practice.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            {diagnosis && (
              <button
                onClick={() => setActiveTab('latest')}
                className={`px-4 py-2.5 rounded-xl text-xs font-bold transition-all ${
                  activeTab === 'latest'
                    ? 'bg-[#A3B5A0] text-[#171A18] shadow-md'
                    : 'bg-[#1D221E] text-[#B5B9B0] hover:text-[#F1F0E9] border border-[#353C36]'
                }`}
              >
                Latest Diagnosis
              </button>
            )}
            <button
              onClick={() => setActiveTab('catalog')}
              className={`px-4 py-2.5 rounded-xl text-xs font-bold transition-all ${
                activeTab === 'catalog'
                  ? 'bg-[#A3B5A0] text-[#171A18] shadow-md'
                  : 'bg-[#1D221E] text-[#B5B9B0] hover:text-[#F1F0E9] border border-[#353C36]'
              }`}
            >
              Taxonomy Catalog ({misconceptions.length})
            </button>
            <button
              onClick={() => setActiveTab('cognitive-lens')}
              className={`px-4 py-2.5 rounded-xl text-xs font-bold transition-all ${
                activeTab === 'cognitive-lens'
                  ? 'bg-[#A3B5A0] text-[#171A18] shadow-md'
                  : 'bg-[#1D221E] text-[#B5B9B0] hover:text-[#F1F0E9] border border-[#353C36]'
              }`}
            >
              Why We Think This
            </button>
            <button
              onClick={() => setActiveTab('simulator')}
              className={`px-4 py-2.5 rounded-xl text-xs font-bold transition-all ${
                activeTab === 'simulator'
                  ? 'bg-[#A3B5A0] text-[#171A18] shadow-md'
                  : 'bg-[#1D221E] text-[#B5B9B0] hover:text-[#F1F0E9] border border-[#353C36]'
              }`}
            >
              Bug & Counter-Example Simulator
            </button>
          </div>
        </div>
      </div>

      {/* Latest Diagnosis Tab */}
      {activeTab === 'latest' && diagnosis && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-[#F1F0E9] flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-[#A3B5A0]" />
              Active Problem Diagnosis Evaluation
            </h2>
            <div className="flex gap-2">
              <button
                onClick={onContinuePractice}
                className="px-4 py-2 rounded-xl bg-[#A3B5A0] hover:bg-[#B7C7B2] text-[#171A18] font-bold text-xs flex items-center gap-1.5 shadow-md transition-colors"
              >
                <span>Continue Practice</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={onReturnToDashboard}
                className="px-4 py-2 rounded-xl bg-[#1D221E] border border-[#353C36] text-[#B5B9B0] hover:text-[#F1F0E9] text-xs font-medium transition-colors"
              >
                Dashboard
              </button>
            </div>
          </div>

          <MisconceptionCard
            misconception={diagnosis.misconception}
            confidence={diagnosis.confidence}
            isLowConfidence={diagnosis.isLowConfidence}
            explanation={diagnosis.explanation}
          />

          {diagnosis.whyWeThinkThis && (
            <WhyWeThinkThisAccordion evidence={diagnosis.whyWeThinkThis} defaultOpen={true} />
          )}

          {diagnosis.targetedQuestion && (
            <div className="p-6 rounded-2xl bg-[#222823] border border-[#353C36] flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="space-y-1">
                <div className="text-xs font-semibold text-[#A3B5A0] uppercase tracking-wider">
                  Recommended Immediate Remediation
                </div>
                <div className="text-sm font-bold text-[#F1F0E9]">
                  {diagnosis.targetedQuestion.topicTitle}
                </div>
                <p className="text-xs text-[#B5B9B0]">
                  {diagnosis.targetedQuestion.prompt}
                </p>
              </div>
              <button
                onClick={() => {
                  if (diagnosis.misconception && diagnosis.targetedQuestion) {
                    setSelectedForModal({
                      misconception: diagnosis.misconception,
                      question: diagnosis.targetedQuestion,
                    });
                  }
                }}
                className="px-5 py-2.5 rounded-xl bg-[#A3B5A0] hover:bg-[#B7C7B2] text-[#171A18] font-bold text-xs shadow-md transition-all flex items-center gap-1.5 shrink-0"
              >
                <Zap className="w-4 h-4 fill-current" />
                <span>Launch Micro-Practice</span>
              </button>
            </div>
          )}
        </div>
      )}

      {/* Catalog Tab */}
      {activeTab === 'catalog' && (
        <div className="space-y-6">
          {/* Controls Bar: Search & Filters */}
          <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-4 p-4 rounded-2xl bg-[#222823] border border-[#353C36] backdrop-blur-md">
            {/* Search */}
            <div className="relative flex-1 max-w-md">
              <Search className="w-4 h-4 text-[#858D83] absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search cognitive bugs by symptom, remedy..."
                className="w-full pl-10 pr-4 py-2 rounded-xl bg-[#171A18] border border-[#353C36] focus:border-[#A3B5A0] focus:outline-none text-xs text-[#F1F0E9] placeholder-[#858D83] transition-colors"
              />
            </div>

            {/* Filter by Subject */}
            <div className="flex items-center gap-2 overflow-x-auto pb-1 lg:pb-0">
              <span className="text-[11px] font-semibold text-[#858D83] uppercase tracking-wider shrink-0 flex items-center gap-1">
                <Layers className="w-3 h-3 text-[#A3B5A0]" />
                Subject:
              </span>
              <select
                value={filterSubject}
                onChange={(e) => setFilterSubject(e.target.value)}
                className="px-3 py-1.5 rounded-xl bg-[#171A18] border border-[#353C36] text-xs text-[#F1F0E9] focus:outline-none focus:border-[#A3B5A0]"
              >
                <option value="all">All Subjects</option>
                {ALL_SUBJECTS.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>

              {/* Severity Filter Pills */}
              <div className="flex items-center gap-1 ml-2">
                {['all', 'high', 'medium', 'low'].map((sev) => (
                  <button
                    key={sev}
                    onClick={() => setFilterSeverity(sev)}
                    className={`px-2.5 py-1 rounded-lg text-[11px] font-medium capitalize transition-all shrink-0 ${
                      filterSeverity === sev
                        ? 'bg-[#283329] text-[#A3B5A0] border border-[#A3B5A0]/40'
                        : 'text-[#858D83] hover:text-[#F1F0E9] hover:bg-[#1D221E]'
                    }`}
                  >
                    {sev === 'all' ? 'All' : sev}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Catalog Cards Grid */}
          {isLoading ? (
            <div className="text-center py-16">
              <div className="w-8 h-8 border-2 border-[#A3B5A0] border-t-transparent rounded-full animate-spin mx-auto mb-3" />
              <p className="text-xs text-[#858D83]">Parsing cognitive diagnosis repository...</p>
            </div>
          ) : filtered.length === 0 ? (
            <div className="p-12 text-center rounded-2xl bg-[#222823] border border-[#353C36] text-[#858D83]">
              <AlertTriangle className="w-6 h-6 mx-auto mb-2 text-[#D8BC86]" />
              <p className="text-sm font-semibold text-[#F1F0E9]">No misconceptions found</p>
              <p className="text-xs mt-1">Try clearing your search query or subject filters.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {filtered.map((m, idx) => (
                <motion.div
                  key={m.id}
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.04 }}
                  className="p-6 rounded-2xl bg-[#222823] border border-[#353C36] hover:border-[#A3B5A0]/40 transition-all space-y-4 shadow-lg flex flex-col justify-between"
                >
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="px-2.5 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider bg-[#283329] border border-[#A3B5A0]/30 text-[#A3B5A0]">
                          {m.code}
                        </span>
                        {m.subjectId && (
                          <span className="text-[10px] text-[#858D83] font-mono capitalize">
                            {m.subjectId}
                          </span>
                        )}
                      </div>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                          m.severity === 'high'
                            ? 'bg-[#D98E8E]/15 border border-[#D98E8E]/30 text-[#D98E8E]'
                            : m.severity === 'medium'
                            ? 'bg-[#D8BC86]/15 border border-[#D8BC86]/30 text-[#D8BC86]'
                            : 'bg-[#8FBF9B]/15 border border-[#8FBF9B]/30 text-[#8FBF9B]'
                        }`}
                      >
                        {m.severity} Severity
                      </span>
                    </div>

                    <h3 className="text-base font-bold text-[#F1F0E9]">
                      {m.title}
                    </h3>

                    <p className="text-xs text-[#B5B9B0] leading-relaxed">
                      {m.friendlyDescription}
                    </p>

                    <div className="p-3 rounded-xl bg-[#171A18] border border-[#353C36] space-y-1">
                      <div className="text-[11px] font-semibold text-[#D8BC86]">Observed Pattern:</div>
                      <div className="font-mono text-xs text-[#F1F0E9]">{m.examplePattern}</div>
                    </div>

                    <p className="text-xs text-[#8FBF9B] leading-relaxed">
                      <span className="font-semibold text-[#B5B9B0]">Remedy:</span> {m.remedyStrategy}
                    </p>
                  </div>

                  <div className="pt-2 flex justify-end">
                    <button
                      onClick={() => handleLaunchPractice(m)}
                      className="px-4 py-2 rounded-xl bg-[#283329] hover:bg-[#A3B5A0] text-[#A3B5A0] hover:text-[#171A18] border border-[#A3B5A0]/30 font-semibold text-xs transition-all flex items-center gap-1.5"
                    >
                      <Zap className="w-3.5 h-3.5 fill-current" />
                      <span>Targeted Practice</span>
                    </button>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Cognitive Lens Tab */}
      {activeTab === 'cognitive-lens' && (
        <div className="space-y-6">
          <div className="p-6 rounded-2xl bg-[#222823] border border-[#353C36] backdrop-blur-md">
            <h2 className="text-lg font-bold text-[#F1F0E9] flex items-center gap-2 mb-2">
              <Sparkles className="w-4 h-4 text-[#A3B5A0]" />
              Explainable AI Diagnostic Evidence Ledger
            </h2>
            <p className="text-xs text-[#B5B9B0] max-w-2xl leading-relaxed">
              Inspect how the AI reasoning engine maps student errors directly to underlying pedagogical
              misconceptions across Mathematics, Programming, Physics, Chemistry, Biology, History, and English.
            </p>
          </div>

          <div className="space-y-4">
            {misconceptions.map((item) => (
              <WhyWeThinkThisAccordion
                key={item.id}
                evidence={{
                  observedPattern: `Pattern: ${item.examplePattern}`,
                  studentMentalStep: item.friendlyDescription,
                  underlyingGap: item.explanation,
                  counterExample: item.remedyStrategy,
                }}
              />
            ))}
          </div>
        </div>
      )}

      {/* Bug & Counter-Example Simulator Tab */}
      {activeTab === 'simulator' && (
        <div className="space-y-6">
          <div className="p-6 rounded-2xl bg-[#222823] border border-[#353C36]">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-bold text-[#F1F0E9] flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-[#A3B5A0]" />
                  Buggy Rule Fingerprint & Counter-Example Sandbox
                </h2>
                <p className="text-xs text-[#B5B9B0] mt-1 max-w-xl">
                  Test numbers or concepts live against canonical cognitive bugs. See why buggy rules feel right, what wrong answers they predict, and the counter-examples that expose them.
                </p>
              </div>

              {/* Domain Switcher */}
              <div className="flex items-center rounded-xl bg-[#1D221E] border border-[#353C36] p-1 text-xs">
                {(['fractions', 'python', 'physics'] as const).map((dom) => (
                  <button
                    key={dom}
                    onClick={() => setSimDomain(dom)}
                    className={`px-3 py-1.5 rounded-lg capitalize transition-colors ${
                      simDomain === dom
                        ? 'bg-[#283329] text-[#A3B5A0] font-bold border border-[#A3B5A0]/40'
                        : 'text-[#858D83] hover:text-[#F1F0E9]'
                    }`}
                  >
                    {dom === 'fractions' ? 'Fractions (Math)' : dom === 'python' ? 'Python Memory' : 'Newtonian Physics'}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Domain 1: Fraction Bugs */}
          {simDomain === 'fractions' && (
            <div className="space-y-6">
              <div className="p-6 rounded-2xl bg-[#222823] border border-[#353C36] space-y-5">
                <div className="text-xs font-bold text-[#A3B5A0] uppercase tracking-wider">
                  1. Interactive Expression Inputs: a/b + c/d
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  <div className="p-3 rounded-xl bg-[#1D221E] border border-[#353C36] text-center">
                    <label className="text-[10px] text-[#858D83] block uppercase font-mono">Numerator A</label>
                    <input
                      type="number"
                      min={1}
                      max={12}
                      value={simA}
                      onChange={(e) => setSimA(Math.max(1, Number(e.target.value)))}
                      className="w-16 bg-transparent text-center font-bold text-lg text-[#F1F0E9] focus:outline-none"
                    />
                  </div>
                  <div className="p-3 rounded-xl bg-[#1D221E] border border-[#353C36] text-center">
                    <label className="text-[10px] text-[#858D83] block uppercase font-mono">Denominator B</label>
                    <input
                      type="number"
                      min={2}
                      max={20}
                      value={simB}
                      onChange={(e) => setSimB(Math.max(2, Number(e.target.value)))}
                      className="w-16 bg-transparent text-center font-bold text-lg text-[#F1F0E9] focus:outline-none"
                    />
                  </div>
                  <div className="p-3 rounded-xl bg-[#1D221E] border border-[#353C36] text-center">
                    <label className="text-[10px] text-[#858D83] block uppercase font-mono">Numerator C</label>
                    <input
                      type="number"
                      min={1}
                      max={12}
                      value={simC}
                      onChange={(e) => setSimC(Math.max(1, Number(e.target.value)))}
                      className="w-16 bg-transparent text-center font-bold text-lg text-[#F1F0E9] focus:outline-none"
                    />
                  </div>
                  <div className="p-3 rounded-xl bg-[#1D221E] border border-[#353C36] text-center">
                    <label className="text-[10px] text-[#858D83] block uppercase font-mono">Denominator D</label>
                    <input
                      type="number"
                      min={2}
                      max={20}
                      value={simD}
                      onChange={(e) => setSimD(Math.max(2, Number(e.target.value)))}
                      className="w-16 bg-transparent text-center font-bold text-lg text-[#F1F0E9] focus:outline-none"
                    />
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-[#171A18] border border-[#353C36] flex items-center justify-between text-sm font-mono">
                  <span className="text-[#858D83]">Expression:</span>
                  <span className="text-[#F1F0E9] text-base font-bold">
                    {simA}/{simB} + {simC}/{simD}
                  </span>
                  <span className="text-[#8FBF9B]">
                    Correct: {(simA * simD + simB * simC)}/{(simB * simD)}
                  </span>
                </div>
              </div>

              {/* Bug Predictions Grid */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* M1 */}
                <div className="p-5 rounded-2xl bg-[#222823] border border-[#353C36] space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-[#D98E8E]/15 text-[#D98E8E] font-bold">
                      BUG M1
                    </span>
                    <span className="text-[10px] text-[#858D83]">Add Across</span>
                  </div>
                  <h4 className="font-bold text-xs text-[#F1F0E9]">Adds Tops and Bottoms</h4>
                  <div className="p-3 rounded-xl bg-[#171A18] font-mono text-center">
                    <div className="text-[10px] text-[#858D83]">({simA}+{simC}) / ({simB}+{simD})</div>
                    <div className="text-xl font-bold text-[#D98E8E] mt-1">
                      {simA + simC}/{simB + simD}
                    </div>
                  </div>
                  <p className="text-[11px] text-[#B5B9B0] leading-relaxed">
                    <strong>Mental Error:</strong> Treats the fraction as two independent addition problems.
                  </p>
                  <div className="p-2.5 rounded-lg bg-[#283329] border border-[#A3B5A0]/20 text-[11px] text-[#A3B5A0]">
                    <strong>Counter-Example:</strong> 1/2 + 1/2 = 2/4 = 1/2. Adding slices gives back half!
                  </div>
                </div>

                {/* M2 */}
                <div className="p-5 rounded-2xl bg-[#222823] border border-[#353C36] space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-[#D8BC86]/15 text-[#D8BC86] font-bold">
                      BUG M2
                    </span>
                    <span className="text-[10px] text-[#858D83]">Add Top, Mult Bottom</span>
                  </div>
                  <h4 className="font-bold text-xs text-[#F1F0E9]">Multiply Denominators Directly</h4>
                  <div className="p-3 rounded-xl bg-[#171A18] font-mono text-center">
                    <div className="text-[10px] text-[#858D83]">({simA}+{simC}) / ({simB}×{simD})</div>
                    <div className="text-xl font-bold text-[#D8BC86] mt-1">
                      {simA + simC}/{simB * simD}
                    </div>
                  </div>
                  <p className="text-[11px] text-[#B5B9B0] leading-relaxed">
                    <strong>Mental Error:</strong> Multiplies bottoms to find common denominator without scaling tops.
                  </p>
                  <div className="p-2.5 rounded-lg bg-[#283329] border border-[#A3B5A0]/20 text-[11px] text-[#A3B5A0]">
                    <strong>Counter-Example:</strong> 1/4 + 1/4 = 2/16 = 1/8. Slices shrunk instead of grew!
                  </div>
                </div>

                {/* M3 */}
                <div className="p-5 rounded-2xl bg-[#222823] border border-[#353C36] space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-[#9EB8CC]/15 text-[#9EB8CC] font-bold">
                      BUG M3
                    </span>
                    <span className="text-[10px] text-[#858D83]">No Top Scaling</span>
                  </div>
                  <h4 className="font-bold text-xs text-[#F1F0E9]">Common Denom Without Scale</h4>
                  <div className="p-3 rounded-xl bg-[#171A18] font-mono text-center">
                    <div className="text-[10px] text-[#858D83]">({simA}+{simC}) / lcm({simB}, {simD})</div>
                    <div className="text-xl font-bold text-[#9EB8CC] mt-1">
                      {simA + simC}/{simB === simD ? simB : simB * simD}
                    </div>
                  </div>
                  <p className="text-[11px] text-[#B5B9B0] leading-relaxed">
                    <strong>Mental Error:</strong> Remembers to find LCD, but simply adds unscaled numerators.
                  </p>
                  <div className="p-2.5 rounded-lg bg-[#283329] border border-[#A3B5A0]/20 text-[11px] text-[#A3B5A0]">
                    <strong>Counter-Example:</strong> 1/2 + 1/4 = (1+1)/4 = 2/4 = 1/2. Adding 1/4 made no change!
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Domain 2: Python Code Bugs */}
          {simDomain === 'python' && (
            <div className="p-6 rounded-2xl bg-[#222823] border border-[#353C36] space-y-5">
              <h3 className="text-sm font-bold text-[#8CC8FF] flex items-center gap-2">
                <Code2 className="w-4 h-4 text-[#8CC8FF]" />
                Python Mental Bug: Mutable Default Arguments (Shared Memory State)
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 rounded-xl bg-[#121413] border border-[#D98E8E]/40 space-y-2">
                  <div className="text-[10px] font-mono text-[#D98E8E] font-bold uppercase">
                    Buggy Code (What Student Writes):
                  </div>
                  <pre className="text-xs font-mono text-[#F1F0E9] overflow-x-auto leading-relaxed">
{`# Default parameter instantiated ONCE at definition:
def add_to_list(val, items=[]):
    items.append(val)
    return items

print(add_to_list('a'))  # ['a']
print(add_to_list('b'))  # ['a', 'b']  <-- BUG! Expects ['b']`}
                  </pre>
                </div>

                <div className="p-4 rounded-xl bg-[#121413] border border-[#8FBF9B]/40 space-y-2">
                  <div className="text-[10px] font-mono text-[#8FBF9B] font-bold uppercase">
                    Corrected Implementation (Idiomatic Python):
                  </div>
                  <pre className="text-xs font-mono text-[#F1F0E9] overflow-x-auto leading-relaxed">
{`# Use None as immutable sentinel:
def add_to_list(val, items=None):
    if items is None:
        items = []  # Fresh heap object per call
    items.append(val)
    return items

print(add_to_list('a'))  # ['a']
print(add_to_list('b'))  # ['b']  <-- Correct isolated state!`}
                  </pre>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-[#283329] border border-[#A3B5A0]/30 text-xs text-[#A3B5A0]">
                <strong>Diagnostic Explanation:</strong> In Python, default parameters are evaluated when function definitions are executed, not when functions are called. Therefore, a mutable list is shared by all calls that do not provide an explicit argument.
              </div>
            </div>
          )}

          {/* Domain 3: Physics Action-Reaction */}
          {simDomain === 'physics' && (
            <div className="p-6 rounded-2xl bg-[#222823] border border-[#353C36] space-y-5">
              <h3 className="text-sm font-bold text-[#D8BC86] flex items-center gap-2">
                <Atom className="w-4 h-4 text-[#D8BC86]" />
                Physics Mental Bug: Newton's Third Law (Forces on Same Body Fallacy)
              </h3>

              <div className="p-4 rounded-xl bg-[#1D221E] border border-[#353C36] space-y-3">
                <div className="text-xs text-[#F1F0E9]">
                  <strong>Classic Horse & Cart Paradox:</strong> If the horse pulls the cart forward with force F, and the cart pulls the horse backward with equal force -F, why does the cart accelerate forward at all?
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                  <div className="p-3.5 rounded-xl bg-[#121413] border border-[#D98E8E]/30 space-y-1.5">
                    <div className="text-[11px] font-bold text-[#D98E8E]">Buggy Mental Model:</div>
                    <p className="text-xs text-[#B5B9B0] leading-relaxed">
                      Believes F and -F cancel each other out on the same object, resulting in net zero force (ΣF = 0).
                    </p>
                  </div>

                  <div className="p-3.5 rounded-xl bg-[#121413] border border-[#8FBF9B]/30 space-y-1.5">
                    <div className="text-[11px] font-bold text-[#8FBF9B]">Physical Reality:</div>
                    <p className="text-xs text-[#B5B9B0] leading-relaxed">
                      Action and reaction forces act on <strong>two different objects</strong>! The only horizontal force on the cart is the forward pull from the horse.
                    </p>
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-[#283329] border border-[#A3B5A0]/30 text-xs text-[#A3B5A0]">
                  <strong>Key Takeaway:</strong> To determine if an object moves, you only sum the forces acting ON that single object. External forces between different objects never cancel on one free-body diagram.
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Standalone Practice Modal */}
      {selectedForModal && (
        <TargetedPracticeModal
          initialQuestion={selectedForModal.question}
          misconceptionTitle={selectedForModal.misconception.title}
          onClose={() => setSelectedForModal(null)}
          onComplete={() => setSelectedForModal(null)}
        />
      )}
    </div>
  );
};
