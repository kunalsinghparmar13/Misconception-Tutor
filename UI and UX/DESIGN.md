---
name: Tutor Minimalist Learning Engine
colors:
  surface: '#f8f9fa'
  surface-dim: '#d9dadb'
  surface-bright: '#f8f9fa'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f3f4f5'
  surface-container: '#edeeef'
  surface-container-high: '#e7e8e9'
  surface-container-highest: '#e1e3e4'
  on-surface: '#191c1d'
  on-surface-variant: '#45464c'
  inverse-surface: '#2e3132'
  inverse-on-surface: '#f0f1f2'
  outline: '#76777d'
  outline-variant: '#c6c6cd'
  surface-tint: '#575e70'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#141b2b'
  on-primary-container: '#7d8497'
  inverse-primary: '#c0c6db'
  secondary: '#4b41e1'
  on-secondary: '#ffffff'
  secondary-container: '#645efb'
  on-secondary-container: '#fffbff'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#00201d'
  on-tertiary-container: '#0c9488'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dce2f7'
  primary-fixed-dim: '#c0c6db'
  on-primary-fixed: '#141b2b'
  on-primary-fixed-variant: '#404758'
  secondary-fixed: '#e2dfff'
  secondary-fixed-dim: '#c3c0ff'
  on-secondary-fixed: '#0f0069'
  on-secondary-fixed-variant: '#3323cc'
  tertiary-fixed: '#89f5e7'
  tertiary-fixed-dim: '#6bd8cb'
  on-tertiary-fixed: '#00201d'
  on-tertiary-fixed-variant: '#005049'
  background: '#f8f9fa'
  on-background: '#191c1d'
  surface-variant: '#e1e3e4'
typography:
  display:
    fontFamily: Geist
    fontSize: 2.25rem
    fontWeight: '600'
    lineHeight: 2.75rem
    letterSpacing: -0.03em
  display-mobile:
    fontFamily: Geist
    fontSize: 1.75rem
    fontWeight: '600'
    lineHeight: 2.25rem
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Geist
    fontSize: 1.5rem
    fontWeight: '600'
    lineHeight: 2rem
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Geist
    fontSize: 1.25rem
    fontWeight: '500'
    lineHeight: 1.75rem
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Geist
    fontSize: 1rem
    fontWeight: '600'
    lineHeight: 1.5rem
    letterSpacing: -0.005em
  body-lg:
    fontFamily: Geist
    fontSize: 1.0625rem
    fontWeight: '400'
    lineHeight: 1.75rem
    letterSpacing: -0.005em
  body-md:
    fontFamily: Geist
    fontSize: 0.9375rem
    fontWeight: '400'
    lineHeight: 1.6rem
    letterSpacing: 0em
  body-sm:
    fontFamily: Geist
    fontSize: 0.8125rem
    fontWeight: '400'
    lineHeight: 1.375rem
    letterSpacing: 0.005em
  code-block:
    fontFamily: JetBrains Mono
    fontSize: 0.875rem
    fontWeight: '400'
    lineHeight: 1.5rem
    letterSpacing: -0.01em
  code-inline:
    fontFamily: JetBrains Mono
    fontSize: 0.8125rem
    fontWeight: '500'
    lineHeight: 1.25rem
    letterSpacing: 0em
  label-md:
    fontFamily: JetBrains Mono
    fontSize: 0.75rem
    fontWeight: '500'
    lineHeight: 1rem
    letterSpacing: 0.04em
  label-sm:
    fontFamily: JetBrains Mono
    fontSize: 0.6875rem
    fontWeight: '500'
    lineHeight: 0.875rem
    letterSpacing: 0.06em
rounded:
  sm: 0.5rem
  DEFAULT: 1rem
  md: 1.5rem
  lg: 2rem
  xl: 3rem
  full: 9999px
spacing:
  gutter: 1.5rem
  gutter-mobile: 1rem
  margin: 2rem
  margin-mobile: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style

The design system embodies an austere, intellectual minimalism engineered for deep comprehension and cognitive flow. Tailored for students, researchers, developers, and autodidacts navigating dense subjects—such as advanced calculus, algorithmic theory, and systems architecture—the interface recedes completely, leaving the dialogue between human and AI front and center.

The aesthetic fuses crisp editorial typography with technical rigor, heavily influenced by contemporary generative AI platforms (Claude, ChatGPT, Linear) and classic scientific publishing. It prioritizes information hierarchy, extreme typographical legibility, and distraction-free spatial composition. UI scaffolding remains quiet and structural: wire-thin hairline dividers, balanced neutral tones, subdued status badges, and precise iconography evoke academic authority, trust, and serene focus.

## Colors

The palette is rooted in ultra-clean neutral slate with purposeful, high-utility accents:

- **Primary (`#111827`):** Deep graphite/ink, establishing an uncompromising high-contrast anchor for typography, active icons, and primary interaction targets. In dark mode, this flips to a crisp `#F9FAFB`.
- **Secondary (`#4F46E5`):** Subtle indigo accent reserved for primary operational moments, subject state highlights (e.g., active STEM pills), and synthetic inline references.
- **Tertiary (`#0D9488`):** Deep teal for verified proofs, successful code executions, and analytical feedback loops.
- **Neutral Canvas (`#F9FAFB` in light, `#0D0F12` in dark):** Clean, non-distracting foundation. Structural borders use `#E5E7EB` in light mode and `#2D3139` in dark mode. Surface containers elevate through micro-contrasts (`#FFFFFF` in light, `#16191E` in dark) rather than noisy drop shadows.

## Typography

Typography is calibrated to maximize sustained reading stamina across prose, complex mathematical formulations (KaTeX/LaTeX), and multi-language syntax. 

- **Primary Prose Engine (Geist):** Handles conversational responses, system messages, and titles. Built on low geometric friction and neutral sans-serif terminals, ensuring reading naturalness without visual clutter.
- **Technical Engine (JetBrains Mono):** Dedicated to technical data, code blocks, keyboard shortcuts, subject badges, and metadata labels. The open apertures and monospaced glyph balance provide unambiguous differentiation between numerals, characters, and syntax operators (e.g., `0` vs `O`, `l` vs `1`).
- **Mathematical Formulations:** Rendered via LaTeX standard styling, normalized to match `body-lg` scale and baseline rhythm.

## Layout & Spacing

The interface employs a split application model with a collapsible sidebar and a centered, fixed-width conversation viewport:

- **Sidebar Rails:** A compact, 260px wide collapsible rail for conversation history, pinned subject workspaces, and user profiles. Collapses down to 0 on mobile into an overlay drawer.
- **Reading Viewport:** Content is bound to a strict `max-w-3xl` (48rem / 768px) centered column. This guarantees optimal typographic line length (between 65 to 80 characters per line) for cognitive assimilation.
- **Floating Input Anchor:** The prompt composer rests pinned at the bottom viewport center, floating within the `max-w-3xl` constraint, suspended with dynamic bottom margins to maintain clear visual separation from ongoing threads.
- **Breakpoints:**
  - `sm` (640px): Sidebar collapses; margins reduce to `margin-mobile` (1rem); font scales shift to mobile tiers.
  - `md` (768px): Sidebar toggle visible; full composer features enabled.
  - `lg` (1024px+): Desktop layout; sticky subject selector chips; auxiliary side panels (e.g., interactive code output or dynamic canvas) open adjacent to the thread.

## Elevation & Depth

Visual hierarchy rejects exaggerated, heavy shadows in favor of crisp tonal stacking and architectural hairline borders:

- **Base Layer (L0):** Default background canvas (`#F9FAFB` light / `#0D0F12` dark).
- **Surface Elevation (L1):** Sidebar panels and code containers sit on `#FFFFFF` (light) or `#16191E` (dark), demarcated cleanly by 1px solid hairline borders (`#E5E7EB` / `#2D3139`).
- **Floating Overlays (L2):** The prompt composer and floating contextual toolbars leverage backdrop blur (`backdrop-blur-md`, 12px) paired with semi-translucent fills (`rgba(255, 255, 255, 0.85)` in light, `rgba(22, 25, 30, 0.85)` in dark) and ambient, ultra-diffused drop shadows (`0 8px 30px rgba(0, 0, 0, 0.04)` in light, `0 8px 30px rgba(0, 0, 0, 0.35)` in dark).
- **No Heavy Skewing:** Elevation informs position and priority, never ornament. Flat surfaces meet sharp borders for an organized, precision-tool feel.

## Shapes

The system embraces a high-order roundedness geometry (`roundedness: 3`) that juxtaposes sweeping pill elements with crisp rectangular structural wrappers:

- **Pill Geometry (Full Radius):** Context-switching subject tabs, status pills, floating action buttons, command pills, and attachment tags are rendered as complete pills (`rounded-full`). This softens user entry points and makes interactive capsules immediately distinct from content blocks.
- **Composer Capsule (`rounded-2xl` to `rounded-3xl`):** The floating input box utilizes a 24px–32px radius, delivering an approachable, unified dock for message entry and tool switches.
- **Code & Content Blocks (`rounded-xl` / 12px):** Mathematical solution callouts, interactive IDE sandboxes, and quoted citations adopt a tighter 12px border radius, maintaining efficient horizontal and vertical screen real estate.

## Components

### Subject Switching Tabs (Pill Tabs)
- **Geometry & Tokens:** Compact horizontal pill-shaped controls (`rounded-full`, height 32px, `space-sm` internal padding).
- **Visuals:** Thin hairline border (`#E5E7EB` / `#2D3139`). Inactive tabs use transparent backgrounds with muted body text (`#6B7280`). Active tabs switch to solid high-contrast fills (`#111827` light / `#F9FAFB` dark) with inverted text, or subtle indigo tint (`#EEF2FF` light / `#312E81` dark) with `#4F46E5` icons.
- **Iconography:** Monospaced and unicode subject symbols positioned left of text label (e.g., `∑` for Mathematics, `</>` for Python, `⚛` for Physics, `§` for Humanities).

### Floating Prompt Composer
- **Structure:** Centered floating container (`max-w-3xl`) suspended 1.5rem above the bottom viewport edge.
- **Styling:** Dynamic textarea without resize handle, wrapped in an L2 translucent surface (`rounded-2xl`, 1px border `#E5E7EB` / `#2D3139`, backdrop-blur).
- **Integrated Utilities:** Bottom utility bar hosting active subject chip, file/context attachment trigger (paperclip icon), token count indicator (`label-sm`), and an energetic circular send button (black pill with crisp white directional arrow).

### Code Blocks & Math Callouts
- **Code Canvas:** Integrated header bar containing language name (`label-md`, JetBrains Mono), file path, and a one-click "Copy Code" ghost button. Monospaced body with optional syntax highlight themes (GitHub Light / Tokyo Night dark).
- **Inline Code:** Wrapped in `#F3F4F6` (light) or `#1F242C` (dark) with `0.25rem` radius, 1px hairline border, and `JetBrains Mono` font.
- **Math Formulations:** Center-aligned display blocks with soft vertical rhythm (`space-md`), rendered in high-definition SVG vectors with LaTeX fallback.

### Inputs & Toggles
- **Input Fields:** Flat, minimalist inputs with zero focus glow. Focused state transitions border color directly to `#111827` (light) or `#9CA3AF` (dark).
- **Checkboxes & Radios:** Sharp, understated controls with solid neutral fill on select; intended for multiple-choice quiz queries and self-assessment modules.

### Compact Sidebar
- **Layout:** Vertical stack featuring brand mark (`Tutor`), followed by "New Session" button, followed by date-grouped history lists (`body-sm`).
- **Row States:** Active conversation item rendered with background `#F3F4F6` (light) or `#1F242C` (dark), paired with a 2-dot context menu appearing on hover.