# Frontend Uses & Architecture Guide: AI That Teaches (Misconception Tutor)

This document provides a comprehensive overview of the uses, capabilities, architecture, and operational workflows of the **Misconception Tutor Frontend UI**.

---

## 1. Executive Summary & Core Mission

Standard mathematics tutoring tools typically identify *that* an answer is wrong, but fail to explain *why* the student produced that specific error.

The **Misconception Tutor UI** is an intelligent, reactive learning interface engineered for **Theme 5 · Problem 8: "A Tutor That Finds the Real Reason You're Stuck"** (IIT Bombay Hackathon). 

Rather than treating errors as random calculation slips, the frontend captures student errors as **computational fingerprints of buggy mental rules**. It displays real-time pedagogical explanations, visualizes step-by-step cognitive replays, generates targeted counter-examples, and tracks long-term mastery using Bayesian Knowledge Tracing (BKT).

---

## 2. Key Uses & Core Capabilities

The frontend is organized into 6 interactive modules accessible via the unified navigation shell:

### A. Targeted Practice Screen (`src/pages/Practice.tsx`)
- **Use**: Active student problem-solving with immediate cognitive feedback.
- **Features**:
  - Exact fraction expression renderer (`src/components/FractionDisplay.tsx`).
  - Bulletproof input parsing: accepts mixed numbers (`1 1/2`), decimals (`0.75`), raw fractions (`3/4`), and spaces.
  - Interactive hint drawer providing progressive conceptual scaffolds.
  - Streak tracker and adaptive motivational banner.
  - Live AI question generator button for on-demand practice on specific operations.

### B. Cognitive Diagnosis & Replay Sandbox (`src/pages/Diagnosis.tsx`)
- **Use**: Deep-dive analysis of a diagnosed error with interactive counter-examples.
- **Features**:
  - **Why We Think This (`src/components/WhyWeThinkThisAccordion.tsx`)**: Replays the student's exact mental arithmetic step-by-step to demystify how their answer was produced.
  - **Interactive Buggy Rule Sandbox**: Allows students to select different buggy rules (e.g. "Add Across") and watch in real-time how the numbers transform.
  - **Counter-Example Renderer**: Displays concrete visual/numerical counter-examples showing why the buggy rule breaks mathematical axioms.
  - **One-Click Targeted Recovery**: Launches a follow-up problem specifically engineered to dismantle the diagnosed misconception.

### C. Learner Progress & Bayesian Knowledge Tracing (`src/pages/Progress.tsx`)
- **Use**: Self-reflection and longitudinal tracking for learners.
- **Features**:
  - Live Bayesian Knowledge Tracing (BKT) mastery curves ($P(L_t)$ probability of skill mastery over consecutive attempts).
  - Misconception frequency distribution radar/bar charts.
  - Historical attempt log with timestamped question prompts, submitted answers, and rule classifications.

### D. Teacher Insights & Cohort Heatmap (`src/pages/TeacherInsights.tsx`)
- **Use**: Diagnostic dashboard for educators and researchers to monitor classroom cohorts.
- **Features**:
  - **Cohort Heatmap (`src/components/TeacherHeatmap.tsx`)**: Visual matrix mapping students against known buggy rules to immediately spot systemic classroom misunderstandings.
  - High-risk student identification with targeted intervention suggestions.
  - Classroom aggregate accuracy and misconception prevalence rates.

### E. AI Multimodal Doubt Solver (`src/pages/DoubtSolver.tsx`)
- **Use**: Natural language question-and-answer assistant powered by Gemini 3.8 Flash.
- **Features**:
  - Multi-turn educational dialogue tailored for conceptual explanations.
  - Explanation modes: *Simpler*, *Step-by-Step*, *Analogy*, and *Deep Dive*.
  - **Web Speech Synthesis (TTS)**: Built-in voice read-aloud functionality for auditory learners.

### F. Multi-Subject Explorer (`src/pages/SubjectsPage.tsx`)
- **Use**: Extends the fraction misconception paradigm across mathematics, programming, physics, and chemistry.

---

## 3. Mapping Frontend to Backend Buggy Rules

The UI directly reflects the mathematical bug classifications implemented in `backend/backend_code.py`:

| Bug ID | Buggy Rule Name | Diagnostic Behavior in UI |
|---|---|---|
| **M1** | Add Across | Recognizes $\frac{a}{b} + \frac{c}{d} = \frac{a+c}{b+d}$. Replays $(1+1)/(4+6) = 2/10 = 1/5$ and offers pizza slice visual counter-example. |
| **M2** | Add Tops, Multiply Bottoms | Identifies $\frac{a}{b} + \frac{c}{d} = \frac{a+c}{b \times d}$. Displays step replay highlighting erroneous operation mixing. |
| **M3** | Common Denominator Found, Tops Not Scaled | Traces common denominator conversion without numerator scaling $\frac{a+c}{\text{lcm}(b, d)}$. Replays unscaled addition. |
| **M4** | Divide Without Flipping | Flags $\frac{a}{b} \div \frac{c}{d} = \frac{a \times c}{b \times d}$. Visualizes Keep-Change-Flip omission. |
| **M5** | Invert First Fraction | Detects dividend inversion $(\frac{b}{a}) \times (\frac{c}{d})$. Illustrates division grouping mechanics. |
| **Unknown** | Uncertain / Calculation Slip | Flags low confidence and prompts an adaptive probe problem to disambiguate. |

---

## 4. Technical Architecture & Directory Layout

```
frontend/
├── index.html                  # Single Page Application HTML shell
├── package.json                # Dependencies, build scripts & metadata
├── package-lock.json           # Locked dependency tree
├── tsconfig.json               # Strict TypeScript configuration
├── vite.config.ts              # Vite 6 bundler config with Tailwind plugin
├── server.ts                   # Express server with Gemini AI API endpoints & SSR proxy
├── metadata.json               # Application descriptor & capability grants
├── USES.md                     # This document: Comprehensive uses and system overview
├── README.md                   # Quickstart developer guide
├── .env.example                # Template for environment variables
└── src/
    ├── main.tsx                # React DOM entry point
    ├── App.tsx                 # Top-level state coordinator, routing & tab switcher
    ├── index.css               # Tailwind CSS imports & global styles
    ├── types/
    │   ├── education.ts        # Question, Misconception, DiagnosisResult, Progress models
    │   └── subjects.ts         # Multi-subject taxonomy definitions
    ├── components/
    │   ├── AppShell.tsx        # Responsive layout shell with collapsible navigation
    │   ├── Topbar.tsx          # Status bar with active learner metrics & streak
    │   ├── Sidebar.tsx         # Primary tab navigation
    │   ├── FractionDisplay.tsx # Typographic fraction renderer
    │   ├── MisconceptionCard.tsx # Diagnostic highlight card with severity badges
    │   ├── WhyWeThinkThisAccordion.tsx # Step-by-step cognitive replay accordion
    │   ├── ConfidenceIndicator.tsx # Diagnostic confidence bar
    │   ├── SolutionRenderer.tsx # Mathematical markdown & step renderer
    │   ├── TargetedPracticeModal.tsx # Follow-up drill launcher
    │   ├── TeacherHeatmap.tsx  # Cohort student-by-misconception matrix
    │   ├── ProgressChart.tsx   # SVG accuracy and trend visualization
    │   ├── ProgressRing.tsx    # Circular completion gauge
    │   ├── AnimatedCounter.tsx # Smooth number roll-up animation
    │   ├── ThreeHeroCanvas.tsx # Three.js interactive 3D hero visual
    │   └── CinematicBackground.tsx # Ambient gradient background
    ├── pages/
    │   ├── Dashboard.tsx       # Student dashboard overview
    │   ├── Practice.tsx        # Active problem solving & diagnostic submit
    │   ├── Diagnosis.tsx       # Cognitive diagnosis sandbox & counter-examples
    │   ├── Progress.tsx        # Bayesian mastery & history view
    │   ├── TeacherInsights.tsx # Educator analytics & cohort overview
    │   ├── DoubtSolver.tsx     # Gemini AI Q&A with voice synthesis
    │   ├── SubjectsPage.tsx    # Subject taxonomy selector
    │   └── Settings.tsx        # Profile & configuration settings
    ├── services/
    │   ├── api.ts              # Diagnostic engine, local persistence & backend bridge
    │   ├── aiService.ts        # Gemini API client for Doubt Solver & question gen
    │   └── mockData.ts         # Pre-computed question bank & misconception catalog
    └── utils/
        └── motion.ts           # Framer motion transition presets
```

---

## 5. Technology Stack

- **Framework**: React 19, TypeScript
- **Build Tool**: Vite 6, `tsx` Node runner
- **Styling**: Tailwind CSS v4, Lucide React icons
- **Animations & 3D**: Motion (`motion/react`), Three.js
- **Audio & Accessibility**: Web Speech API for text-to-speech
- **AI Integration**: `@google/genai` SDK (Gemini 3.8 Flash)

---

## 6. How to Run Locally

### Prerequisites
- Node.js (version 18 or newer)
- npm or bun

### Step 1: Install Dependencies
```bash
cd frontend
npm install
```

### Step 2: Configure Environment
Copy the example environment file:
```bash
cp .env.example .env
```
*(Optional: Provide a `GEMINI_API_KEY` in `.env` if you wish to use the live Gemini Doubt Solver and AI question generator. If omitted, the frontend operates completely offline using its built-in rule engine.)*

### Step 3: Start the Development Server
```bash
npm run dev
```
The application will launch at **`http://localhost:3000`**.

### Step 4: Build for Production
```bash
npm run build
```
Production assets are generated in `frontend/dist/`.
