# Misconception Tutor Frontend UI

Modern, interactive React + TypeScript interface for **Misconception Tutor** (Theme 5: AI That Teaches).

## Overview
- **Practice & Instant Diagnosis**: Solves fraction problems with automatic detection of M1–M5 buggy mental rules.
- **Cognitive Replay**: Replays exact student arithmetic errors step-by-step ("Why We Think This").
- **Interactive Sandbox**: Experiment with buggy rules and explore visual counter-examples.
- **Bayesian Knowledge Tracing**: Real-time mastery probabilities $P(L_t)$ per learner.
- **Teacher Heatmap**: Cohort-wide analytics matrix highlighting common classroom stumbling blocks.
- **Multimodal Doubt Solver**: AI explanations with integrated Text-To-Speech read-aloud.

For a detailed breakdown of all features, pedagogical mechanics, and architecture, see [USES.md](USES.md).

## Quick Start
```bash
# Navigate to this directory
cd frontend

# Install dependencies
npm install

# (Optional) Copy environment config
cp .env.example .env

# Start dev server
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.
