"""
Unit tests for mechanics figure engine (specification validation, 5 templates rendering, exports, CLI).
"""

import json
from pathlib import Path
import numpy as np
import pytest

from mechanics_skills.figure import (
    FigureSpec,
    validate_figure_spec,
    render_figure,
    SINGLE_COLUMN_WIDTH_MM,
    DOUBLE_COLUMN_WIDTH_MM,
)
from mechanics_skills.cli import figure_cli


def test_validate_figure_spec_valid():
    """Verify that a well-formed spec passes validation without critical findings."""
    spec = {
        "template": "sif_curve",
        "title": "Mode I SIF",
        "data": {
            "curves": [{"label": "TI Medium", "x": [0, 1], "y": [1.0, 1.2]}],
            "baseline": 1.0,
        },
    }
    findings = validate_figure_spec(spec)
    assert not any(f.severity == "critical" for f in findings)


def test_validate_figure_spec_invalid_template():
    """Verify that an unknown template triggers a critical finding."""
    spec = {"template": "pie_chart", "data": {"slices": [1, 2, 3]}}
    findings = validate_figure_spec(spec)
    assert any(f.severity == "critical" and "Invalid template" in f.message for f in findings)


def test_validate_figure_spec_missing_data():
    """Verify that missing data field triggers a critical finding."""
    spec = {"template": "stress_contour"}
    findings = validate_figure_spec(spec)
    assert any(f.severity == "critical" and "data" in f.field for f in findings)


def test_validate_figure_spec_prohibited_colormap():
    """Verify that jet and rainbow colormaps are strictly rejected."""
    spec = {
        "template": "stress_contour",
        "data": {
            "values": [[1, 2], [3, 4]],
            "colormap": "jet",
        },
    }
    findings = validate_figure_spec(spec)
    assert any(f.severity == "critical" and "Prohibited colormap 'jet'" in f.message for f in findings)


def test_render_stress_contour(tmp_path):
    """Test rendering 2D stress contour template with crack masking."""
    out_dir = tmp_path / "stress_contour"
    x = np.linspace(-4, 4, 25).tolist()
    y = np.linspace(-4, 4, 25).tolist()

    spec = FigureSpec(
        template="stress_contour",
        layout="single_column",
        title="Crack-Tip Stress Contour",
        data={
            "x": x,
            "y": y,
            "field_name": "sigma_yy",
            "unit": "MPa",
            "colormap": "coolwarm",
            "cracks": [{"segment": [[-3, 0], [0, 0]]}],
        },
    )

    manifest = render_figure(spec, out_dir)
    assert manifest["template"] == "stress_contour"
    assert manifest["dimensions"]["width_mm"] == SINGLE_COLUMN_WIDTH_MM

    for ext in ["png", "pdf", "svg"]:
        f_path = Path(manifest["export_files"][ext])
        assert f_path.is_file()
        assert f_path.stat().st_size > 0

    assert (out_dir / "figure.manifest.json").is_file()
    assert (out_dir / "caption.md").is_file()


def test_render_sif_curve(tmp_path):
    """Test rendering normalized SIF curve template."""
    out_dir = tmp_path / "sif_curve"
    theta = np.linspace(0, np.pi / 2, 20).tolist()
    sif_vals = (1.0 + 0.15 * np.cos(2 * np.array(theta))).tolist()

    spec = FigureSpec(
        template="sif_curve",
        layout="single_column",
        title="Normalized SIF vs Crack Front Angle",
        data={
            "curves": [
                {"label": "Cadmium Selenide", "x": theta, "y": sif_vals, "color": "#1f77b4"},
                {"label": "Isotropic Baseline", "x": theta, "y": [1.0] * len(theta), "color": "#ff7f0e", "linestyle": "--"},
            ],
            "baseline_reference": True,
        },
    )

    manifest = render_figure(spec, out_dir)
    assert manifest["template"] == "sif_curve"
    for ext in ["png", "pdf", "svg"]:
        f_path = Path(manifest["export_files"][ext])
        assert f_path.is_file()
        assert f_path.stat().st_size > 0


def test_render_interaction_heatmap(tmp_path):
    """Test rendering multi-defect interaction matrix heatmap with annotations."""
    out_dir = tmp_path / "heatmap"
    mat = [
        [1.00, 0.20, 0.05],
        [0.20, 1.00, 0.25],
        [0.05, 0.25, 1.00],
    ]

    spec = FigureSpec(
        template="interaction_heatmap",
        layout="single_column",
        title="Crack Interaction Matrix",
        data={
            "matrix": mat,
            "x_labels": ["C1", "C2", "C3"],
            "y_labels": ["C1", "C2", "C3"],
            "annotate": True,
        },
    )

    manifest = render_figure(spec, out_dir)
    assert manifest["template"] == "interaction_heatmap"
    assert (out_dir / "figure.png").is_file()
    assert (out_dir / "figure.pdf").is_file()
    assert (out_dir / "figure.svg").is_file()


def test_render_asymptotic_comparison(tmp_path):
    """Test rendering two-panel asymptotic comparison with relative error subpanel."""
    out_dir = tmp_path / "asymptotic"
    x = np.linspace(0.02, 0.80, 25).tolist()
    exact = (1.0 / (1.0 - np.array(x)**2)).tolist()
    asymp = (1.0 + np.array(x)**2).tolist()

    spec = FigureSpec(
        template="asymptotic_comparison",
        layout="double_column",
        title="Asymptotic Expansion Comparison",
        data={
            "x": x,
            "exact": exact,
            "asymptotic": {"Leading Order": asymp},
        },
    )

    manifest = render_figure(spec, out_dir)
    assert manifest["template"] == "asymptotic_comparison"
    assert manifest["dimensions"]["width_mm"] == DOUBLE_COLUMN_WIDTH_MM
    assert (out_dir / "figure.png").is_file()
    assert (out_dir / "figure.pdf").is_file()
    assert (out_dir / "figure.svg").is_file()


def test_render_crack_geometry(tmp_path):
    """Test rendering vector schematic of crack geometry with load arrows."""
    out_dir = tmp_path / "geometry"
    spec = FigureSpec(
        template="crack_geometry",
        layout="single_column",
        title="Parallel Penny-Shaped Cracks",
        data={
            "cracks": [
                {"center": [0, 1.5], "radius": 1.2, "label": "Crack 1"},
                {"center": [0, -1.5], "radius": 1.2, "label": "Crack 2"},
            ],
            "loading": {"type": "tension", "label": "sigma_0"},
            "dimensions": [{"start": [0, -1.5], "end": [0, 1.5], "label": "h = 3.0"}],
        },
    )

    manifest = render_figure(spec, out_dir)
    assert manifest["template"] == "crack_geometry"
    assert (out_dir / "figure.png").is_file()
    assert (out_dir / "figure.pdf").is_file()
    assert (out_dir / "figure.svg").is_file()


def test_figure_cli_workflow(tmp_path):
    """Test CLI template generation, validation, and rendering workflow."""
    spec_path = tmp_path / "sif_spec.json"
    out_dir = tmp_path / "cli_output"

    # 1. Generate template via CLI
    code = figure_cli(["template", "sif_curve", "--output", str(spec_path)])
    assert code == 0
    assert spec_path.is_file()

    # 2. Validate template via CLI
    val_code = figure_cli(["validate", str(spec_path)])
    assert val_code == 0

    # 3. Render template via CLI
    render_code = figure_cli(["render", str(spec_path), "--output-dir", str(out_dir)])
    assert render_code == 0
    assert (out_dir / "figure.png").is_file()
    assert (out_dir / "figure.pdf").is_file()
    assert (out_dir / "figure.svg").is_file()
    assert (out_dir / "figure.manifest.json").is_file()
