import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { ChevronDown, Search, Eye, Compass, HelpCircle } from 'lucide-react';

interface EvidenceData {
  observedPattern: string;
  studentMentalStep: string;
  underlyingGap: string;
  counterExample: string;
}

interface WhyWeThinkThisAccordionProps {
  evidence: EvidenceData | null;
  defaultOpen?: boolean;
}

export const WhyWeThinkThisAccordion: React.FC<WhyWeThinkThisAccordionProps> = ({
  evidence,
  defaultOpen = true,
}) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  if (!evidence) {
    return (
      <div className="bg-[#1D221E] rounded-2xl p-5 border border-[#353C36] text-left text-xs text-[#B5B9B0] backdrop-blur-md">
        <div className="flex items-center gap-2 text-[#B5B9B0]">
          <HelpCircle className="w-4 h-4 text-[#D8BC86]" />
          <span className="font-medium text-[#F1F0E9]">Diagnostic Trace Availability</span>
        </div>
        <p className="mt-1 text-[#858D83]">
          Algorithmic breakdown unavailable for this response. Additional problem solving evidence is required.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-[#1D221E] rounded-3xl border border-[#353C36] overflow-hidden transition-all duration-300 shadow-xl backdrop-blur-xl">
      <motion.button
        whileHover={{ backgroundColor: 'rgba(255, 255, 255, 0.02)' }}
        whileTap={{ scale: 0.995 }}
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-6 md:px-8 py-5 flex items-center justify-between text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-[#A3B5A0]"
        aria-expanded={isOpen}
      >
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-[#283329] border border-[#A3B5A0]/30 flex items-center justify-center text-[#A3B5A0] shadow-sm">
            <Search className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-sm md:text-base font-bold text-[#F1F0E9]">
              Why We Think This — Cognitive Diagnostic Evidence
            </h4>
            <p className="text-xs text-[#858D83]">
              Inspecting the computational steps and conceptual signals
            </p>
          </div>
        </div>
        <motion.div
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ type: 'spring', stiffness: 300, damping: 20 }}
          className="text-[#858D83] p-1 rounded-lg"
        >
          <ChevronDown className="w-5 h-5" />
        </motion.div>
      </motion.button>

      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
            className="overflow-hidden"
          >
            <div className="px-6 md:px-8 pb-8 pt-2 border-t border-[#353C36] space-y-4 text-left">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* 1. Observed pattern */}
                <div className="p-4 rounded-2xl bg-[#171A18] border border-[#353C36] shadow-inner">
                  <div className="flex items-center gap-2 text-xs font-bold text-[#8FBF9B] mb-2">
                    <Eye className="w-4 h-4" />
                    <span>Observed Pattern</span>
                  </div>
                  <p className="text-xs text-[#F1F0E9] leading-relaxed font-mono">
                    {evidence.observedPattern}
                  </p>
                </div>

                {/* 2. Hypothesized mental model */}
                <div className="p-4 rounded-2xl bg-[#171A18] border border-[#353C36] shadow-inner">
                  <div className="flex items-center gap-2 text-xs font-bold text-[#A3B5A0] mb-2">
                    <Compass className="w-4 h-4" />
                    <span>Probable Mental Model</span>
                  </div>
                  <p className="text-xs text-[#F1F0E9] leading-relaxed">
                    {evidence.studentMentalStep}
                  </p>
                </div>
              </div>

              {/* 3. Underlying Gap & Counter-example */}
              <div className="p-5 rounded-2xl bg-[#171A18] border border-[#353C36] space-y-3">
                <div>
                  <span className="text-xs font-bold text-[#858D83] uppercase tracking-wider block mb-1">
                    Conceptual Gap Analysis
                  </span>
                  <p className="text-xs text-[#B5B9B0] leading-relaxed">
                    {evidence.underlyingGap}
                  </p>
                </div>
                <div className="pt-3 border-t border-[#353C36]">
                  <span className="text-xs font-bold text-[#8FBF9B] block mb-1 flex items-center gap-1.5">
                    <span>Intuitive Counter-Example:</span>
                  </span>
                  <p className="text-xs text-[#F1F0E9] italic leading-relaxed bg-[#283329]/50 p-3 rounded-xl border border-[#8FBF9B]/20">
                    "{evidence.counterExample}"
                  </p>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
