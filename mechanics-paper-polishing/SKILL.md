---
name: mechanics-paper-polishing
description: Academic paper polishing and notation integrity guard for solid mechanics, fracture mechanics, and elasticity. Enforces mathematical formula protection (display/inline math, citations, labels, units), eliminates AI clichés with active mechanics phrasing, guards against high-risk notation ambiguities (COD vs single-side w, Sneddon k_I vs Irwin K_I, engineering vs tensorial shear), and prepares constrained host LLM editing proposals. Use when polishing mechanics manuscripts, auditing math preservation, stripping AI fluff, or validating text edit proposals.
metadata:
  version: "3.1.0"
  domain: "Solid Mechanics / Fracture Mechanics / Academic Publishing"
---

# Mechanics Paper Polishing & Notation Guard

Automated, evidence-anchored academic paper polishing suite designed specifically for theoretical and computational mechanics manuscripts.
Guarantees mathematical formula preservation with cryptographic SHA-256 protection zones, guards against domain notation confusions, eliminates AI fluff, and enforces deterministic edit validation.

---

## 1. When to Use
- Polishing draft manuscripts (Markdown or LaTeX) for top mechanics journals (JMPS, IJSS, EFM, AMS).
- Protecting complex LaTeX math environments (equations, aligns, inline formulas, citations, units) from unauthorized modification.
- Auditing high-risk mechanics notation ambiguities:
  - Crack opening displacement ($COD = 2w$ vs single-side displacement $w$).
  - Stress Intensity Factor normalizations (Irwin $K_I$ vs Sneddon/Barenblatt $k_I = K_I / \sqrt{\pi}$).
  - Shear strain conventions (engineering $\gamma_{xy}$ vs tensorial $\varepsilon_{xy}$).
  - Plane stress vs plane strain assumptions and effective moduli.
- Removing generic AI clichés (`delve`, `pivotal`, `testament`, `foster`, `tapestry`, `underscores`) in favor of direct, active physical phrasing.
- Validating host model editing proposals before applying changes.

---

## 2. Core Capabilities

### A. Protection Zone Tokenizer
- Identifies and locks all mathematical formulas ($...$, $$...$$, \begin{equation}...\end{equation}, \begin{align}...\end{align}).
- Locks citations (\cite{...}, [@...]), cross-references (\ref{...}, \eqref{...}, \label{...}), and code blocks.
- Locks physical numerical quantities with physical units (e.g. `120 GPa`, `25.4 MPa\sqrt{m}`, `0.25 mm`).
- Computes cryptographic SHA-256 hashes to ensure zero formula tampering.

### B. Mechanics Notation Guard
- **Displacement Jump vs Half-Crack Displacement**: Warns if $w$ and $COD$ are used together without stating $COD = 2w$ (for symmetric Mode I) or $[u] \cdot n$.
- **SIF Definition Ambiguity**: Detects potential $\sqrt{\pi}$ factor confusion between Irwin and Sneddon definitions.
- **Shear Component Consistency**: Verifies clear distinction between engineering shear $\gamma_{xy} = 2\varepsilon_{xy}$ and tensorial shear $\varepsilon_{xy}$.
- **Overstated Certainty Prevention**: Blocks attempts to describe numerical/FEA simulations as closed-form "exact solutions".

### C. AI Cliché & Fluff Stripper
- Detects non-mechanics fluff outside protected regions.
- Replaces passive promotional adjectives with active physical verbs (subject + physical action + condition + observable).

---

## 3. Workflow & CLI Commands

### Step 1: Analyze Manuscript
```bash
mechanics-polish analyze manuscript.md
```

### Step 2: Prepare Constrained Task Package for Host LLM
```bash
mechanics-polish prepare manuscript.md --output-dir artifacts/polish_run
```
Generates `polish_request.json` with strict constraints, protected spans, and expected `proposals.json` schema. Status is marked `needs_authoring`.

### Step 3: Validate Host Model Edit Proposals
```bash
mechanics-polish validate manuscript.md proposals.json
```
Blocks any edit that modifies protected math zones, introduces new clichés, or creates overlapping character ranges.

### Step 4: Apply Validated Edits
```bash
mechanics-polish apply manuscript.md proposals.json --output polished_manuscript.md --diff diff_records.json
```
Original manuscript is never modified in place; safe new output file is generated.
