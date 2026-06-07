# 📄 Résumé Screening System

> Rank candidates against a job description **objectively** — built with pure Python and **multiprocessing**.

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-pytest-brightgreen)
![UI](https://img.shields.io/badge/web-Streamlit-ff4b4b)

Hiring starts with one painfully manual task: reading résumés. This project
automates the first pass. Give it a folder of résumés (PDF / DOCX / TXT) and a
job description, and it produces a **ranked leaderboard** — scoring every
candidate against the *same* weighted rubric so the result doesn't depend on
writing style, formatting, or unconscious bias.

It ships with both a **command-line tool** (which screens résumés in parallel
across your CPU cores) and a **Streamlit web app**.

> 💡 **Using it on yourself?** Drop your own CV into the `input/` folder (or
> upload it in the web app) and screen it against a job posting to see which
> required skills you're matching — and which you're missing — *before* you hit
> "Apply".

---

## ✨ Features

- **Multi-format parsing** — extracts clean text from `.pdf`, `.docx` and `.txt`.
- **Skills taxonomy** — 150+ skills across software, data, business analysis and
  **HR** (Workday, SuccessFactors, recruiting, people analytics, …), each with
  spelling variations and word-boundary matching (so "Java" ≠ "JavaScript").
- **Transparent weighted scoring** — required vs. preferred skills, experience
  and keywords, each with a configurable weight.
- **Real multiprocessing** — a `multiprocessing.Pool` screens résumés in
  parallel, one worker per CPU core.
- **Two interfaces** — a CLI (`main.py`) and a web app (`app.py`).
- **Tested** — a `pytest` suite plus GitHub Actions CI on Python 3.9–3.12.

---

## 🧠 How it works

```
 Input                      Processing                        Output
 ─────                      ──────────                        ──────

 Résumés ──► Résumé Parser ──► Keyword Extractor ──┐
 (PDF/DOCX/TXT)                                     │
                                                    ├──► Scoring Engine ──► Ranked leaderboard
 Job Description ──► JD Parser ─────────────────────┘
 (TXT/PDF)
```

1. **Résumé Parser** turns each document into plain text.
2. **JD Parser** reads the job description and splits it into *required skills*,
   *preferred skills*, a *minimum experience* figure and *keywords*.
3. **Keyword Extractor** matches résumé text against the skills taxonomy.
4. **Scoring Engine** applies the weighted formula and ranks everyone.

### Scoring formula

```
Total Score = (Required Skills × 50%)
            + (Preferred Skills × 25%)
            + (Experience       × 15%)
            + (Keywords         × 10%)
```

| Component        | Weight | Rationale                  |
| ---------------- | :----: | -------------------------- |
| Required Skills  |  50%   | Essential technical needs  |
| Preferred Skills |  25%   | Competitive differentiators|
| Experience       |  15%   | Professional depth         |
| Keywords         |  10%   | Domain familiarity         |

Each component is a **coverage ratio** (0–1) of how much of what the job asks for
appears in the résumé, so the final score is naturally bounded to **0–100**. The
weights live in [`data/config.json`](data/config.json) — change them without
touching any code.

### Why multiprocessing?

Parsing PDFs and scanning text is CPU-bound work that's **embarrassingly
parallel** — each résumé is independent. The CLI uses a `multiprocessing.Pool`
to spread that work across all your cores:

- `process_resume` is a top-level function so it pickles cleanly to workers
  (required on Windows/macOS `spawn`).
- Heavy objects (the taxonomy-backed extractor, the scorer) are built **once per
  worker** via the pool `initializer`, not once per résumé.
- Falls back to sequential mode automatically if a pool can't be created.

Benchmark the difference yourself:

```bash
python main.py --sequential   # one process
python main.py                # all cores
```

---

## 📁 Project structure

```
resume_screening_system/
├── app.py                      # Streamlit web interface
├── main.py                     # Command-line interface + multiprocessing pipeline
├── parsers/
│   ├── resume_parser.py        # PDF/DOCX/TXT text extraction
│   └── jd_parser.py            # Job-description parsing
├── extractors/
│   └── keyword_extractor.py    # Skills, experience & keyword extraction
├── matcher/
│   └── scorer.py               # Weighted scoring algorithm
├── data/
│   ├── config.json             # Scoring weights
│   └── skills_taxonomy.json    # Skills database
├── samples/                    # Ready-to-run example résumés & job descriptions
├── tests/                      # pytest suite
├── input/                      # ← drop your own résumés here
├── output/                     # ← results.csv is written here
└── requirements.txt
```

---

## 🚀 Getting started

### 1. Install

```bash
git clone https://github.com/jeanvaljean1812/r-sum-screening-system.git
cd r-sum-screening-system

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Run from the command line

```bash
# Screen the bundled sample résumés against the sample Python-developer role
python main.py

# Use a different job description and your own résumé folder
python main.py --jd samples/job_descriptions/hr_people_analytics.txt --resumes input

# Useful options
python main.py --workers 4      # set the number of parallel processes
python main.py --top 5          # only show the top 5
python main.py --sequential     # disable multiprocessing
python main.py --help           # all options
```

### 3. Run the web app

```bash
streamlit run app.py
```

Then open <http://localhost:8501>, paste a job description, upload résumés and
click **Screen Résumés**.

### 4. Test your own CV

1. Put your CV (PDF/DOCX/TXT) in the `input/` folder.
2. Pick or paste the job description you're applying for.
3. Run `python main.py --resumes input --jd <your-jd-file>` (or use the web app).
4. See your score and exactly which required skills you matched or missed.

---

## 🧪 Sample output

```
============================================================
SCREENING RESULTS
============================================================
Rank #1: Alice Johnson | Score: 95.33/100 | Matched: Django, Python, REST APIs, SQL, AWS (+2 more)
Rank #2: Carol Davis | Score: 70.33/100 | Matched: Django, Python, REST APIs, SQL
Rank #3: Frank Chen | Score: 35.67/100 | Matched: Python, SQL
============================================================
```

A detailed `output/results.csv` with the per-component point breakdown is written
on every run.

---

## ⚖️ A note on bias

This system scores every résumé against the **same** predefined criteria —
required skills, preferred skills, experience and keywords — instead of
subjective judgment. Because the rubric is identical for everyone, factors like
writing style, formatting or unconscious preference don't move the ranking.

That said, keyword matching is a **first-pass filter, not a hiring decision**.
A taxonomy can only find what's in it, and a great candidate may describe their
experience in words it doesn't recognise. Use it to *triage and to understand
your own CV*, and keep a human in the loop.

---

## 🛠️ Configuration

- **Weights** — edit [`data/config.json`](data/config.json).
- **Skills** — add to [`data/skills_taxonomy.json`](data/skills_taxonomy.json).
  Each skill maps a canonical name to a list of lowercase variations:

  ```json
  "Power BI": ["power bi", "powerbi"]
  ```

---

## ✅ Running the tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

---

## ☁️ Deploying to Streamlit Cloud

1. Push this repository to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. Create a new app, select this repo and set the main file to `app.py`.
4. Deploy — your app will be live at `https://<your-app-name>.streamlit.app`.

---

## 🗺️ Possible improvements

- Semantic matching with embeddings (catch synonyms the taxonomy misses).
- Section-aware parsing (separate education / experience / skills).
- Configurable per-skill weights and "must-have" knock-out rules.
- Export to PDF/Excel reports.

---

## 🙏 Credits

Inspired by the freeCodeCamp tutorial
[*How to Build a Résumé Screening System Using Python and Multiprocessing*](https://www.freecodecamp.org/news/python-resume-screening-system/)
by **Abdul Talha**. This implementation follows that article's architecture and
scoring formula, and fills in the full working code (parsers, scorer,
multiprocessing pipeline, web app, sample data and tests).

## 📜 License

[MIT](LICENSE)
