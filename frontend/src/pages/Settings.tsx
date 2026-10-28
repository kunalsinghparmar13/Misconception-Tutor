import React, { useState, useEffect } from 'react';
import { motion } from 'motion/react';
import {
  Settings as SettingsIcon,
  Bell,
  Cpu,
  Shield,
  Palette,
  Volume2,
  CheckCircle,
  AlertCircle,
  HelpCircle,
  Save,
  Layers,
  Code2,
  Sparkles,
  RotateCcw,
} from 'lucide-react';
import { ALL_SUBJECTS } from '../data/subjects';
import { aiService, BackendStatus } from '../services/aiService';
import { api } from '../services/api';

interface SettingsProps {
  onProgressReset?: () => Promise<void>;
}

export const Settings: React.FC<SettingsProps> = ({ onProgressReset }) => {
  const [preferredSubject, setPreferredSubject] = useState<string>(() => {
    try {
      return localStorage.getItem('ai_that_teaches_active_subject') || 'mathematics';
    } catch {
      return 'mathematics';
    }
  });
  const [explanationDepth, setExplanationDepth] = useState<string>('balanced');
  const [codeLanguage, setCodeLanguage] = useState<string>('python');
  const [soundEffects, setSoundEffects] = useState(true);
  const [hapticFeedback, setHapticFeedback] = useState(true);
  const [instantDiagnosis, setInstantDiagnosis] = useState(true);
  const [confidenceThreshold, setConfidenceThreshold] = useState(85);
  const [backendStatus, setBackendStatus] = useState<BackendStatus | null>(null);
  const [isSaved, setIsSaved] = useState(false);

  useEffect(() => {
    aiService.getBackendStatus().then(setBackendStatus);
  }, []);

  const handleSave = () => {
    try {
      localStorage.setItem('ai_that_teaches_active_subject', preferredSubject);
    } catch {}
    setIsSaved(true);
    setTimeout(() => setIsSaved(false), 2400);
  };

  const handleClearMistakes = () => {
    try {
      localStorage.removeItem('ai_that_teaches_mistake_review');
      setIsSaved(true);
      setTimeout(() => setIsSaved(false), 2000);
    } catch {}
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 text-left">
      {/* Header Banner */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-[#222823] via-[#1D221E] to-[#171A18] border border-[#353C36] p-6 lg:p-8 backdrop-blur-xl shadow-xl">
        <div className="absolute top-0 right-0 w-80 h-80 bg-[#A3B5A0]/5 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col sm:flex-row sm:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#283329] border border-[#A3B5A0]/30 text-xs font-semibold text-[#A3B5A0]">
              <SettingsIcon className="w-3.5 h-3.5 text-[#A3B5A0]" />
              <span>Platform Preferences & Multi-Subject Engine Settings</span>
            </div>
            <h1 className="text-3xl font-extrabold text-[#F1F0E9] tracking-tight">
              Platform &{' '}
              <span className="bg-gradient-to-r from-[#A3B5A0] to-[#B7C7B2] bg-clip-text text-transparent">
                Engine Settings
              </span>
            </h1>
            <p className="text-sm text-[#B5B9B0]">
              Configure default subject focus, AI explanation depth, diagnostic sensitivity, and data management policies.
            </p>
          </div>

          <button
            onClick={handleSave}
            className="px-6 py-3 rounded-xl bg-[#A3B5A0] hover:bg-[#B7C7B2] text-[#171A18] font-bold text-sm shadow-md transition-all flex items-center gap-2 shrink-0"
          >
            <Save className="w-4 h-4" />
            <span>Save Settings</span>
          </button>
        </div>
      </div>

      {isSaved && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
          className="p-4 rounded-xl bg-[#8FBF9B]/15 border border-[#8FBF9B]/30 text-[#8FBF9B] text-sm flex items-center gap-2.5"
        >
          <CheckCircle className="w-4 h-4 shrink-0" />
          <span>Configuration parameters synchronized successfully.</span>
        </motion.div>
      )}

      {/* Section 1: Academic Focus & AI Tutor Preferences */}
      <div className="p-6 rounded-2xl bg-[#222823] border border-[#353C36] space-y-6 shadow-md">
        <h2 className="text-base font-bold text-[#F1F0E9] flex items-center gap-2">
          <Layers className="w-4 h-4 text-[#A3B5A0]" />
          Academic Focus & Pedagogical Style
        </h2>

        <div className="space-y-4 divide-y divide-[#353C36]">
          {/* Default Subject */}
          <div className="pt-2 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="space-y-0.5">
              <div className="text-sm font-semibold text-[#F1F0E9]">Primary Focus Subject</div>
              <div className="text-xs text-[#858D83]">
                Default curriculum context loaded on startup across Practice and Doubt Solving.
              </div>
            </div>
            <select
              value={preferredSubject}
              onChange={(e) => setPreferredSubject(e.target.value)}
              className="px-3 py-2 rounded-xl bg-[#1D221E] border border-[#353C36] text-xs text-[#F1F0E9] focus:outline-none focus:border-[#A3B5A0]"
            >
              {ALL_SUBJECTS.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.categoryLabel})
                </option>
              ))}
            </select>
          </div>

          {/* Explanation Style */}
          <div className="pt-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="space-y-0.5">
              <div className="text-sm font-semibold text-[#F1F0E9]">AI Explanation Depth</div>
              <div className="text-xs text-[#858D83]">
                Controls the verbosity and mathematical rigor of AI responses.
              </div>
            </div>
            <div className="flex items-center gap-1.5 bg-[#1D221E] p-1 rounded-xl border border-[#353C36]">
              {['simpler', 'balanced', 'rigorous'].map((mode) => (
                <button
                  key={mode}
                  onClick={() => setExplanationDepth(mode)}
                  className={`px-3 py-1 text-xs font-semibold rounded-lg capitalize transition-colors ${
                    explanationDepth === mode
                      ? 'bg-[#A3B5A0] text-[#171A18]'
                      : 'text-[#858D83] hover:text-[#F1F0E9]'
                  }`}
                >
                  {mode}
                </button>
              ))}
            </div>
          </div>

          {/* Preferred Code Language */}
          <div className="pt-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="space-y-0.5">
              <div className="text-sm font-semibold text-[#F1F0E9]">Programming Language Target</div>
              <div className="text-xs text-[#858D83]">
                Default language for code debugging snippets and syntax highlighting.
              </div>
            </div>
            <select
              value={codeLanguage}
              onChange={(e) => setCodeLanguage(e.target.value)}
              className="px-3 py-2 rounded-xl bg-[#1D221E] border border-[#353C36] text-xs text-[#F1F0E9] focus:outline-none focus:border-[#A3B5A0]"
            >
              <option value="python">Python</option>
              <option value="javascript">JavaScript / TypeScript</option>
              <option value="cpp">C / C++</option>
              <option value="java">Java</option>
              <option value="sql">SQL</option>
            </select>
          </div>
        </div>
      </div>

      {/* Section 2: AI Backend & Diagnostic Engine Parameters */}
      <div className="p-6 rounded-2xl bg-[#222823] border border-[#353C36] space-y-6 shadow-md">
        <h2 className="text-base font-bold text-[#F1F0E9] flex items-center gap-2">
          <Cpu className="w-4 h-4 text-[#A3B5A0]" />
          Diagnostic Inference Engine Parameters
        </h2>

        <div className="space-y-4 divide-y divide-[#353C36]">
          {/* Engine Status */}
          <div className="pt-2 flex items-center justify-between">
            <div className="space-y-0.5">
              <div className="text-sm font-semibold text-[#F1F0E9]">AI Engine Core Status</div>
              <div className="text-xs text-[#858D83]">
                {backendStatus?.liveAiEnabled
                  ? 'Connected to Gemini 3.8 Flash via Google Gen AI server-side SDK.'
                  : 'Pedagogical heuristic engine active with step-by-step resolution.'}
              </div>
            </div>
            <span
              className={`px-3 py-1 rounded-xl text-xs font-mono font-bold border ${
                backendStatus?.liveAiEnabled
                  ? 'bg-[#8FBF9B]/15 text-[#8FBF9B] border-[#8FBF9B]/30'
                  : 'bg-[#D8BC86]/15 text-[#D8BC86] border-[#D8BC86]/30'
              }`}
            >
              {backendStatus?.liveAiEnabled ? 'Live Gemini AI' : 'Pedagogical Engine'}
            </span>
          </div>

          <div className="pt-4 flex items-center justify-between">
            <div className="space-y-0.5 max-w-lg">
              <div className="text-sm font-semibold text-[#F1F0E9]">Instant Option Evaluation</div>
              <div className="text-xs text-[#858D83]">
                Analyzes multiple-choice reasoning immediately upon selection.
              </div>
            </div>
            <button
              onClick={() => setInstantDiagnosis(!instantDiagnosis)}
              className={`w-12 h-6 rounded-full transition-colors relative p-0.5 border ${
                instantDiagnosis
                  ? 'bg-[#A3B5A0] border-[#A3B5A0]'
                  : 'bg-[#1D221E] border-[#353C36]'
              }`}
            >
              <div
                className={`w-5 h-5 rounded-full bg-[#171A18] transition-transform ${
                  instantDiagnosis ? 'translate-x-6' : 'translate-x-0'
                }`}
              />
            </button>
          </div>

          <div className="pt-4 space-y-2">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <div className="text-sm font-semibold text-[#F1F0E9]">
                  Confidence Classification Threshold ({confidenceThreshold}%)
                </div>
                <div className="text-xs text-[#858D83]">
                  Minimum probabilistic certainty required before designating an error as a systemic misconception.
                </div>
              </div>
              <span className="text-xs font-mono font-bold text-[#A3B5A0]">
                {confidenceThreshold}%
              </span>
            </div>
            <input
              type="range"
              min="50"
              max="99"
              value={confidenceThreshold}
              onChange={(e) => setConfidenceThreshold(Number(e.target.value))}
              className="w-full accent-[#A3B5A0] bg-[#1D221E] h-2 rounded-lg cursor-pointer"
            >
            </input>
          </div>
        </div>
      </div>

      {/* Section 3: Data & Reset Controls */}
      <div className="p-6 rounded-2xl bg-[#222823] border border-[#353C36] space-y-6 shadow-md">
        <h2 className="text-base font-bold text-[#F1F0E9] flex items-center gap-2">
          <Palette className="w-4 h-4 text-[#A3B5A0]" />
          Visual Theme & Data Hygiene
        </h2>

        <div className="space-y-4 divide-y divide-[#353C36]">
          <div className="pt-2 flex items-center justify-between">
            <div className="space-y-0.5">
              <div className="text-sm font-semibold text-[#F1F0E9]">Design Theme</div>
              <div className="text-xs text-[#858D83]">Minimal Charcoal & Muted Sage Green Palette</div>
            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[#1D221E] border border-[#353C36]">
              <span className="w-3 h-3 rounded-full bg-[#A3B5A0]" />
              <span className="w-3 h-3 rounded-full bg-[#8FBF9B]" />
              <span className="w-3 h-3 rounded-full bg-[#171A18] border border-[#353C36]" />
              <span className="text-xs font-medium text-[#F1F0E9] ml-1">Minimal Sage</span>
            </div>
          </div>

          <div className="pt-4 flex items-center justify-between">
            <div className="space-y-0.5">
              <div className="text-sm font-semibold text-[#F1F0E9]">Clear Mistake Review Queue</div>
              <div className="text-xs text-[#858D83]">
                Empties your recorded problem review log for spaced repetition.
              </div>
            </div>
            <button
              onClick={handleClearMistakes}
              className="px-3.5 py-1.5 rounded-xl bg-[#1D221E] hover:bg-[#283329] border border-[#353C36] text-xs font-semibold text-[#F1F0E9] transition-colors"
            >
              Clear Mistakes
            </button>
          </div>

          <div className="pt-4 flex items-center justify-between">
            <div className="space-y-0.5">
              <div className="text-sm font-semibold text-[#D98E8E]">Reset Complete Diagnostic Profile</div>
              <div className="text-xs text-[#858D83]">
                Clears recorded attempts, misconceptions history, and streak metrics back to baseline.
              </div>
            </div>
            <button
              onClick={async () => {
                await api.resetLearnerProgress();
                if (onProgressReset) await onProgressReset();
                setIsSaved(true);
              }}
              className="px-3.5 py-1.5 rounded-xl bg-[#D98E8E]/15 hover:bg-[#D98E8E]/25 border border-[#D98E8E]/30 text-xs font-semibold text-[#D98E8E] transition-colors"
            >
              Reset Data
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
