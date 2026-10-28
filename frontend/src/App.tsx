import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { AppShell } from './components/AppShell';
import { NavTab } from './components/Sidebar';
import { Dashboard } from './pages/Dashboard';
import { DoubtSolver } from './pages/DoubtSolver';
import { SubjectsPage } from './pages/SubjectsPage';
import { Practice } from './pages/Practice';
import { Diagnosis } from './pages/Diagnosis';
import { Progress } from './pages/Progress';
import { TeacherInsights } from './pages/TeacherInsights';
import { Settings } from './pages/Settings';
import { DiagnosisResult, LearnerProgress } from './types/education';
import { api } from './services/api';
import { INITIAL_LEARNER_PROGRESS } from './services/mockData';

export default function App() {
  const [currentTab, setCurrentTab] = useState<NavTab>('dashboard');
  const [activeDiagnosis, setActiveDiagnosis] = useState<DiagnosisResult | null>(null);
  const [progress, setProgress] = useState<LearnerProgress>(INITIAL_LEARNER_PROGRESS);
  const [targetPracticeTopic, setTargetPracticeTopic] = useState<string | undefined>(undefined);
  const [doubtSubjectContext, setDoubtSubjectContext] = useState<string | undefined>(undefined);
  const [doubtQuestionPrompt, setDoubtQuestionPrompt] = useState<string | undefined>(undefined);
  const [activeSubjectId, setActiveSubjectId] = useState<string>(() => {
    try {
      return localStorage.getItem('ai_that_teaches_active_subject') || 'mathematics';
    } catch {
      return 'mathematics';
    }
  });

  const handleSelectSubject = (id: string) => {
    setActiveSubjectId(id);
    try {
      localStorage.setItem('ai_that_teaches_active_subject', id);
    } catch {}
  };

  // Load progress on initial render
  const refreshProgress = async () => {
    try {
      const data = await api.fetchLearnerProgress();
      setProgress(data);
    } catch (err) {
      console.warn('Failed to refresh progress', err);
    }
  };

  useEffect(() => {
    refreshProgress();
  }, []);

  // When student submits an answer in Practice
  const handleCompleteAnswer = (diagnosis: DiagnosisResult) => {
    setActiveDiagnosis(diagnosis);
    refreshProgress();
  };

  // Launch practice with optional topic
  const handleStartPractice = (topicOrSubject?: string) => {
    const subjectToUse = topicOrSubject || activeSubjectId;
    setTargetPracticeTopic(subjectToUse);
    if (topicOrSubject) {
      handleSelectSubject(topicOrSubject);
    }
    setCurrentTab('practice');
  };

  // Launch doubt solver with optional subject or prompt
  const handleOpenDoubtSolver = (subjectId?: string, questionText?: string) => {
    const subj = subjectId || activeSubjectId;
    setDoubtSubjectContext(subj);
    if (subjectId) {
      handleSelectSubject(subjectId);
    }
    setDoubtQuestionPrompt(questionText);
    setCurrentTab('doubts');
  };

  return (
    <AppShell
      currentTab={currentTab}
      onSelectTab={(tab) => setCurrentTab(tab)}
      hasActiveDiagnosis={Boolean(activeDiagnosis)}
      accuracy={progress.accuracy}
      streakDays={progress.activeStreakDays}
      activeSubjectId={activeSubjectId}
      onSelectSubject={handleSelectSubject}
    >
      <AnimatePresence mode="wait">
        <motion.div
          key={currentTab}
          initial={{ opacity: 0, y: 10, filter: 'blur(4px)' }}
          animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
          exit={{ opacity: 0, y: -6, filter: 'blur(4px)' }}
          transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
          className="w-full"
        >
          {currentTab === 'dashboard' && (
            <Dashboard
              progress={progress}
              onStartPractice={handleStartPractice}
              onNavigateToProgress={() => setCurrentTab('progress')}
              onNavigateToDiagnosis={() => setCurrentTab('diagnosis')}
              onNavigateToDoubtSolver={handleOpenDoubtSolver}
              onNavigateToSubjects={() => setCurrentTab('subjects')}
              hasActiveDiagnosis={Boolean(activeDiagnosis)}
            />
          )}

          {currentTab === 'doubts' && (
            <DoubtSolver
              initialSubjectId={doubtSubjectContext}
              initialQuestion={doubtQuestionPrompt}
            />
          )}

          {currentTab === 'subjects' && (
            <SubjectsPage
              onSelectTopicForPractice={(subjectId, topicId) => {
                setTargetPracticeTopic(subjectId);
                setCurrentTab('practice');
              }}
              onAskDoubtAboutTopic={(subjectId, topicTitle) => {
                handleOpenDoubtSolver(
                  subjectId,
                  `Can you explain the key concepts and formulas in ${topicTitle}?`
                );
              }}
            />
          )}

          {currentTab === 'practice' && (
            <Practice
              onCompleteAnswer={handleCompleteAnswer}
              targetTopic={targetPracticeTopic}
              onNavigateToDiagnosis={() => setCurrentTab('diagnosis')}
              onAskDoubtAboutQuestion={(subj, qText) => handleOpenDoubtSolver(subj, qText)}
            />
          )}

          {currentTab === 'diagnosis' && (
            <Diagnosis
              diagnosis={activeDiagnosis}
              onContinuePractice={() => setCurrentTab('practice')}
              onReturnToDashboard={() => setCurrentTab('dashboard')}
            />
          )}

          {currentTab === 'progress' && (
            <Progress
              initialProgress={progress}
              onPracticeTopic={handleStartPractice}
              onNavigateToDoubtSolver={handleOpenDoubtSolver}
            />
          )}

          {currentTab === 'teacher' && <TeacherInsights />}

          {currentTab === 'settings' && (
            <Settings onProgressReset={refreshProgress} />
          )}
        </motion.div>
      </AnimatePresence>
    </AppShell>
  );
}
