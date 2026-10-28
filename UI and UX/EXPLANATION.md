# UI & UX Architecture & Code Explanation

This folder contains the complete, self-contained UI/UX design prototype exported directly from **Google Stitch** (`stitch.withgoogle.com`) for the **Misconception Tutor** project (*Theme 5: AI That Teaches*).

---

## 1. Overview & Contents

This folder provides all design specifications, source code, and visual assets created for the Tutor Minimalist Learning Engine:

| File | Purpose |
|---|---|
| [`code.html`](code.html) | Complete, zero-dependency, responsive HTML5 + Tailwind CSS interface. |
| [`app.js`](app.js) | Browser bridge that submits tutor prompts to the local LLM backend. |
| [`DESIGN.md`](DESIGN.md) | Full Design System token specifications (Color palette, Typography, Elevation, Spacing). |
| [`screen.png`](screen.png) | High-resolution visual snapshot of the rendered interface. |
| [`EXPLANATION.md`](EXPLANATION.md) | This document: in-depth architectural and code breakdown for readers and developers. |

---

## 2. Core Philosophy & Design Intent

Traditional math tutoring platforms typically tell a student *if* their answer is wrong, but fail to diagnose *why* they arrived at that specific answer. 

This UI/UX design is built around the **Bloom 2-Sigma Socratic Diagnostic method**:
1. **Never solve homework outright**: The interface focuses on identifying the exact step where mental logic diverged.
2. **Visual Step Traceback**: Highlights arithmetic slips, unscaled numerators, sign flips, or boundary conditions.
3. **Isomorphic Follow-up Drills**: Generates practice problems that specifically target the diagnosed misconception.

---

## 3. Deep Dive into `code.html`

The entire application interface is contained in `code.html`. It runs directly in any modern browser without requiring a node build step or external bundler.

### A. Head & Configuration Layer (Lines 1–3)
- **External Typography**:
  - `Geist` (Modern, high-legibility geometric sans-serif for UI elements, headings, and body text).
  - `JetBrains Mono` (Monospaced font for code snippets, formulas, and technical labels).
  - `Google Material Symbols Outlined` (Universal icon system for clean iconography).
- **Tailwind CSS Engine**:
  - Loaded via CDN (`https://cdn.tailwindcss.com`).
  - Embedded `tailwind.config` script injects custom design system tokens:
    - **Surface & Backgrounds**: `#f8f9fa` (light surface), `#ffffff` (container lowest), `#edeeef` (container default).
    - **Primary Accent**: Pure Black (`#000000`) for high-contrast focus.
    - **Secondary Accent**: `#4b41e1` (electric violet) for badges, pulses, and interactive states.
    - **Typography Scales**: Defined sizes from `label-sm` (0.6875rem) to `display` (2.25rem).

### B. Navigation Shell & Sidebar (`<aside>`, Lines 3–4)
- **Fixed Width**: `w-[260px]` fixed to the left edge with a subtle drop shadow (`shadow-[0_1px_8px_rgba(0,0,0,0.04)]`).
- **Logo & Collapse Trigger**:
  - Product logo branding at the top.
  - Collapse icon (`dock_to_right`) to maximize canvas space when needed.
- **Action Bar**:
  - **"New Chat"** primary button with a keyboard shortcut badge (`⌘K`).
- **Subject Filter Pills**:
  - Fast-filtering buttons: **All**, **∑ Maths**, and **⟨/⟩ Python**.
- **Historical Session Navigation**:
  - Categorized under `Today`, `Previous 7 Days`, and `Workspaces`.
  - Links to prior debugging sessions (e.g., *Quadratic equation factoring error*, *Recursion stack overflow debug*).
- **User Profile Footer**:
  - Student badge (**Alex Rivera**, Free Student) with account status and a settings shortcut gear.

### C. Top Bar Header (`<header>`, Line 4)
- Fixed at top (`h-14`, `left-[260px]`, `backdrop-blur-xl`).
- Status indicators:
  - Green pulsing badge: **"AI Adaptive Mode"**.
  - Model tag: **"Active Model: Tutor-v2 (Math & Code)"**.
  - Utility buttons for conversation sharing, thread export, and avatar profile.

### D. Main Diagnostic Workspace (`<main>`, Lines 4–200)
- **Background Ambient Glow**:
  - Radial gradient blur (`w-[720px] h-[340px] bg-secondary-fixed/30 blur-3xl`) positioned behind the hero header for depth.
- **Hero Diagnostic Section**:
  - Status pill: *"Socratic Diagnostic Active"* with live pulse indicator.
  - Headline: *"Where are you stuck today?"*.
  - Subtitle explaining the problem submission workflow.

- **Bento 2-Column Subject Selection Cards**:
  - **Mathematics Card (`#tab-math`)**:
    - Symbol: `∑`
    - Subtitle: *Algebra, Calculus, Linear Algebra & Geometry derivations.*
    - Badge: *Targeted Diagnostic · Find sign & step slips.*
  - **Python Algorithms Card (`#tab-python`)**:
    - Symbol: `⟨/⟩`
    - Subtitle: *Algorithms, Data Structures, Complexity & Runtime Debugging.*
    - Badge: *Traceback Parsing · Pinpoint loop & index errors.*
  - Selecting either card triggers dynamic active rings and changes placeholder contexts.

- **Common Debugging Starters (4-Card Grid)**:
  - Pre-built real-world problem scenarios that can be clicked to instantly stage into the composer:
    1. **Factorization verification**: Quadratic sign check ($2x^2 + 5x - 12 = 0$).
    2. **Fibonacci recursion depth**: Identifying redundant tree branches and transitions to DP memoization.
    3. **Integration by parts sign flip**: Tracing minus-sign distribution in $\int x e^{-2x} dx$.
    4. **Nested loop IndexError**: Diagnosing boundary conditions in grid traversal.

- **Feature Highlights Strip**:
  - Three value-proposition callouts:
    - **Step Diagnostics**: Flags where the mistake occurred, not just the correct answer.
    - **Visual Traceback**: Interactive tree diagrams for logic flows.
    - **Isomorphic Practice**: Instant drills matching the student's exact blind spot.

### E. Floating Input Composer (`fixed bottom-0`, Line 263)
- Anchored to the bottom viewport with safe-area spacing and high backdrop blur.
- Features:
  - Auto-resizing multiline `<textarea>`.
  - Context attachment button (`attach_file`).
  - Formula insertion trigger (`functions`).
  - Code block snippet trigger (`code`).
  - Live character counter (`0 / 4000`).
  - High-contrast Send button (`arrow_upward`).

---

## 4. Client-Side JavaScript Logic

The original prototype behavior remains inline in `code.html`; the application
bridge is in [`app.js`](app.js):

```javascript
// 1. Switches active subject between Mathematics and Python
function setSubject(subject) { ... }

// 2. Pre-fills composer textarea with sample questions & focuses input
function stagePrompt(text) { ... }

// 3. Dismisses the notification banner
function clearStagedPrompt() { ... }
```

The bridge tracks the selected subject, submits the composer text to
`POST /api/llm/answer`, displays the generated response, and shows explicit
backend errors when the local adapter is unavailable. It never calls Gemini or
uses a client-side answer fallback.

The existing inline helpers continue to provide:

1. **`setSubject(subject)`**:
   - Manages active border ring classes (`ring-2 ring-primary`).
   - Toggles visibility of the `"Active Path"` confirmation badges.
   - Dynamically updates the placeholder text in the composer textarea based on whether the student is solving math or code.

2. **`stagePrompt(text)`**:
   - Inserts selected starter problem text into the composer.
   - Dynamically recalculates `textarea.scrollHeight` to expand the input height cleanly.
   - Reveals the staging notification banner (`#staging-banner`).
   - Automatically sets cursor focus to the textarea.

3. **`clearStagedPrompt()`**:
   - Hides the staging banner upon user dismissal.

---

## 5. How to Run & View the UI

For the complete application, run it from the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m backend.api
```

Then open `http://localhost:8000`. Flask serves `code.html`, `app.js`, and the
API from one origin, while the first answer request lazily loads the PEFT
adapter in `LLM/`.

The HTML can still be viewed directly:

### Direct File Open

Double-click `code.html` or open it via terminal:
```bash
# macOS
open "UI and UX/code.html"

# Linux
xdg-open "UI and UX/code.html"

# Windows
start "UI and UX/code.html"
```

### Static Server (prototype only)
```bash
# Using Python
python3 -m http.server 8000

# Open http://localhost:8000/UI%20and%20UX/code.html
```

---

## 6. Integration with Python Backend (`backend/api.py`)

The Flask API serves the approved UI and exposes:

- `GET /api/health` for service and dependency status.
- `GET /api/backend-status` for the UI/backend readiness state.
- `POST /api/llm/answer` for local adapter generation.

The adapter is loaded lazily from `LLM/`. Its compatible base model is read
from `LLM_BASE_MODEL`, defaulting to the model declared by the checked-in
adapter configuration. If dependencies, model files, or network access are
missing, the API returns a clear `503` rather than silently switching models.
