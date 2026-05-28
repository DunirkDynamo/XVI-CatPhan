"""Standalone whole-image mirror-correlation experiment for the CTP486 module.

This script mirrors the XVI-CatPhan loading and module-location flow, then
builds a 3-slice average of the CTP486 uniformity module and computes two
symmetry-correlation curves:

- horizontal pass: original image vs. left-right mirrored image across x shifts
- vertical pass: original image vs. up-down mirrored image across y shifts

Outputs:
- a TSV table of correlation vs shift for both passes
- a summary text file with the peak shifts and inferred center estimate
- a styled PNG plot showing the averaged image and both correlation curves
"""

from __future__ import annotations

import argparse
import os
import sys
import tkinter as tk
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple
from tkinter import filedialog

import matplotlib.pyplot as plt
import numpy as np
import pydicom as dicom


def _bootstrap_repo_imports() -> None:
    """Allow imports from the local XVI-CatPhan src tree when run as a script."""
    repo_root = Path(__file__).resolve().parents[1]
    src_dir = repo_root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


_bootstrap_repo_imports()

from catphan_analysis.utils.geometry import SliceLocator  # noqa: E402
from catphan_analysis.utils.image_processing import ImageProcessor  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run whole-image mirror-correlation center estimation on the CTP486 module."
    )
    parser.add_argument(
        "dicom_path",
        nargs="?",
        help="Path to the DICOM study directory. If omitted, opens a folder picker.",
    )
    parser.add_argument(
        "--output-dir",
        help="Directory for plots and text outputs (default: same as dicom_path)",
    )
    parser.add_argument(
        "--max-shift",
        type=int,
        default=None,
        help="Maximum absolute shift in pixels to evaluate per axis (default: half image size minus 1)",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=180,
        help="Output DPI for the saved plot",
    )
    return parser.parse_args()


def select_folder() -> Path | None:
    """Open a folder-selection dialog using the same flow as catphan-select."""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    folder_path = filedialog.askdirectory(
        title="Select folder containing DICOM files",
        mustexist=True,
    )

    root.destroy()

    if folder_path:
        return Path(folder_path)
    return None


def load_dicom_files(dicom_path: Path) -> List:
    """Load and sort DICOM files using the same ordering rules as XVI-CatPhan."""
    dicom_pairs: List[Tuple[float, object]] = []
    missing_slice_location = 0

    for root, _, filenames in os.walk(dicom_path):
        for filename in filenames:
            if not filename.lower().endswith(".dcm"):
                continue

            dcm_path = Path(root, filename)
            try:
                ds = dicom.dcmread(dcm_path, force=True)
                ds.file_meta.TransferSyntaxUID = dicom.uid.ImplicitVRLittleEndian

                sort_value = None
                if hasattr(ds, "SliceLocation"):
                    sort_value = float(ds.SliceLocation)
                elif hasattr(ds, "ImagePositionPatient") and len(ds.ImagePositionPatient) >= 3:
                    sort_value = float(ds.ImagePositionPatient[2])
                elif hasattr(ds, "InstanceNumber"):
                    sort_value = float(ds.InstanceNumber)

                if sort_value is None:
                    missing_slice_location += 1
                    sort_value = float(len(dicom_pairs))

                dicom_pairs.append((sort_value, ds))
            except Exception as exc:
                print(f"Skipping {dcm_path.name}: {exc}")

    if missing_slice_location > 0:
        print(
            "Warning: "
            f"{missing_slice_location} file(s) missing SliceLocation; used fallback sort keys."
        )

    dicom_pairs.sort(key=lambda item: item[0], reverse=True)
    dicom_set = [ds for _, ds in dicom_pairs]
    print(f"Loaded {len(dicom_set)} DICOM files")
    return dicom_set


def average_ctp486_image(dicom_set: Sequence) -> Tuple[np.ndarray, int]:
    """Locate CTP486 exactly as XVI-CatPhan does and return the 3-slice average."""
    locator = SliceLocator(list(dicom_set))
    slice_indices = locator.locate_all_modules()
    idx_486 = slice_indices["ctp486"]
    image = ImageProcessor.average_slices(dicom_set, [idx_486 - 1, idx_486, idx_486 + 1])
    print(f"Located CTP486 at slice index {idx_486}")
    return np.asarray(image, dtype=float), int(idx_486)


def normalized_overlap_correlation(a: np.ndarray, b: np.ndarray) -> float:
    """Return a Pearson-like normalized correlation for two same-shaped arrays."""
    flat_a = np.ravel(a).astype(float)
    flat_b = np.ravel(b).astype(float)

    if flat_a.size == 0 or flat_b.size == 0:
        return float("nan")

    flat_a = flat_a - np.mean(flat_a)
    flat_b = flat_b - np.mean(flat_b)

    denom = np.linalg.norm(flat_a) * np.linalg.norm(flat_b)
    if denom == 0:
        return float("nan")
    return float(np.dot(flat_a, flat_b) / denom)


def horizontal_overlap(image: np.ndarray, mirrored: np.ndarray, shift: int) -> Tuple[np.ndarray, np.ndarray]:
    """Return overlapping regions for a horizontal shift of the mirrored image."""
    if shift >= 0:
        return image[:, shift:], mirrored[:, : image.shape[1] - shift]
    return image[:, : image.shape[1] + shift], mirrored[:, -shift:]


def vertical_overlap(image: np.ndarray, mirrored: np.ndarray, shift: int) -> Tuple[np.ndarray, np.ndarray]:
    """Return overlapping regions for a vertical shift of the mirrored image."""
    if shift >= 0:
        return image[shift:, :], mirrored[: image.shape[0] - shift, :]
    return image[: image.shape[0] + shift, :], mirrored[-shift:, :]


def mirror_correlation_curve(image: np.ndarray, axis: str, max_shift: int | None) -> Tuple[np.ndarray, np.ndarray]:
    """Compute correlation as a function of shift for one mirror axis."""
    if axis not in {"horizontal", "vertical"}:
        raise ValueError("axis must be 'horizontal' or 'vertical'")

    if axis == "horizontal":
        mirrored = np.fliplr(image)
        default_limit = image.shape[1] // 2 - 1
        overlap_fn = horizontal_overlap
    else:
        mirrored = np.flipud(image)
        default_limit = image.shape[0] // 2 - 1
        overlap_fn = vertical_overlap

    limit = default_limit if max_shift is None else min(int(max_shift), default_limit)
    shifts = np.arange(-limit, limit + 1, dtype=int)
    correlations = np.empty_like(shifts, dtype=float)

    for index, shift in enumerate(shifts):
        region_a, region_b = overlap_fn(image, mirrored, int(shift))
        correlations[index] = normalized_overlap_correlation(region_a, region_b)

    return shifts, correlations


def infer_center_from_peaks(image: np.ndarray, shift_x: int, shift_y: int) -> Tuple[float, float]:
    """Convert mirror-correlation peak shifts into an estimated center location."""
    midpoint_x = (image.shape[1] - 1) / 2.0
    midpoint_y = (image.shape[0] - 1) / 2.0
    center_x = midpoint_x + shift_x / 2.0
    center_y = midpoint_y + shift_y / 2.0
    return center_x, center_y


def refine_peak_subpixel(shifts: np.ndarray, correlations: np.ndarray) -> Tuple[float, float, int]:
    """Refine the correlation peak with a 3-point parabolic fit when possible."""
    peak_index = int(np.nanargmax(correlations))
    peak_shift = float(shifts[peak_index])
    peak_corr = float(correlations[peak_index])

    if peak_index == 0 or peak_index == len(correlations) - 1:
        return peak_shift, peak_corr, peak_index

    left_corr = float(correlations[peak_index - 1])
    center_corr = peak_corr
    right_corr = float(correlations[peak_index + 1])
    denominator = left_corr - 2.0 * center_corr + right_corr
    if denominator == 0:
        return peak_shift, peak_corr, peak_index

    delta = 0.5 * (left_corr - right_corr) / denominator
    if abs(delta) > 1.0:
        return peak_shift, peak_corr, peak_index

    refined_shift = peak_shift + delta
    refined_corr = center_corr - 0.25 * (left_corr - right_corr) * delta
    return float(refined_shift), float(refined_corr), peak_index


def save_curve_table(output_path: Path, shifts_x: np.ndarray, corr_x: np.ndarray, shifts_y: np.ndarray, corr_y: np.ndarray) -> None:
    """Save the correlation curves as a tab-separated text file."""
    max_len = max(len(shifts_x), len(shifts_y))
    with open(output_path, "w", encoding="ascii") as handle:
        handle.write(
            "horizontal_shift_px\thorizontal_correlation\tvertical_shift_px\tvertical_correlation\n"
        )
        for idx in range(max_len):
            hx = str(int(shifts_x[idx])) if idx < len(shifts_x) else ""
            hc = f"{corr_x[idx]:.8f}" if idx < len(corr_x) else ""
            vy = str(int(shifts_y[idx])) if idx < len(shifts_y) else ""
            vc = f"{corr_y[idx]:.8f}" if idx < len(corr_y) else ""
            handle.write(f"{hx}\t{hc}\t{vy}\t{vc}\n")


def save_summary(
    output_path: Path,
    image: np.ndarray,
    idx_486: int,
    shift_x: float,
    corr_x: float,
    shift_y: float,
    corr_y: float,
) -> None:
    """Save the peak-shift summary and inferred center estimate."""
    center_x, center_y = infer_center_from_peaks(image, shift_x, shift_y)
    midpoint_x = (image.shape[1] - 1) / 2.0
    midpoint_y = (image.shape[0] - 1) / 2.0

    with open(output_path, "w", encoding="ascii") as handle:
        handle.write(f"ctp486_slice_index\t{idx_486}\n")
        handle.write(f"image_width\t{image.shape[1]}\n")
        handle.write(f"image_height\t{image.shape[0]}\n")
        handle.write(f"image_midpoint_x\t{midpoint_x:.3f}\n")
        handle.write(f"image_midpoint_y\t{midpoint_y:.3f}\n")
        handle.write(f"peak_horizontal_shift_px\t{shift_x:.6f}\n")
        handle.write(f"peak_horizontal_correlation\t{corr_x:.8f}\n")
        handle.write(f"peak_vertical_shift_px\t{shift_y:.6f}\n")
        handle.write(f"peak_vertical_correlation\t{corr_y:.8f}\n")
        handle.write(f"estimated_center_x\t{center_x:.3f}\n")
        handle.write(f"estimated_center_y\t{center_y:.3f}\n")


def _style_axes(ax: plt.Axes) -> None:
    ax.set_facecolor("#fcfcf8")
    ax.grid(True, alpha=0.18, linewidth=0.8)
    for spine in ax.spines.values():
        spine.set_color("#4d4d4d")
        spine.set_linewidth(0.8)


def save_plot(
    output_path: Path,
    image: np.ndarray,
    shifts_x: np.ndarray,
    corr_x: np.ndarray,
    shifts_y: np.ndarray,
    corr_y: np.ndarray,
    shift_x_peak: float,
    corr_x_peak: float,
    shift_y_peak: float,
    corr_y_peak: float,
    dpi: int,
) -> None:
    """Render a styled diagnostic figure showing the image and correlation curves."""
    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "figure.facecolor": "#f5f1e8",
            "savefig.facecolor": "#f5f1e8",
        }
    )

    est_center_x, est_center_y = infer_center_from_peaks(image, shift_x_peak, shift_y_peak)
    midpoint_x = (image.shape[1] - 1) / 2.0
    midpoint_y = (image.shape[0] - 1) / 2.0

    fig = plt.figure(figsize=(12.5, 8.0), constrained_layout=True)
    grid = fig.add_gridspec(2, 2, width_ratios=[1.05, 1.15], height_ratios=[1.0, 1.0])
    ax_image = fig.add_subplot(grid[:, 0])
    ax_h = fig.add_subplot(grid[0, 1])
    ax_v = fig.add_subplot(grid[1, 1])

    ax_image.imshow(image, cmap="bone")
    ax_image.scatter([midpoint_x], [midpoint_y], s=70, c="#d1495b", marker="+", linewidths=1.6, label="Image midpoint")
    ax_image.scatter([est_center_x], [est_center_y], s=48, c="#2c7a7b", marker="o", edgecolors="#163a3d", linewidths=0.9, label="Mirror-correlation center")
    ax_image.set_title("Averaged CTP486 Image")
    ax_image.set_xlabel("Column index")
    ax_image.set_ylabel("Row index")
    _style_axes(ax_image)
    ax_image.legend(loc="lower right", frameon=True, facecolor="#fffdf8", edgecolor="#666666")

    ax_h.plot(shifts_x, corr_x, color="#2f5d8a", linewidth=2.0)
    ax_h.axvline(shift_x_peak, color="#d1495b", linestyle="--", linewidth=1.2)
    ax_h.scatter([shift_x_peak], [corr_x_peak], color="#d1495b", s=36, zorder=3)
    ax_h.set_title("Horizontal Mirror Correlation")
    ax_h.set_xlabel("Horizontal shift (px)")
    ax_h.set_ylabel("Correlation")
    ax_h.text(
        0.02,
        0.94,
        f"Peak shift = {shift_x_peak:.3f} px\nPeak corr = {corr_x_peak:.4f}",
        transform=ax_h.transAxes,
        va="top",
        ha="left",
        bbox={"boxstyle": "round,pad=0.3", "facecolor": "#fffdf8", "edgecolor": "#6b6b6b", "alpha": 0.95},
    )
    _style_axes(ax_h)

    ax_v.plot(shifts_y, corr_y, color="#3b7d4c", linewidth=2.0)
    ax_v.axvline(shift_y_peak, color="#d1495b", linestyle="--", linewidth=1.2)
    ax_v.scatter([shift_y_peak], [corr_y_peak], color="#d1495b", s=36, zorder=3)
    ax_v.set_title("Vertical Mirror Correlation")
    ax_v.set_xlabel("Vertical shift (px)")
    ax_v.set_ylabel("Correlation")
    ax_v.text(
        0.02,
        0.94,
        f"Peak shift = {shift_y_peak:.3f} px\nPeak corr = {corr_y_peak:.4f}",
        transform=ax_v.transAxes,
        va="top",
        ha="left",
        bbox={"boxstyle": "round,pad=0.3", "facecolor": "#fffdf8", "edgecolor": "#6b6b6b", "alpha": 0.95},
    )
    _style_axes(ax_v)

    fig.suptitle("CTP486 Whole-Image Mirror-Correlation Study", fontsize=15, fontweight="bold")
    fig.savefig(output_path, dpi=dpi)
    plt.close(fig)


def main() -> int:
    args = parse_args()
    print("\n" + "=" * 60)
    print("Mirror Correlation Center Study")
    print("=" * 60 + "\n")

    if args.dicom_path:
        dicom_path = Path(args.dicom_path).resolve()
        print(f"Using folder from command line: {dicom_path}")
    else:
        print("Opening folder selection dialog...")
        selected_folder = select_folder()
        if not selected_folder:
            print("\nNo folder selected. Exiting.")
            return 1
        dicom_path = selected_folder.resolve()
        print(f"\nSelected folder: {dicom_path}")

    if not dicom_path.exists():
        print(f"Error: Selected path does not exist: {dicom_path}")
        return 1

    if not any(dicom_path.iterdir()):
        print(f"Error: Selected folder is empty: {dicom_path}")
        return 1

    output_dir = Path(args.output_dir).resolve() if args.output_dir else dicom_path
    output_dir.mkdir(parents=True, exist_ok=True)

    dicom_set = load_dicom_files(dicom_path)
    if len(dicom_set) < 3:
        raise RuntimeError("Need at least 3 DICOM slices to build the averaged CTP486 image.")

    image, idx_486 = average_ctp486_image(dicom_set)

    shifts_x, corr_x = mirror_correlation_curve(image, axis="horizontal", max_shift=args.max_shift)
    shifts_y, corr_y = mirror_correlation_curve(image, axis="vertical", max_shift=args.max_shift)

    shift_x_peak, corr_x_peak, _ = refine_peak_subpixel(shifts_x, corr_x)
    shift_y_peak, corr_y_peak, _ = refine_peak_subpixel(shifts_y, corr_y)

    curve_table_path = output_dir / "mirror_correlation_profiles.tsv"
    summary_path = output_dir / "mirror_correlation_summary.txt"
    plot_path = output_dir / "mirror_correlation_analysis.png"

    save_curve_table(curve_table_path, shifts_x, corr_x, shifts_y, corr_y)
    save_summary(summary_path, image, idx_486, shift_x_peak, corr_x_peak, shift_y_peak, corr_y_peak)
    save_plot(
        plot_path,
        image,
        shifts_x,
        corr_x,
        shifts_y,
        corr_y,
        shift_x_peak,
        corr_x_peak,
        shift_y_peak,
        corr_y_peak,
        args.dpi,
    )

    est_center_x, est_center_y = infer_center_from_peaks(image, shift_x_peak, shift_y_peak)
    print(f"Saved curve table: {curve_table_path}")
    print(f"Saved summary: {summary_path}")
    print(f"Saved plot: {plot_path}")
    print(f"Refined horizontal peak shift: {shift_x_peak:.6f} px")
    print(f"Refined vertical peak shift: {shift_y_peak:.6f} px")
    print(f"Estimated center from mirror-correlation: ({est_center_x:.3f}, {est_center_y:.3f})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())