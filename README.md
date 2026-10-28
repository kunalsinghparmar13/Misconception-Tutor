# Misconception Tutor

**A tutor that finds the real reason you're stuck.**

Built for *Theme 5: AI That Teaches, Problem 8* at the IIT Bombay hackathon.

![tests](https://github.com/<team>/<repo>/actions/workflows/tests.yml/badge.svg)

> Struggling with maths usually isn't about missing facts. It's one specific misunderstanding that produces the same kind of mistake again and again. This project traces a wrong answer back to the likely misconception, explains it, and generates a new problem aimed at exactly that misconception.

**Live demo:** `<add Streamlit URL here>`  |  **Demo video:** `<add link here>`  |  **Slides:** `<add link here>`

---

## What it does

1. **Diagnoses** a learner's wrong answer into one of 5 fraction-arithmetic misconceptions (or says "unknown" when unsure).
2. **Explains** the likely mistake, including a "why we think this" replay that shows the exact steps of the buggy rule that would produce the learner's answer.
3. **Generates** a new practice problem that exposes the same misconception, with every answer verified by exact arithmetic.
4. **Remembers** each learner across sessions and shows how often each misconception still appears.
5. **Chooses the next question adaptively** by picking the problem that tells us the most about which misconception the learner holds (expected information gain).

### Example

| | |
|---|---|
| Problem | 1/4 + 1/6 |
| Learner answers | 1/5 |
| Diagnosis | Adds tops and bottoms (M1) |
| Replay | (1+1) over (4+6) = 2/10 = 1/5, which is exactly your answer |
| Next problem | 1/6 + 1/9, built so M1 gives a wrong answer different from the other bugs |

*(Add screenshots of the practice, feedback, profile, and teacher screens in `docs/`.)*

## The core idea: misconceptions as "buggy rules"

A misconception behaves like a bug in the learner's mental program. Apply the buggy rule and you get a predictable wrong answer, so wrong answers act like fingerprints.

| ID | Misconception | Example | Wrong answer | Correct |
|---|---|---|---|---|
| M1 | Add across (add tops and add bottoms) | 1/4 + 1/6 | 2/10 (= 1/5) | 5/12 |
| M2 | Add tops, multiply bottoms | 1/4 + 1/6 | 2/24 (= 1/12) | 5/12 |
| M3 | Common denominator found, numerators not scaled | 1/4 + 1/6 | 2/12 (= 1/6) | 5/12 |
| M4 | Divide without flipping | 1/2 ÷ 1/4 | 1/8 | 2 |
| M5 | Flips the wrong fraction when dividing | 1/2 ÷ 1/4 | 1/2 | 2 |

Because each bug can be computed, we **generate labeled training data ourselves** and test on **real, hand-labeled answers** collected from people.

## How it works

```
Learner answer -> Diagnosis (classifier) -> Explanation + replay
      ^                                              |
      |                                              v
  Tracker (SQLite) <-- Targeted problem generator <--+
      |
      +--> Adaptive question picker (information gain)
```

| Module | Folder | Purpose |
|---|---|---|
| Buggy rules | `problems/bugs.py` | One function per misconception |
| Problem generator | `problems/` | Targeted problems, verified with exact fractions |
| Diagnosis | `diagnosis/` | Feature extraction, classifier, adaptive picker |
| Tracking | `tracking/` | SQLite attempts, per-learner profile |
| App | `UI and UX/`, `backend/` | Approved tutor interface connected to the local LLM |

## Quick start

Requires Python 3.11 or newer, Git LFS, and enough local memory for the
adapter's compatible base model.

```bash
git clone https://github.com/kunalsinghparmar13/Misconception-Tutor.git
cd Misconception-Tutor
git lfs pull
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m backend.api
```

Open `http://localhost:8000`. The approved interface is `UI and UX/code.html`.
The backend serves that interface and routes every answer through the PEFT
adapter in `LLM/`. Set `LLM_BASE_MODEL` to override the base model named in
`LLM/adapter_config.json`.

## Project structure

```
UI and UX/code.html     # approved responsive tutor interface
UI and UX/app.js        # sends composer questions to the backend
backend/api.py          # Flask server and local LLM adapter runtime
backend/backend_code.py # exact arithmetic and misconception engine
LLM/                    # PEFT adapter, tokenizer, and checkpoints
.github/workflows/      # CI (runs pytest)
```

## Runtime contract

The Flask service serves `UI and UX/code.html` at `/`, serves its browser bridge
at `/app.js`, and exposes `/api/llm/answer` for tutor responses. The service
uses only the checked-in PEFT adapter in `LLM/`; if the adapter dependencies or
compatible base model are unavailable, it returns an explicit error instead of
starting a different frontend or answer provider.

## Data

| Source | Use |
|---|---|
| Synthetic (generated from the buggy rules, with noise) | Training the classifier |
| Real answers collected with a Google Form and labeled by hand (`data/real_test.csv`) | **Test set only**, never used for training |
| Public datasets such as ASSISTments and Eedi | Background and taxonomy inspiration |

Regenerate synthetic data:

```bash
python data/gen_synthetic.py
```

## Model and evaluation

The classifier uses hand-built features (does the answer's numerator equal a+c, does its denominator equal b+d, b×d, or lcm(b, d), does its value match each bug's predicted value, and so on) with a scikit-learn model. If the top probability is below a threshold, it answers "unknown" instead of guessing.

Train and evaluate:

```bash
python diagnosis/train.py
```

**Results on the real hand-labeled test set** *(fill in with your real numbers)*

| Metric | Our classifier | LLM zero-shot baseline |
|---|---|---|
| Accuracy | TBD | TBD |
| Macro F1 | TBD | TBD |
| Test set size | TBD | TBD |

Confusion matrix: `docs/confusion_matrix.png` *(add)*.

The LLM is **never** used to decide the diagnosis. It is only an optional baseline for comparison and, if enabled, a way to reword explanations. All explanations also have a template fallback, so the app works offline.

## Adaptive diagnosis

Some wrong answers cannot separate two misconceptions. For example, on 1/2 + 1/3 both M2 and M3 give 2/6. The system keeps a probability for each misconception and picks the next problem with the highest **expected information gain**. Here, 1/4 + 1/6 separates M1, M2, and M3 completely.

**Simulated-student experiment:** questions needed to identify the hidden misconception, random vs adaptive. *(Add chart `docs/adaptive_vs_random.png` and the numbers.)*

## Does it help? Pre/post study

- Participants: **TBD** (tutor group n = TBD, control group n = TBD)
- Design: pre-test, 15 minutes with the tutor or ordinary practice, post-test with different numbers
- Result: bug rate per misconception before and after, per group *(add `docs/study_results.png`)*

**Honest limitations:** very small sample, short intervention, same-day retest. The results show direction, not proof, and we do not claim statistical significance.

## Tests

```bash
pytest -q
```

Tests check that every generated problem gives a wrong, unique answer for its target bug, that the classifier handles known examples, that the tracker computes profiles correctly, and that odd inputs such as `abc` or `1/0` do not crash the app. CI runs them on every push and pull request.

## Deployment

The app is deployed on Streamlit Community Cloud from the `main` branch with `streamlit_app.py` as the entry file. Free hosting has limits: apps sleep after a period of no visitors and storage is temporary, so the hosted version uses seeded demo data. Real study sessions were run locally.

## Privacy and ethics

- Study participants were told what the study was and took part voluntarily.
- Only anonymous learner IDs are stored. No names, emails, or other personal data.
- The real study data is kept out of this public repository.

## Known limitations

- Covers only fraction addition and division (5 misconceptions). The pipeline is domain-independent, but other domains are future work.
- Real test data is small, and some answers can be explained by more than one misconception.
- Learners' careless slips can look like misconceptions. The "unknown" option and repeated evidence reduce this but do not remove it.
- The study is small and short.

## Future work

- More topics (percentages, signed numbers, algebra) and a Python-errors taxonomy
- Hindi / Hinglish input and a taxonomy built from Indian school syllabi
- Step-by-step work instead of final answers only
- Larger, longer study with real classrooms

## Team

| Name | Role | Owns |
|---|---|---|
| `<Name>` | Member A: Diagnosis (ML) | `diagnosis/`, `problems/bugs.py`, `models/`, `notebooks/` |
| `<Name>` | Member B: Problems, tracking, data | `problems/generator.py`, `tracking/`, `data/seed_demo.py` |
| `<Name>` | Member C: App, study, story | `streamlit_app.py`, `pages/`, `docs/`, `.github/` |

Contribution workflow: branch from `main`, open a pull request, get one review from a teammate before merging. Never commit directly to `main`.

## References

- Brown, J. S. and Burton, R. R. (1978). Diagnostic models for procedural bugs in basic mathematical skills. *Cognitive Science*.
- Corbett, A. T. and Anderson, J. R. (1995). Knowledge tracing: modeling the acquisition of procedural knowledge. *User Modeling and User-Adapted Interaction*.
- ASSISTments public datasets.
- Eedi diagnostic questions datasets and the Kaggle "Mining Misconceptions in Mathematics" competition.

## License

`<Choose one, for example MIT>`. See `LICENSE`.
