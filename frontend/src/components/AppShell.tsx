import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Sidebar, NavTab } from './Sidebar';
import { Topbar } from './Topbar';
import { CinematicBackground } from './CinematicBackground';
import {
  LayoutDashboard,
  MessageSquareQuote,
  Layers,
  BookOpen,
  BrainCircuit,
  BarChart3,
  Users,
  Settings as SettingsIcon,
  X,
  Sparkles,
} from 'lucide-react';

interface AppShellProps {
  currentTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  hasActiveDiagnosis: boolean;
  accuracy: number;
  streakDays: number;
  activeSubjectId?: string;
  onSelectSubject?: (id: string) => void;
  children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({
  currentTab,
  onSelectTab,
  hasActiveDiagnosis,
  accuracy,
  streakDays,
  activeSubjectId,
  onSelectSubject,
  children,
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);

  const mobileNavItems = [
    { id: 'dashboard' as NavTab, label: 'Dashboard', icon: LayoutDashboard },
    { id: 'doubts' as NavTab, label: 'Doubt AI', icon: MessageSquareQuote },
    { id: 'subjects' as NavTab, label: 'Subjects', icon: Layers },
    { id: 'practice' as NavTab, label: 'Practice', icon: BookOpen },
    { id: 'diagnosis' as NavTab, label: 'Diagnosis', icon: BrainCircuit, badge: hasActiveDiagnosis },
    { id: 'progress' as NavTab, label: 'Progress', icon: BarChart3 },
    { id: 'teacher' as NavTab, label: 'Teacher', icon: Users },
    { id: 'settings' as NavTab, label: 'Settings', icon: SettingsIcon },
  ];

  return (
    <div className="min-h-screen text-[#F1F0E9] flex flex-col lg:flex-row antialiased relative">
      {/* Cinematic Animated Background */}
      <CinematicBackground />

      {/* Desktop Persistent Sidebar */}
      <Sidebar
        currentTab={currentTab}
        onSelectTab={onSelectTab}
        hasActiveDiagnosis={hasActiveDiagnosis}
      />

      {/* Mobile Drawer Overlay */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <div className="fixed inset-0 z-50 lg:hidden flex">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/75 backdrop-blur-md"
              onClick={() => setMobileMenuOpen(false)}
            />
            <motion.div
              initial={{ x: -280, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: -280, opacity: 0 }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              className="relative w-72 bg-[#171A18]/95 border-r border-[#353C36] h-full p-6 flex flex-col z-10 shadow-2xl backdrop-blur-xl text-left"
            >
              <div className="flex items-center justify-between pb-6 border-b border-[#353C36]">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-[#A3B5A0]" />
                  <span className="font-bold text-base text-[#F1F0E9]">AI That Teaches</span>
                </div>
                <motion.button
                  whileTap={{ scale: 0.9 }}
                  onClick={() => setMobileMenuOpen(false)}
                  className="p-1.5 text-[#B5B9B0] hover:text-[#F1F0E9] rounded-lg hover:bg-white/5"
                >
                  <X className="w-5 h-5" />
                </motion.button>
              </div>

              <nav className="flex-1 py-6 space-y-1.5 overflow-y-auto">
                {mobileNavItems.map((item) => {
                  const Icon = item.icon;
                  const isActive = currentTab === item.id;
                  return (
                    <motion.button
                      key={item.id}
                      whileTap={{ scale: 0.96 }}
                      onClick={() => {
                        onSelectTab(item.id);
                        setMobileMenuOpen(false);
                      }}
                      className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-left text-sm font-medium transition-all ${
                        isActive
                          ? 'bg-[#283329] text-[#F1F0E9] border border-[#A3B5A0]/40'
                          : 'text-[#B5B9B0] hover:text-[#F1F0E9] hover:bg-[#1D221E]'
                      }`}
                    >
                      <Icon className={`w-4 h-4 ${isActive ? 'text-[#A3B5A0]' : 'text-[#858D83]'}`} />
                      <span>{item.label}</span>
                      {item.badge && (
                        <span className="ml-auto text-[10px] px-1.5 py-0.5 bg-[#283329] text-[#A3B5A0] rounded border border-[#A3B5A0]/30 font-semibold">
                          Active
                        </span>
                      )}
                    </motion.button>
                  );
                })}
              </nav>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 relative z-10">
        <Topbar
          currentTab={currentTab}
          activeSubjectId={activeSubjectId}
          onSelectSubject={onSelectSubject}
          onOpenPractice={() => onSelectTab('practice')}
          onToggleMobileMenu={() => setMobileMenuOpen(true)}
          accuracy={accuracy}
          streakDays={streakDays}
        />

        <main className="flex-1 p-4 md:p-8 max-w-7xl mx-auto w-full">
          {children}
        </main>

        {/* Mobile Bottom Navigation Bar */}
        <div className="lg:hidden sticky bottom-0 z-40 bg-[#171A18]/90 backdrop-blur-xl border-t border-[#353C36] px-2 py-2 flex items-center justify-around">
          {mobileNavItems.slice(0, 5).map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <motion.button
                key={item.id}
                whileTap={{ scale: 0.9 }}
                onClick={() => onSelectTab(item.id)}
                className={`flex flex-col items-center py-1 px-2 rounded-lg text-[10px] font-medium transition-colors ${
                  isActive ? 'text-[#A3B5A0]' : 'text-[#858D83] hover:text-[#F1F0E9]'
                }`}
              >
                <Icon className="w-5 h-5 mb-0.5" />
                <span>{item.label}</span>
              </motion.button>
            );
          })}
        </div>
      </div>
    </div>
  );
};
