import React from 'react';
import { motion } from 'motion/react';
import { Misconception } from '../types/education';
import { ConfidenceIndicator } from './ConfidenceIndicator';
import { Sparkles, Brain, Lightbulb, AlertCircle } from 'lucide-react';

interface MisconceptionCardProps {
  misconception: Misconception | null;
  confidence: number;
  isLowConfidence: boolean;
  explanation: string;
}

export const MisconceptionCard: React.FC<MisconceptionCardProps> = ({
  misconception,
  confidence,
  isLowConfidence,
  explanation,
}) => {
  if (isLowConfidence || !misconception) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4 }}
        className="bg-[#222823] border border-[#D8BC86]/40 rounded-3xl p-6 md:p-8 text-left shadow-xl backdrop-blur-xl relative overflow-hidden"
      >
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-2xl bg-[#D8BC86]/15 border border-[#D8BC86]/30 flex items-center justify-center shrink-0 text-[#D8BC86]">
            <AlertCircle className="w-6 h-6 animate-pulse" />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="text-base md:text-lg font-bold text-[#F1F0E9]">
                Uncertain Diagnosis — Additional Probe Suggested
              </h3>
            </div>
            <p className="text-xs sm:text-sm text-[#B5B9B0] leading-relaxed mb-4">
              The response does not cleanly match a known algorithmic misconception pattern.
              This may be a calculation slip or an atypical multi-step approach.
            </p>
            <ConfidenceIndicator
              confidence={confidence}
              isLowConfidence={true}
              className="mt-2"
            />
          </div>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className="bg-[#222823] border border-[#353C36] hover:border-[#A3B5A0]/40 transition-colors rounded-3xl p-6 md:p-8 text-left shadow-xl relative overflow-hidden backdrop-blur-xl"
    >
      <div className="absolute top-0 right-0 w-80 h-80 bg-gradient-to-br from-[#A3B5A0]/5 to-transparent rounded-full blur-3xl pointer-events-none animate-pulse-subtle" />

      <div className="flex items-start gap-5 relative z-10">
        <motion.div
          animate={{ y: [0, -3, 0] }}
          transition={{ duration: 3.5, repeat: Infinity, ease: 'easeInOut' }}
          className="w-14 h-14 rounded-2xl bg-[#283329] border border-[#A3B5A0]/40 flex items-center justify-center shrink-0 text-[#A3B5A0] shadow-md shadow-[#A3B5A0]/15"
        >
          <Brain className="w-7 h-7" />
        </motion.div>

        <div className="flex-1 space-y-4">
          <div>
            <div className="flex items-center justify-between flex-wrap gap-2 mb-1.5">
              <span className="text-xs font-bold text-[#A3B5A0] uppercase tracking-wider flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5" />
                Detected Cognitive Pattern
              </span>
              <span className="text-xs text-[#858D83] font-mono bg-[#1D221E] px-2.5 py-0.5 rounded-md border border-[#353C36]">
                Taxonomy Code: {misconception.code}
              </span>
            </div>
            <h3 className="text-xl md:text-2xl font-extrabold text-[#F1F0E9] tracking-tight">
              {misconception.title}
            </h3>
            <p className="text-xs sm:text-sm text-[#B5B9B0] mt-1 leading-relaxed">
              {misconception.friendlyDescription}
            </p>
          </div>

          {/* Supportive Explanation Callout */}
          <div className="bg-[#1D221E] rounded-2xl p-5 border border-[#353C36] space-y-2 shadow-inner">
            <div className="flex items-center gap-2 text-xs font-semibold text-[#8FBF9B]">
              <Lightbulb className="w-4 h-4 shrink-0" />
              <span>Let's look at this step together:</span>
            </div>
            <p className="text-xs sm:text-sm text-[#F1F0E9] leading-relaxed pl-6 font-medium">
              {explanation}
            </p>
            <p className="text-xs text-[#858D83] pl-6 pt-1">
              <span className="text-[#A3B5A0] font-semibold">Underlying Concept: </span>
              {misconception.explanation}
            </p>
          </div>

          {/* Recovery Strategy Badge */}
          <div className="bg-[#283329] rounded-2xl p-4 border border-[#A3B5A0]/30 text-xs text-[#F1F0E9] flex items-start gap-3">
            <span className="text-[#A3B5A0] font-bold shrink-0 uppercase tracking-wide">
              Action Plan:
            </span>
            <span className="text-[#B5B9B0] leading-relaxed">{misconception.remedyStrategy}</span>
          </div>

          {/* Confidence Indicator */}
          <div className="pt-2 border-t border-[#353C36]">
            <ConfidenceIndicator
              confidence={confidence}
              isLowConfidence={isLowConfidence}
            />
          </div>
        </div>
      </div>
    </motion.div>
  );
};
