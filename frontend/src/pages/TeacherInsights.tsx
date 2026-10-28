import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { TeacherInsights as TeacherInsightsType } from '../types/education';
import { ALL_SUBJECTS } from '../data/subjects';
import { TeacherHeatmap } from '../components/TeacherHeatmap';
import { api } from '../services/api';
import {
  Users,
  AlertTriangle,
  Lightbulb,
  CheckCircle2,
  FileSpreadsheet,
  Download,
  Share2,
  Sparkles,
  Layers,
  ArrowRight,
  TrendingDown,
  BookOpen,
  Filter,
} from 'lucide-react';

interface SubjectStruggleData {
  subjectId: string;
  subjectName: string;
  averageAccuracy: number;
  topMisconception: string;
  studentsAtRisk: number;
  recommendedIntervention: string;
}

const MULTI_SUBJECT_CLASS_DATA: SubjectStruggleData[] = [
  {
    subjectId: 'mathematics',
    subjectName: 'Mathematics',
    averageAccuracy: 68,
    topMisconception: 'Adding Numerators & Denominators Directly',
    studentsAtRisk: 7,
    recommendedIntervention: 'Conduct 15-minute visual fraction partitioning exercise using common denominator area models.',
  },
  {
    subjectId: 'programming',
    subjectName: 'Programming & CS',
    averageAccuracy: 74,
    topMisconception: 'Mutable Default Argument State Sharing (Python)',
    studentsAtRisk: 5,
    recommendedIntervention: 'Review memory stack vs heap diagrams and demonstrate `arg=None` guard idiom.',
  },
  {
    subjectId: 'physics',
    subjectName: 'Physics',
    averageAccuracy: 62,
    topMisconception: 'Action-Reaction Believed to Act on Same Body',
    studentsAtRisk: 9,
    recommendedIntervention: 'Practice drawing isolated free-body diagrams for interacting pairs (Earth hooves vs cart).',
  },
  {
    subjectId: 'chemistry',
    subjectName: 'Chemistry',
    averageAccuracy: 71,
    topMisconception: 'Apparent Mass Loss in Open Gas Reactions',
    studentsAtRisk: 4,
    recommendedIntervention: 'Show mass conservation in sealed versus open flask experiments on a digital scale.',
  },
  {
    subjectId: 'biology',
    subjectName: 'Biology',
    averageAccuracy: 79,
    topMisconception: 'Lamarckian Inheritance of Acquired Traits',
    studentsAtRisk: 3,
    recommendedIntervention: 'Clarify germline vs somatic mutation boundaries through Darwinian variation simulations.',
  },
  {
    subjectId: 'history',
    subjectName: 'History',
    averageAccuracy: 81,
    topMisconception: 'Presentism (Judging 18th-century actors by 21st-century norms)',
    studentsAtRisk: 3,
    recommendedIntervention: 'Analyze 1789 cahiers de doléances primary source documents to reconstruct contemporary perspectives.',
  },
  {
    subjectId: 'english',
    subjectName: 'English & Languages',
    averageAccuracy: 76,
    topMisconception: 'Intervening Prepositional Phrase Agreement Trap',
    studentsAtRisk: 6,
    recommendedIntervention: 'Drill sentence bracket parsing to cross out intervening prepositional phrases.',
  },
];

export const TeacherInsights: React.FC = () => {
  const [insights, setInsights] = useState<TeacherInsightsType | null>(null);
  const [selectedSubjectId, setSelectedSubjectId] = useState<string>('all');
  const [isLoading, setIsLoading] = useState(true);
  const [copiedShare, setCopiedShare] = useState(false);

  useEffect(() => {
    loadInsights();
  }, []);

  const loadInsights = async () => {
    setIsLoading(true);
    try {
      const data = await api.fetchTeacherInsights();
      setInsights(data);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleExportCSV = () => {
    if (!insights) return;
    const rows = [
      ['Student ID', 'Overall Accuracy (%)', 'Subject', 'Struggle Topic', 'Intervention Needed'],
      ...insights.learners.map((l, idx) => {
        const riskSubject = MULTI_SUBJECT_CLASS_DATA[idx % MULTI_SUBJECT_CLASS_DATA.length];
        return [
          l.anonymousId,
          l.accuracy.toString(),
          riskSubject.subjectName,
          riskSubject.topMisconception,
          l.accuracy < 70 ? 'Immediate Small Group' : 'Independent Practice',
        ];
      }),
    ];

    const csvContent =
      'data:text/csv;charset=utf-8,' + rows.map((e) => e.map(cell => `"${cell}"`).join(',')).join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `cohort_subject_diagnostics_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleShareReport = () => {
    setCopiedShare(true);
    setTimeout(() => setCopiedShare(false), 2000);
  };

  if (isLoading || !insights) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] space-y-3">
        <div className="w-8 h-8 border-2 border-[#A3B5A0] border-t-transparent rounded-full animate-spin" />
        <p className="text-xs text-[#858D83]">Aggregating multi-subject classroom cognitive heatmaps...</p>
      </div>
    );
  }

  const filteredMultiSubject =
    selectedSubjectId === 'all'
      ? MULTI_SUBJECT_CLASS_DATA
      : MULTI_SUBJECT_CLASS_DATA.filter((s) => s.subjectId === selectedSubjectId);

  return (
    <div className="space-y-8 text-left">
      {/* Header Banner */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-[#222823] via-[#1D221E] to-[#171A18] border border-[#353C36] p-6 lg:p-8 backdrop-blur-xl shadow-xl">
        <div className="absolute top-0 right-0 w-80 h-80 bg-[#A3B5A0]/5 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-3 max-w-2xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#283329] border border-[#A3B5A0]/30 text-xs font-semibold text-[#A3B5A0]">
              <Users className="w-3.5 h-3.5 text-[#A3B5A0]" />
              <span>Multi-Subject Cohort Analytics & Differentiated Teaching</span>
            </div>
            <h1 className="text-3xl lg:text-4xl font-extrabold text-[#F1F0E9] tracking-tight">
              Classroom{' '}
              <span className="bg-gradient-to-r from-[#A3B5A0] to-[#B7C7B2] bg-clip-text text-transparent">
                Cognitive Bug Matrix
              </span>
            </h1>
            <p className="text-sm text-[#B5B9B0] leading-relaxed">
              Identify student clusters sharing identical misconceptions across all academic subjects.
              Group students automatically for targeted small-group intervention and export diagnostic rosters.
            </p>
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleExportCSV}
              className="px-4 py-2.5 rounded-xl bg-[#A3B5A0] hover:bg-[#B7C7B2] text-[#171A18] font-bold text-xs flex items-center gap-2 shadow-md transition-all shrink-0"
            >
              <Download className="w-4 h-4" />
              <span>Export Roster CSV</span>
            </button>
            <button
              onClick={handleShareReport}
              className="p-2.5 rounded-xl bg-[#1D221E] hover:bg-[#222823] border border-[#353C36] text-[#B5B9B0] hover:text-[#F1F0E9] transition-colors"
              title="Share report link"
            >
              <Share2 className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Multi-Subject Filter & Overview Cards */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-xs font-bold text-[#F1F0E9]">
            <Layers className="w-4 h-4 text-[#A3B5A0]" />
            <span>Cross-Subject Cohort Performance</span>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[11px] text-[#858D83]">Filter Subject:</span>
            <select
              value={selectedSubjectId}
              onChange={(e) => setSelectedSubjectId(e.target.value)}
              className="px-3 py-1.5 rounded-xl bg-[#1D221E] border border-[#353C36] text-xs text-[#F1F0E9] focus:outline-none focus:border-[#A3B5A0]"
            >
              <option value="all">All Academic Disciplines</option>
              {ALL_SUBJECTS.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Multi-Subject Performance Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredMultiSubject.map((item) => (
            <div
              key={item.subjectId}
              className="p-4 rounded-2xl bg-[#222823] border border-[#353C36] hover:border-[#A3B5A0]/40 transition-colors space-y-3"
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-sm text-[#F1F0E9]">{item.subjectName}</span>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                    item.averageAccuracy >= 75
                      ? 'bg-[#8FBF9B]/15 text-[#8FBF9B] border border-[#8FBF9B]/30'
                      : item.averageAccuracy >= 65
                      ? 'bg-[#D8BC86]/15 text-[#D8BC86] border border-[#D8BC86]/30'
                      : 'bg-[#D98E8E]/15 text-[#D98E8E] border border-[#D98E8E]/30'
                  }`}
                >
                  {item.averageAccuracy}% Class Avg
                </span>
              </div>

              <div className="text-xs space-y-1">
                <div className="text-[#858D83]">Primary Cognitive Hurdle:</div>
                <div className="text-[#F1F0E9] font-medium text-[11px]">{item.topMisconception}</div>
              </div>

              <div className="pt-2 border-t border-[#353C36] flex items-center justify-between text-[11px]">
                <span className="text-[#D8BC86] font-semibold">{item.studentsAtRisk} Students Need Guidance</span>
                <span className="text-[#A3B5A0]">Action Ready</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Cohort Heatmap Component */}
      <TeacherHeatmap insights={insights} />

      {/* AI Prescribed Interventions */}
      <div className="p-6 rounded-2xl bg-[#222823] border border-[#353C36] space-y-4 shadow-md">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-[#F1F0E9] flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-[#A3B5A0]" />
            AI-Prescribed Differentiated Teaching Plans
          </h2>
          <span className="text-xs text-[#858D83]">Based on {insights.classSize} student diagnostic profiles</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {insights.cohortRecommendations.map((rec, i) => (
            <div
              key={i}
              className="p-4 rounded-xl bg-[#1D221E] border border-[#353C36] hover:border-[#A3B5A0]/35 transition-colors space-y-2"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-[#F1F0E9] flex items-center gap-2">
                  <Lightbulb className="w-4 h-4 text-[#A3B5A0]" />
                  Prescription #{i + 1}
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-[#283329] text-[#A3B5A0] border border-[#A3B5A0]/30">
                  Targeted Micro-Lesson
                </span>
              </div>
              <p className="text-xs text-[#B5B9B0] leading-relaxed">
                {rec}
              </p>
              <div className="pt-1 flex items-center justify-between text-[11px]">
                <span className="text-[#858D83]">Estimated Session Time: 15 mins</span>
                <button
                  onClick={() => alert(`Lesson protocol generated for: ${rec}`)}
                  className="text-[#A3B5A0] hover:text-[#B7C7B2] font-medium transition-colors"
                >
                  Generate Activity &rarr;
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
