# UI and UX — Misconception Tutor Design Prototype

Exported design prototype from **Google Stitch** (`stitch.withgoogle.com`) for **Theme 5: AI That Teaches (Misconception Tutor)**.

## Files
- **[`code.html`](code.html)**: Self-contained, responsive HTML5 + Tailwind CSS web dashboard.
- **[`DESIGN.md`](DESIGN.md)**: Design system tokens (colors, typography, spacing, elevation).
- **[`screen.png`](screen.png)**: Visual preview of the design prototype.
- **[`EXPLANATION.md`](EXPLANATION.md)**: Detailed code walkthrough, component breakdown, and backend integration guide.

## Quick View
Open [`code.html`](code.html) directly in any modern browser:
```bash
open "UI and UX/code.html"
```

For the connected application, run the Python backend from the repository root:

```bash
./run_app.sh
```

Then open `http://localhost:8000`. The Send button uses the checked-in PEFT
adapter in `LLM/` through `/api/llm/answer`; it does not call a hosted AI
provider or generate a client-side fallback answer. The adapter's compatible
base model is read from `LLM_BASE_MODEL`, defaulting to
`unsloth/gemma-4-E4B-it-unsloth-bnb-4bit`.
