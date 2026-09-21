# Mechanics Figure Templates & Publication Guidelines

Comprehensive specification for mechanics visualization templates adhering to top-tier solid mechanics journal standards (JMPS, IJSS, EFM, AMS).

---

## 1. Publication Sizing & Style Guidelines

### Physical Layout Standards
- **Single-column layout**: Target width **85 mm** (3.35 inches). Typical height 60–80 mm.
- **Double-column layout**: Target width **175 mm** (6.89 inches). Typical height 90–120 mm.
- **DPI**: Minimum **300 DPI** for raster output (PNG); vector formats (PDF, SVG) use embedded TrueType curves (pdf.fonttype = 42).
- **Typography**: Primary serif font: Times New Roman / STIXGeneral / DejaVu Serif.
  - Title: 9.0–10.0 pt
  - Axis Labels: 8.5 pt
  - Tick Labels: 7.5 pt
  - Legend: 7.0–7.5 pt
- **Colormaps**:
  - Signed quantities (e.g. sigma_xx, sigma_yy, tau_xy): Zero-centered diverging colormap (`coolwarm`, `seismic`, `RdBu_r`).
  - Positive scalars (e.g. von Mises, Tresca, energy release rate): Perceptually uniform sequential colormap (`viridis`, `plasma`).
  - **Prohibited**: `jet` and `rainbow` are strictly barred due to non-uniform luminance gradients and pseudo-singular visual artifacts.

---

## 2. Five Mechanics Templates

### 2.1 Stress Contour (`stress_contour`)
Used for 2D singular or regular stress fields around cracks, notches, and inclusions.
- **Aspect Ratio**: Must be strictly `equal` to prevent non-physical spatial distortion.
- **Crack Masking**: Internal crack surfaces and void boundaries must be masked with NaN or overlaid with thick crack border lines.
- **Components**: Supports direct 2D `values` or components (`sigma_xx`, `sigma_yy`, `tau_xy`, `sigma_zz`) with automatic calculation of von Mises or Tresca equivalents.

```json
{
  "template": "stress_contour",
  "title": "Crack-Tip Normal Stress sigma_yy",
  "layout": "single_column",
  "data": {
    "x": [-5.0, 0.0, 5.0],
    "y": [-5.0, 0.0, 5.0],
    "field_name": "sigma_yy",
    "unit": "MPa",
    "colormap": "coolwarm",
    "cracks": [
      {"segment": [[-4.0, 0.0], [0.0, 0.0]]}
    ]
  },
  "conventions": {
    "sign_convention": "tension_positive"
  }
}
```

---

### 2.2 SIF Curve (`sif_curve`)
Line plot of normalized Stress Intensity Factor ($K_I / K_0$, $K_{II} / K_0$, $K_{III} / K_0$) vs crack front angle $	heta$ ($0$ to $pi/2$) or relative distance ($h/a, d/a$).
- **Baseline Reference**: Dashed horizontal baseline line at $K_I / K_0 = 1.0$ clearly identifies amplification or shielding.
- **Multi-Curve Comparison**: Supports distinct curves for different material symmetries (transversely isotropic vs isotropic) or spacing ratios.

```json
{
  "template": "sif_curve",
  "title": "Normalized Mode I SIF along Crack Front",
  "layout": "single_column",
  "data": {
    "curves": [
      {
        "label": "Cadmium Selenide (TI)",
        "x": [0.0, 0.785, 1.571],
        "y": [1.18, 1.05, 0.92],
        "color": "#1f77b4"
      },
      {
        "label": "Isotropic Baseline",
        "x": [0.0, 0.785, 1.571],
        "y": [1.00, 1.00, 1.00],
        "color": "#ff7f0e",
        "linestyle": "--"
      }
    ],
    "baseline_reference": true,
    "xlabel": "Crack Front Angle theta [rad]",
    "ylabel": "Normalized SIF K_I / K_0"
  },
  "conventions": {
    "sif_normalization": "standard"
  }
}
```

---

### 2.3 Interaction Heatmap (`interaction_heatmap`)
Discrete matrix visualization for multi-crack interaction matrices $M_{ij}$, transmission coefficients $Lambda_{ij}$, or Kachanov influence factors.
- **Annotations**: Formatted numerical text directly inside matrix cells for matrix dimensions $le 10 	imes 10$.
- **Luminance Adaptivity**: Text color flips between white and black depending on cell background value.

```json
{
  "template": "interaction_heatmap",
  "title": "Crack Interaction Transmission Matrix",
  "layout": "single_column",
  "data": {
    "matrix": [
      [1.00, 0.22, 0.08],
      [0.22, 1.00, 0.25],
      [0.08, 0.25, 1.00]
    ],
    "x_labels": ["Crack 1", "Crack 2", "Crack 3"],
    "y_labels": ["Crack 1", "Crack 2", "Crack 3"],
    "colorbar_label": "Transmission Coefficient Lambda_ij",
    "colormap": "viridis",
    "annotate": true
  }
}
```

---

### 2.4 Asymptotic Comparison (`asymptotic_comparison`)
Two-panel stacked plot verifying mathematical boundary layer expansions.
- **Top Panel**: Global numerical/exact benchmark curve vs inner/outer asymptotic expansions.
- **Bottom Panel**: Relative error $log_{10}|Delta K / K_0| = log_{10} rac{|K_{	ext{asymp}} - K_{	ext{exact}}|}{K_0}$.
- **Singularity Safety**: Protects against log(0) and division by zero.

```json
{
  "template": "asymptotic_comparison",
  "title": "Asymptotic Expansion vs Global Exact Solution",
  "layout": "single_column",
  "data": {
    "x": [0.05, 0.20, 0.50, 0.80],
    "exact": [1.002, 1.041, 1.333, 2.777],
    "exact_label": "Exact Solution",
    "asymptotic": {
      "Order O(eps^2)": [1.002, 1.040, 1.250, 1.640],
      "Order O(eps^4)": [1.002, 1.041, 1.312, 2.050]
    },
    "xlabel": "Small Parameter epsilon = a/h",
    "ylabel": "Normalized SIF K_I / K_0"
  }
}
```

---

### 2.5 Crack Geometry Schematic (`crack_geometry`)
Vector schematic of 2D/3D crack configurations (penny-shaped circular or elliptical cracks, centers, radii $a$, spacing $h, d$, and load arrows).
- **Proportions**: Accurate spatial scaling with equal aspect ratio.
- **Visual Callouts**: Double-headed dimension arrows ($h, 2a$) and external tensile load arrows ($sigma_0$).

```json
{
  "template": "crack_geometry",
  "title": "Interacting Parallel Penny-Shaped Cracks",
  "layout": "single_column",
  "data": {
    "cracks": [
      {"center": [0.0, 1.8], "radius": 1.5, "label": "Crack A (a_1 = 1.5)"},
      {"center": [0.0, -1.8], "radius": 1.5, "label": "Crack B (a_2 = 1.5)"}
    ],
    "loading": {
      "type": "tension",
      "label": "sigma_0 (Far-field tension)"
    },
    "dimensions": [
      {"start": [0.0, -1.8], "end": [0.0, 1.8], "label": "h = 3.6", "label_offset": [0.5, 0.0]}
    ],
    "bounds": [-6, 6, -5, 5]
  }
}
```
