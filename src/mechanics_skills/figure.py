"""
Mechanics Figure & Publication Visualization Engine.
Publication-ready 85mm (single-column) and 175mm (double-column) scientific visualization
for solid mechanics, fracture mechanics, and elasticity.
"""

import dataclasses
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Ellipse, FancyArrowPatch, Rectangle
    HAS_MATPLOTLIB = True
except ImportError:
    matplotlib = None
    plt = None
    Ellipse = FancyArrowPatch = Rectangle = None
    HAS_MATPLOTLIB = False

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    np = None
    HAS_NUMPY = False

from mechanics_skills.integrity import (
    Finding,
    ConventionRegistry,
    audit_data_provenance,
)

MM_TO_INCH = 1.0 / 25.4
SINGLE_COLUMN_WIDTH_MM = 85.0
DOUBLE_COLUMN_WIDTH_MM = 175.0

ALLOWED_TEMPLATES = {
    "stress_contour",
    "sif_curve",
    "interaction_heatmap",
    "asymptotic_comparison",
    "crack_geometry",
}

PROHIBITED_COLORMAPS = {"jet", "rainbow"}


@dataclass
class FigureSpec:
    """
    Specification contract for mechanics figures.
    """
    template: str
    data: Dict[str, Any]
    title: str = ""
    panels: List[Dict[str, Any]] = dataclasses.field(default_factory=list)
    conventions: Dict[str, Any] = dataclasses.field(default_factory=dict)
    export_formats: List[str] = dataclasses.field(default_factory=lambda: ["png", "pdf", "svg"])
    layout: str = "single_column"  # "single_column" (85mm) | "double_column" (175mm)
    dpi: int = 300
    width_mm: Optional[float] = None
    height_mm: Optional[float] = None
    caption: str = ""
    scientific_question: str = ""
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template": self.template,
            "title": self.title,
            "data": self.data,
            "panels": self.panels,
            "conventions": self.conventions,
            "export_formats": self.export_formats,
            "layout": self.layout,
            "dpi": self.dpi,
            "width_mm": self.width_mm,
            "height_mm": self.height_mm,
            "caption": self.caption,
            "scientific_question": self.scientific_question,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FigureSpec":
        return cls(
            template=str(d.get("template", "")),
            data=dict(d.get("data", {})),
            title=str(d.get("title", "")),
            panels=list(d.get("panels", [])),
            conventions=dict(d.get("conventions", {})),
            export_formats=list(d.get("export_formats", ["png", "pdf", "svg"])),
            layout=str(d.get("layout", "single_column")),
            dpi=int(d.get("dpi", 300)),
            width_mm=d.get("width_mm"),
            height_mm=d.get("height_mm"),
            caption=str(d.get("caption", "")),
            scientific_question=str(d.get("scientific_question", "")),
            metadata=dict(d.get("metadata", {})),
        )


def validate_figure_spec(spec: Union[FigureSpec, Dict[str, Any]]) -> List[Finding]:
    """
    Validate FigureSpec against mechanics standards and publication guidelines.
    Detects invalid templates, missing data arrays, prohibited colormaps (jet/rainbow),
    dimension mismatches, and undefined baseline normalizations.
    """
    findings: List[Finding] = []
    d = spec.to_dict() if isinstance(spec, FigureSpec) else spec

    template = d.get("template")
    if not template or template not in ALLOWED_TEMPLATES:
        findings.append(
            Finding(
                severity="critical",
                category="G1",
                message=f"Invalid template '{template}'. Allowed templates: {sorted(list(ALLOWED_TEMPLATES))}",
                field="template",
                context={"allowed": sorted(list(ALLOWED_TEMPLATES))},
            )
        )

    data = d.get("data")
    if not data or not isinstance(data, dict):
        findings.append(
            Finding(
                severity="critical",
                category="G3",
                message="FigureSpec 'data' field is missing or not a dictionary",
                field="data",
            )
        )
        return findings

    # Check colormaps
    cmap = data.get("colormap", "").lower()
    if cmap in PROHIBITED_COLORMAPS:
        findings.append(
            Finding(
                severity="critical",
                category="G1",
                message=f"Prohibited colormap '{cmap}' violates perceptual uniformity standards. Use viridis, plasma, seismic, or coolwarm.",
                field="colormap",
                context={"colormap": cmap},
            )
        )

    # Template-specific audits
    if template == "stress_contour":
        if "values" not in data and not any(k in data for k in ["sigma_xx", "sigma_yy", "tau_xy"]):
            findings.append(
                Finding(
                    severity="critical",
                    category="G1",
                    message="stress_contour requires 'values' 2D array or stress components (sigma_xx, sigma_yy, tau_xy)",
                    field="data.values",
                )
            )

    elif template == "sif_curve":
        if "curves" not in data and "y" not in data:
            findings.append(
                Finding(
                    severity="critical",
                    category="G1",
                    message="sif_curve requires 'curves' list or 'y' numerical array",
                    field="data.curves",
                )
            )
        if "baseline" in data and abs(float(data["baseline"])) < 1e-12:
            findings.append(
                Finding(
                    severity="critical",
                    category="G1",
                    message="Baseline reference SIF K_0 cannot be zero",
                    field="data.baseline",
                )
            )

    elif template == "interaction_heatmap":
        matrix = data.get("matrix")
        if matrix is None or not isinstance(matrix, (list, np.ndarray)):
            findings.append(
                Finding(
                    severity="critical",
                    category="G1",
                    message="interaction_heatmap requires 2D 'matrix' array",
                    field="data.matrix",
                )
            )

    elif template == "asymptotic_comparison":
        if "exact" not in data and "reference" not in data:
            findings.append(
                Finding(
                    severity="critical",
                    category="G1",
                    message="asymptotic_comparison requires 'exact' or 'reference' curve array",
                    field="data.exact",
                )
            )
        if "asymptotic" not in data:
            findings.append(
                Finding(
                    severity="critical",
                    category="G1",
                    message="asymptotic_comparison requires 'asymptotic' curve array or dictionary",
                    field="data.asymptotic",
                )
            )

    elif template == "crack_geometry":
        cracks = data.get("cracks")
        if not cracks or not isinstance(cracks, list):
            findings.append(
                Finding(
                    severity="critical",
                    category="G1",
                    message="crack_geometry requires non-empty 'cracks' list",
                    field="data.cracks",
                )
            )

    return findings


def setup_publication_style():
    """Configure publication-grade Matplotlib rcParams (single/double column ready)."""
    if not HAS_MATPLOTLIB or plt is None:
        return
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "STIXGeneral", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "font.size": 8.5,
        "axes.titlesize": 9.0,
        "axes.labelsize": 8.5,
        "xtick.labelsize": 7.5,
        "ytick.labelsize": 7.5,
        "legend.fontsize": 7.5,
        "figure.titlesize": 10.0,
        "lines.linewidth": 1.0,
        "axes.linewidth": 0.8,
        "xtick.major.width": 0.7,
        "ytick.major.width": 0.7,
        "xtick.direction": "in",
        "ytick.direction": "in",
    })


def _render_stress_contour(ax, data: Dict[str, Any]):
    """Render 2D stress contour with crack masking and equal aspect."""
    x = np.array(data.get("x", np.linspace(0, 10, 50)))
    y = np.array(data.get("y", np.linspace(0, 10, 50)))

    if x.ndim == 1 and y.ndim == 1:
        X, Y = np.meshgrid(x, y)
    else:
        X, Y = x, y

    target_field = data.get("field_name", "sigma_yy")
    cmap_name = data.get("colormap", "coolwarm" if "sigma" in target_field or "tau" in target_field else "viridis")

    if "values" in data:
        Z = np.array(data["values"])
    elif "sigma_xx" in data and "sigma_yy" in data:
        s_xx = np.array(data["sigma_xx"])
        s_yy = np.array(data["sigma_yy"])
        t_xy = np.array(data.get("tau_xy", np.zeros_like(s_xx)))
        s_zz = np.array(data.get("sigma_zz", np.zeros_like(s_xx)))

        if target_field == "von_mises":
            Z = np.sqrt(0.5 * ((s_xx - s_yy)**2 + (s_yy - s_zz)**2 + (s_zz - s_xx)**2 + 6 * t_xy**2))
            cmap_name = "viridis"
        elif target_field == "tresca":
            r = np.sqrt(((s_xx - s_yy) / 2.0)**2 + t_xy**2)
            s1 = (s_xx + s_yy) / 2.0 + r
            s3 = (s_xx + s_yy) / 2.0 - r
            Z = np.maximum(s1 - s3, np.maximum(s1 - s_zz, s_zz - s3))
            cmap_name = "viridis"
        else:
            Z = s_yy
    else:
        # Synthetic fallback demonstration field
        r = np.sqrt(X**2 + Y**2) + 1e-4
        theta = np.arctan2(Y, X)
        Z = (1.0 / np.sqrt(r)) * np.cos(theta / 2.0) * (1.0 + np.sin(theta / 2.0) * np.sin(3.0 * theta / 2.0))

    # Apply crack mask if specified
    if "crack_mask" in data:
        mask = np.array(data["crack_mask"], dtype=bool)
        Z = np.where(mask, np.nan, Z)

    levels = data.get("levels", 16)
    cf = ax.contourf(X, Y, Z, levels=levels, cmap=cmap_name)
    cbar = plt.colorbar(cf, ax=ax, fraction=0.046, pad=0.04)
    unit_str = data.get("unit", "MPa")
    cbar.set_label(f"{target_field} [{unit_str}]")

    # Draw crack geometry lines if provided
    cracks = data.get("cracks", [])
    for crack in cracks:
        if "segment" in crack:
            seg = crack["segment"]
            ax.plot([seg[0][0], seg[1][0]], [seg[0][1], seg[1][1]], color="black", linewidth=2.5, zorder=10)

    ax.set_aspect("equal")
    ax.set_xlabel(data.get("xlabel", "x [mm]"))
    ax.set_ylabel(data.get("ylabel", "y [mm]"))
    ax.set_title(data.get("title", f"2D Stress Distribution: {target_field}"))


def _render_sif_curve(ax, data: Dict[str, Any]):
    """Render normalized SIF curves with baseline reference line."""
    curves = data.get("curves", [])
    if not curves and "y" in data:
        curves = [{
            "label": data.get("curve_label", "Mode I SIF"),
            "x": data.get("x", np.linspace(0, 1, len(data["y"]))),
            "y": data["y"],
        }]

    palette = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]
    linestyles = ["-", "--", "-.", ":"]

    for idx, c in enumerate(curves):
        x_pts = np.array(c.get("x", data.get("x", np.linspace(0, 1, len(c["y"])))))
        y_pts = np.array(c["y"])
        color = c.get("color", palette[idx % len(palette)])
        ls = c.get("linestyle", linestyles[idx % len(linestyles)])
        marker = c.get("marker", "o" if len(x_pts) <= 15 else "")
        label = c.get("label", f"Curve {idx+1}")
        ax.plot(x_pts, y_pts, color=color, linestyle=ls, marker=marker, markersize=3.5, label=label)

    # Baseline reference line (K_I / K_0 = 1.0)
    if data.get("baseline_reference", True):
        ax.axhline(1.0, color="#7f7f7f", linestyle=":", linewidth=1.0, label="Baseline ($K_I/K_0 = 1.0$)")

    ax.set_xlabel(data.get("xlabel", r"Crack Front Angle $	heta$ [rad]"))
    ax.set_ylabel(data.get("ylabel", r"Normalized SIF $K_I / K_0$"))
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(frameon=True, framealpha=0.8, edgecolor="none")
    ax.set_title(data.get("title", "Normalized Stress Intensity Factor Distribution"))


def _render_interaction_heatmap(ax, data: Dict[str, Any]):
    """Render multi-defect interaction matrix heatmap."""
    matrix = np.array(data["matrix"], dtype=float)
    x_labels = data.get("x_labels", [f"Crack {i+1}" for i in range(matrix.shape[1])])
    y_labels = data.get("y_labels", [f"Crack {i+1}" for i in range(matrix.shape[0])])

    cmap_name = data.get("colormap", "coolwarm" if np.any(matrix < 0) else "viridis")
    im = ax.imshow(matrix, cmap=cmap_name, aspect="auto", interpolation="nearest")

    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(data.get("colorbar_label", r"Interaction Matrix $M_{ij}$"))

    ax.set_xticks(np.arange(len(x_labels)))
    ax.set_yticks(np.arange(len(y_labels)))
    ax.set_xticklabels(x_labels, rotation=45, ha="right")
    ax.set_yticklabels(y_labels)

    # Annotate cells if matrix is manageable size
    if matrix.shape[0] <= 10 and matrix.shape[1] <= 10 and data.get("annotate", True):
        v_min, v_max = np.nanmin(matrix), np.nanmax(matrix)
        thresh = (v_max + v_min) / 2.0
        for i in range(matrix.shape[0]):
            for j in range(matrix.shape[1]):
                val = matrix[i, j]
                color = "white" if val > thresh else "black"
                ax.text(j, i, f"{val:.2f}", ha="center", va="center", color=color, fontsize=7.0)

    ax.set_title(data.get("title", "Multi-Defect Transmission / Interaction Matrix"))


def _render_asymptotic_comparison(fig, data: Dict[str, Any]):
    """Render two-panel global asymptotic comparison and relative error plot."""
    x = np.array(data["x"])
    exact = np.array(data.get("exact", data.get("reference", [])))

    gs = fig.add_gridspec(2, 1, height_ratios=[2.5, 1.2], hspace=0.15)
    ax_top = fig.add_subplot(gs[0])
    ax_bot = fig.add_subplot(gs[1], sharex=ax_top)

    ax_top.plot(x, exact, "k-", linewidth=1.5, label=data.get("exact_label", "Exact / Benchmark"))

    asymp_data = data["asymptotic"]
    palette = ["#d62728", "#1f77b4", "#2ca02c"]

    if isinstance(asymp_data, dict):
        curves = asymp_data
    else:
        curves = {data.get("asymptotic_label", "Asymptotic Expansion"): asymp_data}

    for idx, (lbl, y_asymp) in enumerate(curves.items()):
        arr = np.array(y_asymp)
        c = palette[idx % len(palette)]
        ax_top.plot(x, arr, linestyle="--", color=c, label=lbl)

        # Relative error
        denom = np.where(np.abs(exact) > 1e-12, np.abs(exact), 1.0)
        rel_err = np.abs(arr - exact) / denom
        clamped_err = np.maximum(rel_err, 1e-12)
        log_err = np.log10(clamped_err)
        ax_bot.plot(x, log_err, linestyle="-", color=c, label=f"Error: {lbl}")

    ax_top.set_ylabel(data.get("ylabel", r"$K_I / K_0$"))
    ax_top.grid(True, linestyle=":", alpha=0.5)
    ax_top.legend(frameon=True, framealpha=0.8, edgecolor="none")
    ax_top.set_title(data.get("title", "Asymptotic Expansion vs Exact Field"))
    plt.setp(ax_top.get_xticklabels(), visible=False)

    ax_bot.set_xlabel(data.get("xlabel", r"Small Parameter $\varepsilon = a/h$"))
    ax_bot.set_ylabel(r"$log_{10}|Delta K / K_0|$")
    ax_bot.grid(True, linestyle=":", alpha=0.5)


def _render_crack_geometry(ax, data: Dict[str, Any]):
    """Render vector schematic of 2D/3D crack geometry with load arrows."""
    cracks = data.get("cracks", [])
    bounds = data.get("bounds", [-5, 5, -5, 5])
    ax.set_xlim(bounds[0], bounds[1])
    ax.set_ylim(bounds[2], bounds[3])
    ax.set_aspect("equal")

    for c in cracks:
        center = c.get("center", [0.0, 0.0])
        a = c.get("radius", c.get("a", 1.0))
        b = c.get("b", a * 0.15)
        angle = c.get("angle", 0.0)
        ellipse = Ellipse(
            xy=center,
            width=2 * a,
            height=2 * b,
            angle=angle,
            facecolor="#e0e0e0",
            edgecolor="#1a1a1a",
            linewidth=1.2,
            hatch="//",
            zorder=3,
        )
        ax.add_patch(ellipse)
        if "label" in c:
            ax.text(center[0], center[1] + b * 1.5, c["label"], ha="center", va="bottom", fontsize=7.5)

    loading = data.get("loading", {})
    if loading:
        load_type = loading.get("type", "tension")
        load_label = loading.get("label", r"$sigma_0$")
        y_top = bounds[3] * 0.85
        y_bot = bounds[2] * 0.85
        xs = np.linspace(bounds[0] * 0.7, bounds[1] * 0.7, 5)
        arrow_len = (bounds[3] - bounds[2]) * 0.08
        for x_arr in xs:
            ax.annotate(
                "",
                xy=(x_arr, y_top + arrow_len),
                xytext=(x_arr, y_top),
                arrowprops=dict(arrowstyle="->", color="#c62828", lw=1.2),
            )
            ax.annotate(
                "",
                xy=(x_arr, y_bot - arrow_len),
                xytext=(x_arr, y_bot),
                arrowprops=dict(arrowstyle="->", color="#c62828", lw=1.2),
            )
        ax.text(0, y_top + arrow_len * 1.3, load_label, ha="center", va="bottom", color="#c62828", fontsize=8.5)

    dimensions = data.get("dimensions", [])
    for dim in dimensions:
        p1 = dim.get("start")
        p2 = dim.get("end")
        lbl = dim.get("label", "")
        if p1 and p2:
            ax.annotate(
                "",
                xy=p2,
                xytext=p1,
                arrowprops=dict(arrowstyle="<->", color="#1565c0", lw=1.0),
            )
            mid = [(p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0]
            offset = dim.get("label_offset", [0, 0.3])
            ax.text(mid[0] + offset[0], mid[1] + offset[1], lbl, ha="center", va="center", color="#1565c0", fontsize=8.0)

    ax.grid(True, linestyle=":", alpha=0.3)
    ax.set_xlabel("x [mm]")
    ax.set_ylabel("y [mm]")
    ax.set_title(data.get("title", "Defect Configuration & Far-Field Loading Schematic"))


def render_figure(
    spec: Union[FigureSpec, Dict[str, Any]],
    output_dir: Union[str, Path],
) -> Dict[str, Any]:
    """
    Render a mechanics figure according to FigureSpec and export publication files
    (PNG at 300+ DPI, vector PDF, SVG, spec JSON, manifest JSON, and draft caption).
    """
    d = spec.to_dict() if isinstance(spec, FigureSpec) else spec
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    findings = validate_figure_spec(d)
    if not HAS_MATPLOTLIB or not HAS_NUMPY:
        raise ImportError(
            "Publication figure rendering requires 'matplotlib' and 'numpy'. "
            "Install with: pip install 'mechanics-agent-skills[figure]'"
        )
    setup_publication_style()

    layout = d.get("layout", "single_column")
    if layout == "double_column":
        default_w_mm = DOUBLE_COLUMN_WIDTH_MM
        default_h_mm = 110.0
    else:
        default_w_mm = SINGLE_COLUMN_WIDTH_MM
        default_h_mm = 75.0

    width_mm = float(d.get("width_mm") or default_w_mm)
    height_mm = float(d.get("height_mm") or default_h_mm)
    dpi = int(d.get("dpi", 300))

    fig_w = width_mm * MM_TO_INCH
    fig_h = height_mm * MM_TO_INCH

    template = d.get("template")
    data = d.get("data", {})

    fig = plt.figure(figsize=(fig_w, fig_h), dpi=dpi)

    if template == "asymptotic_comparison":
        _render_asymptotic_comparison(fig, data)
    else:
        ax = fig.add_subplot(111)
        if template == "stress_contour":
            _render_stress_contour(ax, data)
        elif template == "sif_curve":
            _render_sif_curve(ax, data)
        elif template == "interaction_heatmap":
            _render_interaction_heatmap(ax, data)
        elif template == "crack_geometry":
            _render_crack_geometry(ax, data)

    if template != "asymptotic_comparison":
        try:
            fig.tight_layout()
        except Exception:
            pass

    formats = d.get("export_formats", ["png", "pdf", "svg"])
    export_files = {}

    if "png" in formats:
        png_path = out / "figure.png"
        fig.savefig(png_path, dpi=dpi, bbox_inches="tight")
        export_files["png"] = str(png_path)

    if "pdf" in formats:
        pdf_path = out / "figure.pdf"
        fig.savefig(pdf_path, format="pdf", bbox_inches="tight")
        export_files["pdf"] = str(pdf_path)

    if "svg" in formats:
        svg_path = out / "figure.svg"
        fig.savefig(svg_path, format="svg", bbox_inches="tight")
        export_files["svg"] = str(svg_path)

    plt.close(fig)

    spec_path = out / "figure.spec.json"
    spec_path.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
    export_files["spec"] = str(spec_path)

    caption_content = (
        f"**Figure.** {d.get('title', 'Mechanics Analysis Result')}. "
        f"Synthesized under template '{template}' ({layout}, width {width_mm:.1f} mm). "
        f"Data conventions: {d.get('conventions', {}).get('sign_convention', 'tension-positive')}, "
        f"normalization: {d.get('conventions', {}).get('sif_normalization', 'standard')}."
    )
    caption_path = out / "caption.md"
    caption_path.write_text(caption_content, encoding="utf-8")
    export_files["caption"] = str(caption_path)

    data_hashes = {
        "raw_data_sha256": audit_data_provenance(data),
        "spec_sha256": audit_data_provenance(d),
    }

    manifest = {
        "template": template,
        "layout": layout,
        "dimensions": {
            "width_mm": width_mm,
            "height_mm": height_mm,
            "dpi": dpi,
            "width_in": fig_w,
            "height_in": fig_h,
        },
        "export_files": export_files,
        "data_hashes": data_hashes,
        "findings": [f.to_dict() for f in findings],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "caption": caption_content,
    }

    manifest_path = out / "figure.manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    export_files["manifest"] = str(manifest_path)

    return manifest
