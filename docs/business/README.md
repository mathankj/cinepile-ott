# CinePile Business Docs

Use these documents in client conversations. They tell the same story at three levels of depth.

## What's in this folder

| File | Audience | When to use |
|---|---|---|
| **`features-master-list.md`** | Internal — you + me | Source of truth. Every feature, what phase, what status, what cost. |
| **`phase-1-launch.md`** | Client / partner | First meeting after V1 ships. "Here's what's live right now." |
| **`phase-2-growth.md`** | Client / partner | Quarter 2 review. "Here's what we add to grow revenue + retention." |
| **`phase-3-scale.md`** | Client / partner / investors | Year-end / fund-raise. "Here's what makes us competitive at scale." |

## How to turn these into client artefacts

The markdown is intentionally clean enough to convert to PDF / DOCX / PPT without re-editing:

### To PDF (recommended for client decks)
```bash
# Install pandoc + a LaTeX engine once
choco install pandoc miktex   # Windows
brew install pandoc basictex  # Mac

# Convert
pandoc phase-1-launch.md -o phase-1-launch.pdf --pdf-engine=xelatex
pandoc phase-2-growth.md -o phase-2-growth.pdf --pdf-engine=xelatex
pandoc phase-3-scale.md  -o phase-3-scale.pdf  --pdf-engine=xelatex
```

### To DOCX (for client to annotate)
```bash
pandoc phase-1-launch.md -o phase-1-launch.docx
```

### To PPT slides (for a meeting)
```bash
pandoc phase-1-launch.md -o phase-1-launch.pptx
```

### To XLSX (the master features table specifically)
The master list has tables that copy-paste cleanly into Excel. Or:
```bash
# Extract just the tables and convert
pandoc features-master-list.md -o features-master-list.docx
# then open in Word → Save As Excel
```

## The phased-disclosure pattern

> "Every phase we disable future features and show them, then they believe us."

Concretely, when building the demo for a Phase 1 client meeting:

1. Set an env var `CINEPILE_PHASE=1` in `backend/.env`.
2. Code paths that check `phase >= 2` (or use a feature flag) skip Phase 2 + 3 UI.
3. Hidden routes (`/admin/forensic-watermark`, `/downloads`, etc.) just don't render.
4. Client sees a clean Phase 1 product, not a half-built Phase 3 with broken links.

**Status:** the feature-flag scaffolding is NOT yet built. Today everything renders. If the client meeting is imminent and you want to actually demo a Phase 1-only build, ping me — that's a 1-day implementation (env var + a `<FeatureFlag>` wrapper component).
