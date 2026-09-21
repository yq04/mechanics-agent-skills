---
name: mechanics-figure
description: Publication-ready scientific visualization and verification engine for solid mechanics and fracture mechanics. Generates 85mm single-column and 175mm double-column figures adhering to journal standards (300+ DPI, vector PDF/SVG, perceptual colormaps, crack masking, SIF curves, interaction heatmaps, asymptotic comparisons, and crack schematics). Use when rendering publication figures, plotting stress contours, analyzing SIF curves, verifying data provenance, or auditing mechanics figure layouts.
metadata:
  version: "3.1.0"
  domain: "Solid Mechanics / Fracture Mechanics / Computational Mechanics"
---

# Mechanics Figure & Publication Visualization Engine

Automated, publication-grade visualization and verification suite for solid mechanics, fracture mechanics, and elasticity.
Enforces rigorous journal standards (JMPS, IJSS, EFM, AMS), strict dimension compliance (85 mm single-column, 175 mm double-column), perceptual colormap integrity, vector PDF/SVG exports, and cryptographic data provenance.

---

## 1. When to Use
- Generating journal-ready figures for mechanics research papers.
- Plotting 2D stress fields ($sigma_{xx}, sigma_{yy}, 	au_{xy}$, von Mises, Tresca) with equal aspect ratio and crack surface masking.
- Generating normalized Stress Intensity Factor (SIF) curves ($K_I / K_0$) vs crack front angle $	heta$ or distance $h/a$ with baseline reference lines.
- Visualizing multi-defect transmission / interaction matrices $M_{ij}$ with annotated heatmaps.
- Comparing global exact/numerical solutions with inner/outer asymptotic expansions and relative error subplots.
- Creating vector schematics of crack configurations (centers, radii $a$, spacing $h, d$, load arrows).
- Auditing raw dataset cryptographic hashes (SHA-256) and verifying constitutive positive definiteness before publication.

---

## 2. Fast CLI Commands

### Render Figure from Specification
```bash
mechanics-figure render spec.json --output-dir artifacts/figure_output
```

### Validate Specification against Mechanics Standards
```bash
mechanics-figure validate spec.json
```

### Generate Sample Specification Template
```bash
# Available templates: stress_contour, sif_curve, interaction_heatmap, asymptotic_comparison, crack_geometry
mechanics-figure template sif_curve --output examples/sif_spec.json
```

### CLI Wrapper Script
```bash
python mechanics-figure/scripts/render_mechanics_figure.py render spec.json --output-dir out/
```

---

## 3. Python API Quickstart

```python
from mechanics_skills.figure import FigureSpec, render_figure

# Define a publication-ready SIF curve figure
spec = FigureSpec(
    template="sif_curve",
    layout="single_column",  # 85 mm target width
    title="Mode I SIF along Crack Front",
    data={
        "curves": [
            {
                "label": "Cadmium Selenide (TI)",
                "x": [0.0, 0.4, 0.8, 1.2, 1.57],
                "y": [1.18, 1.14, 1.05, 0.96, 0.92],
                "color": "#1f77b4"
            }
        ],
        "baseline_reference": True,
        "xlabel": r"Crack Front Angle $	heta$ [rad]",
        "ylabel": r"Normalized SIF $K_I / K_0$",
    },
    conventions={"sif_normalization": "standard"},
)

# Render figure: exports PNG (300 DPI), vector PDF, SVG, spec JSON, and manifest JSON
manifest = render_figure(spec, output_dir="artifacts/sif_figure")
print(f"Rendered to: {manifest['export_files']}")
```

---

## 4. Output Artifacts

Every figure render produces a complete audit bundle in the target directory:
- `figure.png`: High-resolution bitmap (300+ DPI).
- `figure.pdf`: Publication-grade vector format with embedded TrueType fonts (fonttype = 42).
- `figure.svg`: Clean vector graphics suitable for web or post-processing.
- `figure.spec.json`: The exact FigureSpec input used for reproducible rendering.
- `caption.md`: Draft publication caption stating title, conventions, and normalization facts.
- `figure.manifest.json`: Cryptographic manifest containing SHA-256 data hashes, physical dimensions, and audit findings.
