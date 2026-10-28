import React from 'react';
import { motion } from 'motion/react';
import {
  LayoutDashboard,
  MessageSquareQuote,
  Layers,
  BookOpen,
  BrainCircuit,
  BarChart3,
  Users,
  Settings,
  Sparkles,
  Flame,
} from 'lucide-react';

export type NavTab =
  | 'dashboard'
  | 'doubts'
  | 'subjects'
  | 'practice'
  | 'diagnosis'
  | 'progress'
  | 'teacher'
  | 'settings';

interface SidebarProps {
  currentTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  hasActiveDiagnosis: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onSelectTab,
  hasActiveDiagnosis,
}) => {
  const navItems = [
    {
      id: 'dashboard' as NavTab,
      label: 'Dashboard',
      icon: LayoutDashboard,
      description: 'Overview & Activity Hub',
    },
    {
      id: 'doubts' as NavTab,
      label: 'Ask Doubt AI',
      icon: MessageSquareQuote,
      description: 'Universal Doubt Solver',
      badge: 'Gemini AI',
    },
    {
      id: 'subjects' as NavTab,
      label: 'Subject Library',
      icon: Layers,
      description: '11 Academic Disciplines',
    },
    {
      id: 'practice' as NavTab,
      label: 'Practice',
      icon: BookOpen,
      description: 'Multi-Subject Problem Sets',
    },
    {
      id: 'diagnosis' as NavTab,
      label: 'Cognitive Diagnosis',
      icon: BrainCircuit,
      description: 'Misconception Analysis',
      badge: hasActiveDiagnosis ? 'Active' : undefined,
    },
    {
      id: 'progress' as NavTab,
      label: 'My Progress',
      icon: BarChart3,
      description: 'Mistake Log & Analytics',
    },
    {
      id: 'teacher' as NavTab,
      label: 'Class Insights',
      icon: Users,
      description: 'Cohort Cognitive Heatmap',
    },
    {
      id: 'settings' as NavTab,
      label: 'Settings',
      icon: Settings,
      description: 'Preferences & Reset',
    },
  ];

  return (
    <aside className="w-64 bg-[#171A18]/95 backdrop-blur-xl border-r border-[#353C36] flex flex-col shrink-0 h-screen sticky top-0 hidden lg:flex select-none z-20">
      {/* Brand Header */}
      <div className="p-6 border-b border-[#353C36] flex items-center gap-3 text-left">
        <motion.div
          whileHover={{ rotate: 180, scale: 1.05 }}
          transition={{ type: 'spring', stiffness: 200, damping: 15 }}
          className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#A3B5A0] to-[#8FBF9B] p-[1px] shadow-lg shadow-[#A3B5A0]/20 flex items-center justify-center cursor-pointer"
        >
          <div className="w-full h-full bg-[#171A18] rounded-[11px] flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-[#A3B5A0]" />
          </div>
        </motion.div>
        <div>
          <h1 className="font-bold text-base text-[#F1F0E9] tracking-tight flex items-center gap-1.5">
            <span>AI That Teaches</span>
          </h1>
          <p className="text-[11px] text-[#858D83]">All-Subject Learning 2030</p>
        </div>
      </div>

      {/* Navigation items */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto relative text-left">
        <div className="px-3 py-2 text-[10px] font-semibold text-[#858D83] uppercase tracking-wider">
          Learning Navigation
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;
          return (
            <motion.button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              whileTap={{ scale: 0.98 }}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left relative transition-colors group ${
                isActive ? 'text-[#F1F0E9]' : 'text-[#B5B9B0] hover:text-[#F1F0E9]'
              }`}
            >
              {isActive && (
                <motion.div
                  layoutId="sidebarActiveIndicator"
                  className="absolute inset-0 bg-[#283329] border border-[#A3B5A0]/40 rounded-xl shadow-md z-0"
                  transition={{ type: 'spring', stiffness: 350, damping: 30 }}
                />
              )}

              <motion.div
                whileHover={{ scale: 1.15, rotate: 6 }}
                transition={{ type: 'spring', stiffness: 400, damping: 20 }}
                className="relative z-10"
              >
                <Icon
                  className={`w-4 h-4 shrink-0 transition-colors ${
                    isActive ? 'text-[#A3B5A0]' : 'text-[#858D83] group-hover:text-[#F1F0E9]'
                  }`}
                />
              </motion.div>

              <div className="flex-1 min-w-0 relative z-10">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold truncate">{item.label}</span>
                  {item.badge && (
                    <motion.span
                      animate={{ scale: [1, 1.05, 1] }}
                      transition={{ duration: 2, repeat: Infinity }}
                      className="text-[9px] px-1.5 py-0.5 font-bold bg-[#1D221E] text-[#A3B5A0] rounded-md border border-[#A3B5A0]/30"
                    >
                      {item.badge}
                    </motion.span>
                  )}
                </div>
                <p className="text-[10px] text-[#858D83] truncate">{item.description}</p>
              </div>
            </motion.button>
          );
        })}
      </nav>

      {/* Bottom Session Box */}
      <div className="p-3.5 bg-[#1D221E] m-3 rounded-xl border border-[#353C36] relative overflow-hidden text-left">
        <div className="flex items-center justify-between text-xs mb-1">
          <span className="text-[#B5B9B0] flex items-center gap-1.5">
            <Flame className="w-3.5 h-3.5 text-[#D8BC86] animate-pulse" />
            <span>Learning Engine:</span>
          </span>
          <span className="text-[#8FBF9B] font-semibold font-mono text-[11px]">Ready</span>
        </div>
        <p className="text-[10px] text-[#858D83] leading-relaxed">
          Universal multi-subject AI reasoning with cognitive misconception tracking.
        </p>
      </div>
    </aside>
  );
};
