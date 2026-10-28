import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { TeacherInsights } from '../types/education';
import { Filter, Users, ShieldCheck, Info } from 'lucide-react';

interface TeacherHeatmapProps {
  insights: TeacherInsights;
}

export const TeacherHeatmap: React.FC<TeacherHeatmapProps> = ({ insights }) => {
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [hoveredCell, setHoveredCell] = useState<{ learner: string; topic: string; rate: number } | null>(null);

  const categories = ['All', 'Addition', 'Subtraction', 'Multiplication', 'Division'];

  const filteredColumns =
    selectedCategory === 'All'
      ? insights.misconceptionColumns
      : insights.misconceptionColumns.filter((col) => col.category === selectedCategory);

  // Helper for heatmap cell color in Sage/Amber/Coral palette
  const getCellBg = (rate: number) => {
    if (rate === 0) return 'bg-[#8FBF9B]/15 text-[#8FBF9B] border-[#8FBF9B]/30';
    if (rate <= 20) return 'bg-[#8FBF9B]/25 text-[#8FBF9B] border-[#8FBF9B]/40';
    if (rate <= 40) return 'bg-[#D8BC86]/20 text-[#D8BC86] border-[#D8BC86]/30';
    if (rate <= 60) return 'bg-[#D8BC86]/35 text-[#D8BC86] border-[#D8BC86]/50';
    return 'bg-[#D98E8E]/25 text-[#D98E8E] border-[#D98E8E]/40';
  };

  return (
    <div className="bg-[#222823] rounded-3xl border border-[#353C36] p-5 md:p-7 shadow-xl space-y-6 backdrop-blur-xl text-left">
      {/* Header and Filter */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Users className="w-5 h-5 text-[#A3B5A0]" />
            <h3 className="text-base font-bold text-[#F1F0E9] tracking-tight">
              Class Cohort Cognitive Divergence Heatmap
            </h3>
          </div>
          <p className="text-xs text-[#858D83] flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-[#8FBF9B]" />
            <span>Anonymous Learner IDs · Privacy Preserved</span>
          </p>
        </div>

        {/* Filter controls */}
        <div className="flex items-center gap-1 bg-[#1D221E] p-1.5 rounded-2xl border border-[#353C36] overflow-x-auto relative">
          <div className="px-2 text-xs text-[#858D83] flex items-center gap-1">
            <Filter className="w-3 h-3" />
            <span className="hidden md:inline">Topic:</span>
          </div>
          {categories.map((cat) => {
            const isSelected = selectedCategory === cat;
            return (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`relative px-3.5 py-1 text-xs font-semibold rounded-xl transition-colors whitespace-nowrap z-10 ${
                  isSelected ? 'text-[#171A18]' : 'text-[#858D83] hover:text-[#F1F0E9]'
                }`}
              >
                {isSelected && (
                  <motion.div
                    layoutId="heatmapFilterTab"
                    className="absolute inset-0 bg-[#A3B5A0] rounded-xl shadow-sm z-[-1]"
                    transition={{ type: 'spring', stiffness: 350, damping: 25 }}
                  />
                )}
                <span>{cat}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Heatmap Grid Matrix */}
      <div className="overflow-x-auto rounded-2xl border border-[#353C36] bg-[#171A18]/60">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="border-b border-[#353C36] bg-[#1D221E]">
              <th className="p-3.5 font-bold text-[#F1F0E9] min-w-[130px]">Learner ID</th>
              <th className="p-3.5 font-bold text-[#858D83] min-w-[90px]">Accuracy</th>
              {filteredColumns.map((col) => (
                <th key={col.code} className="p-3.5 font-bold text-[#A3B5A0] min-w-[140px]">
                  <div className="flex flex-col">
                    <span className="truncate">{col.title}</span>
                    <span className="text-[10px] text-[#858D83] font-mono font-normal">
                      {col.code}
                    </span>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {insights.learners.map((learner) => (
              <tr
                key={learner.anonymousId}
                className="border-b border-[#353C36]/40 hover:bg-[#222823] transition-colors"
              >
                <td className="p-3.5 font-mono text-xs font-semibold text-[#F1F0E9] flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-[#A3B5A0]/60" />
                  <span>{learner.anonymousId}</span>
                </td>
                <td className="p-3.5 font-mono text-xs text-[#B5B9B0]">
                  <span
                    className={`font-bold ${
                      learner.accuracy >= 75
                        ? 'text-[#8FBF9B]'
                        : learner.accuracy >= 55
                        ? 'text-[#D8BC86]'
                        : 'text-[#D98E8E]'
                    }`}
                  >
                    {learner.accuracy}%
                  </span>
                </td>
                {filteredColumns.map((col) => {
                  const errorRate = learner.activeMisconceptions[col.code] ?? 0;
                  return (
                    <td key={col.code} className="p-2.5">
                      <div
                        onMouseEnter={() =>
                          setHoveredCell({
                            learner: learner.anonymousId,
                            topic: col.title,
                            rate: errorRate,
                          })
                        }
                        onMouseLeave={() => setHoveredCell(null)}
                        className={`h-8 rounded-lg flex items-center justify-center font-mono text-[11px] font-bold border transition-all duration-150 cursor-pointer hover:scale-105 ${getCellBg(
                          errorRate
                        )}`}
                      >
                        {errorRate > 0 ? `${errorRate}%` : '0%'}
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Legend & Tooltip Strip */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between text-xs text-[#858D83] gap-3 pt-1">
        <div className="flex items-center gap-4 flex-wrap">
          <span className="font-semibold text-[#F1F0E9]">Divergence Legend:</span>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-[#8FBF9B]/30 border border-[#8FBF9B]" />
            <span>0–20% (Mastered)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-[#D8BC86]/30 border border-[#D8BC86]" />
            <span>21–60% (Emerging)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-[#D98E8E]/30 border border-[#D98E8E]" />
            <span>61–100% (High Priority)</span>
          </div>
        </div>

        {hoveredCell && (
          <div className="p-2 rounded-xl bg-[#1D221E] border border-[#353C36] text-[11px] text-[#F1F0E9] flex items-center gap-2">
            <Info className="w-3.5 h-3.5 text-[#A3B5A0]" />
            <span>
              {hoveredCell.learner} • {hoveredCell.topic}: <strong>{hoveredCell.rate}% Error Frequency</strong>
            </span>
          </div>
        )}
      </div>
    </div>
  );
};
