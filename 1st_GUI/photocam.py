import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np


# ----------------------------
# Utility helpers
# ----------------------------

def require_executable(name: str) -> None:
    if shutil.which(name) is None:
        raise RuntimeError(f"Required executable not found on PATH: {name}")


def run(cmd, allow_fail=False, capture_output=False, cwd=None):
    print("Running:", " ".join(map(str, cmd)))
    result = subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        capture_output=capture_output,
    )
    if result.returncode != 0 and not allow_fail:
        if capture_output:
            print(result.stdout)
            print(result.stderr)
        raise subprocess.CalledProcessError(
            result.returncode, cmd, output=result.stdout, stderr=result.stderr
        )
    return result


def safe_rmtree(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def ensure_clean_dir(path: Path) -> None:
    safe_rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


# ----------------------------
# Frame extraction + filtering
# ----------------------------

def extract_frames_ffmpeg(video_path: Path, raw_dir: Path, fps: int = 8) -> int:
    """
    Extract frames from the input video.

    First tries HDR/HLG -> SDR tone mapping using FFmpeg zscale+tonemap.
    If that fails, falls back to a simpler extraction path.
    """
    raw_dir.mkdir(parents=True, exist_ok=True)
    pattern = str(raw_dir / "frame_%06d.jpg")

    # Attempt 1: iPhone HDR/HLG-friendly extraction.
    # If ffmpeg build or input does not like this, we fall back.
    hdr_filter = (
        f"fps={fps},"
        "zscale=transfer=linear,"
        "tonemap=hable,"
        "zscale=primaries=bt709:transfer=bt709:matrix=bt709,"
        "format=yuv420p"
    )

    cmd_hdr = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",
        "-i", str(video_path),
        "-map", "0:v:0",
        "-vf", hdr_filter,
        "-q:v", "2",
        pattern,
        "-y",
    ]

    result = run(cmd_hdr, allow_fail=True, capture_output=True)
    extracted = list(raw_dir.glob("*.jpg"))
    if result.returncode == 0 and extracted:
        return len(extracted)

    # Clean partial files if the HDR path failed.
    for f in raw_dir.glob("*.jpg"):
        f.unlink()

    # Attempt 2: simple robust fallback.
    cmd_basic = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",
        "-i", str(video_path),
        "-map", "0:v:0",
        "-vf", f"fps={fps}",
        "-q:v", "2",
        pattern,
        "-y",
    ]
    run(cmd_basic)

    extracted = list(raw_dir.glob("*.jpg"))
    if not extracted:
        raise RuntimeError("FFmpeg extracted zero frames.")
    return len(extracted)


def laplacian_variance(gray: np.ndarray) -> float:
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def thumbnail_signature(gray: np.ndarray, size: int = 64) -> np.ndarray:
    thumb = cv2.resize(gray, (size, size), interpolation=cv2.INTER_AREA)
    return thumb.astype(np.float32)


def select_good_frames(
    raw_dir: Path,
    filtered_dir: Path,
    blur_threshold: float = 80.0,
    duplicate_mad_threshold: float = 2.5,
    min_keep: int = 20,
) -> dict:
    """
    Removes very blurry frames and near-duplicates.
    Keeps more frames if the input is short so we don't over-prune.
    """
    ensure_clean_dir(filtered_dir)

    frame_paths = sorted(raw_dir.glob("*.jpg"))
    if not frame_paths:
        raise RuntimeError("No raw frames found to filter.")

    stats = []
    for path in frame_paths:
        img = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if img is None:
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = laplacian_variance(gray)
        sig = thumbnail_signature(gray)
        stats.append((path, blur, sig))

    if not stats:
        raise RuntimeError("OpenCV could not read any extracted frames.")

    # If too many frames are under threshold, relax it automatically.
    blur_values = np.array([s[1] for s in stats], dtype=np.float32)
    auto_blur_threshold = max(
        min(blur_threshold, float(np.percentile(blur_values, 35))),
        20.0,
    )

    kept = []
    prev_sig = None
    for path, blur, sig in stats:
        if blur < auto_blur_threshold:
            continue

        if prev_sig is not None:
            mad = float(np.mean(np.abs(sig - prev_sig)))
            if mad < duplicate_mad_threshold:
                continue

        kept.append((path, blur))
        prev_sig = sig

    # Safety fallback: if we kept too little, keep top sharp frames.
    if len(kept) < min_keep:
        ranked = sorted(stats, key=lambda x: x[1], reverse=True)
        chosen = ranked[: min(min_keep, len(ranked))]
        chosen_paths = {p for p, _, _ in chosen}
        kept = [(p, b) for p, b, _ in stats if p in chosen_paths]
        kept.sort(key=lambda x: x[0].name)

    # Copy and renumber sequentially for COLMAP.
    for i, (src, _) in enumerate(kept, start=1):
        dst = filtered_dir / f"image_{i:06d}.jpg"
        shutil.copy2(src, dst)

    return {
        "raw_frames": len(frame_paths),
        "kept_frames": len(kept),
        "blur_threshold_used": auto_blur_threshold,
    }


# ----------------------------
# COLMAP model inspection
# ----------------------------

def convert_model_to_txt(model_dir: Path, txt_dir: Path) -> None:
    ensure_clean_dir(txt_dir)
    run([
        "colmap", "model_converter",
        "--input_path", str(model_dir),
        "--output_path", str(txt_dir),
        "--output_type", "TXT",
    ])


def count_sparse_model_stats(model_dir: Path) -> tuple[int, int]:
    """
    Returns (registered_images, points3D_count) for a COLMAP model.
    Uses model_converter -> TXT so we don't need pycolmap.
    """
    with tempfile.TemporaryDirectory() as tmp:
        txt_dir = Path(tmp) / "txt_model"
        convert_model_to_txt(model_dir, txt_dir)

        images_txt = txt_dir / "images.txt"
        points_txt = txt_dir / "points3D.txt"

        registered_images = 0
        points3d = 0

        # images.txt alternates:
        # line 1 = image metadata
        # line 2 = 2D points
        # comments start with #
        if images_txt.exists():
            non_comment = [
                line for line in images_txt.read_text(errors="ignore").splitlines()
                if line.strip() and not line.startswith("#")
            ]
            registered_images = len(non_comment) // 2

        if points_txt.exists():
            for line in points_txt.read_text(errors="ignore").splitlines():
                if line.strip() and not line.startswith("#"):
                    points3d += 1

        return registered_images, points3d


def choose_best_sparse_model(sparse_root: Path) -> tuple[Path, dict]:
    """
    COLMAP may create sparse/0, sparse/1, ...
    We pick the best one by:
      1) most registered images
      2) then most 3D points
    """
    candidates = []
    for child in sorted(sparse_root.iterdir()):
        if not child.is_dir():
            continue
        if (child / "images.bin").exists() and (child / "points3D.bin").exists():
            imgs, pts = count_sparse_model_stats(child)
            candidates.append((child, imgs, pts))

    if not candidates:
        raise RuntimeError("COLMAP produced no valid sparse models.")

    candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
    best_dir, best_imgs, best_pts = candidates[0]
    return best_dir, {
        "all_models": [
            {"path": str(p), "registered_images": imgs, "points3D": pts}
            for p, imgs, pts in candidates
        ],
        "best_registered_images": best_imgs,
        "best_points3D": best_pts,
    }


def export_sparse_ply(model_dir: Path, output_ply: Path) -> None:
    run([
        "colmap", "model_converter",
        "--input_path", str(model_dir),
        "--output_path", str(output_ply),
        "--output_type", "PLY",
    ])


# ----------------------------
# Reconstruction pipeline
# ----------------------------

def choose_matcher(num_images: int) -> str:
    """
    For modest frame counts, exhaustive matching usually gives stronger results.
    For larger frame counts, sequential matching is more efficient.
    """
    return "exhaustive" if num_images <= 180 else "sequential"


def run_colmap_sparse(
    images_dir: Path,
    sparse_dir: Path,
    db_path: Path,
    camera_model: str = "SIMPLE_RADIAL",
) -> tuple[Path, dict]:
    if db_path.exists():
        db_path.unlink()
    ensure_clean_dir(sparse_dir)

    image_files = sorted(images_dir.glob("*.jpg"))
    if len(image_files) < 8:
        raise RuntimeError("Too few filtered images for a meaningful reconstruction.")

    matcher = choose_matcher(len(image_files))

    run([
        "colmap", "feature_extractor",
        "--database_path", str(db_path),
        "--image_path", str(images_dir),
        "--ImageReader.camera_model", camera_model,
        "--ImageReader.single_camera", "1",
    ])

    if matcher == "exhaustive":
        run([
            "colmap", "exhaustive_matcher",
            "--database_path", str(db_path),
        ])
    else:
        run([
            "colmap", "sequential_matcher",
            "--database_path", str(db_path),
        ])

    run([
        "colmap", "mapper",
        "--database_path", str(db_path),
        "--image_path", str(images_dir),
        "--output_path", str(sparse_dir),
    ])

    best_model_dir, stats = choose_best_sparse_model(sparse_dir)
    stats["matcher_used"] = matcher
    stats["filtered_image_count"] = len(image_files)
    return best_model_dir, stats


def try_dense_reconstruction(
    images_dir: Path,
    model_dir: Path,
    dense_dir: Path,
) -> dict:
    ensure_clean_dir(dense_dir)

    out = {
        "dense_attempted": True,
        "undistortion_ok": False,
        "patch_match_ok": False,
        "fusion_ok": False,
        "poisson_ok": False,
        "delaunay_ok": False,
        "fused_ply": None,
        "poisson_mesh": None,
        "delaunay_mesh": None,
    }

    und = run([
        "colmap", "image_undistorter",
        "--image_path", str(images_dir),
        "--input_path", str(model_dir),
        "--output_path", str(dense_dir),
        "--output_type", "COLMAP",
        "--max_image_size", "2000",
    ], allow_fail=True)

    if und.returncode != 0:
        return out

    out["undistortion_ok"] = True

    pm = run([
        "colmap", "patch_match_stereo",
        "--workspace_path", str(dense_dir),
        "--workspace_format", "COLMAP",
        "--PatchMatchStereo.geom_consistency", "true",
    ], allow_fail=True)

    if pm.returncode != 0:
        return out

    out["patch_match_ok"] = True

    fused_ply = dense_dir / "fused.ply"
    fus = run([
        "colmap", "stereo_fusion",
        "--workspace_path", str(dense_dir),
        "--workspace_format", "COLMAP",
        "--input_type", "geometric",
        "--output_path", str(fused_ply),
    ], allow_fail=True)

    if fus.returncode != 0:
        return out

    out["fusion_ok"] = True
    out["fused_ply"] = str(fused_ply)

    poisson_mesh = dense_dir / "meshed-poisson.ply"
    poi = run([
        "colmap", "poisson_mesher",
        "--input_path", str(fused_ply),
        "--output_path", str(poisson_mesh),
    ], allow_fail=True)
    if poi.returncode == 0:
        out["poisson_ok"] = True
        out["poisson_mesh"] = str(poisson_mesh)

    delaunay_mesh = dense_dir / "meshed-delaunay.ply"
    de = run([
        "colmap", "delaunay_mesher",
        "--input_path", str(dense_dir),
        "--output_path", str(delaunay_mesh),
    ], allow_fail=True)
    if de.returncode == 0:
        out["delaunay_ok"] = True
        out["delaunay_mesh"] = str(delaunay_mesh)

    return out


def build_report(workspace: Path, report: dict) -> None:
    report_path = workspace / "report.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\nSaved report: {report_path}")


def video_to_3d_model(
    video_path: str,
    workspace: str = "reconstruction_workspace",
    fps: int = 8,
    camera_model: str = "SIMPLE_RADIAL",
):
    require_executable("ffmpeg")
    require_executable("colmap")

    video_path = Path(video_path).expanduser().resolve()
    workspace = Path(workspace).expanduser().resolve()

    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    raw_frames_dir = workspace / "raw_frames"
    images_dir = workspace / "images"
    sparse_dir = workspace / "sparse"
    dense_dir = workspace / "dense"
    db_path = workspace / "database.db"

    workspace.mkdir(parents=True, exist_ok=True)
    ensure_clean_dir(raw_frames_dir)
    ensure_clean_dir(images_dir)
    ensure_clean_dir(sparse_dir)
    ensure_clean_dir(dense_dir)
    if db_path.exists():
        db_path.unlink()

    report = {
        "video_path": str(video_path),
        "workspace": str(workspace),
        "fps": fps,
        "camera_model": camera_model,
    }

    print("\n=== STEP 1: Extract frames ===")
    extracted_count = extract_frames_ffmpeg(video_path, raw_frames_dir, fps=fps)
    report["extracted_frames"] = extracted_count
    print(f"Extracted {extracted_count} raw frames.")

    print("\n=== STEP 2: Remove blurry / duplicate frames ===")
    frame_stats = select_good_frames(
        raw_frames_dir=raw_frames_dir,
        filtered_dir=images_dir,
        blur_threshold=80.0,
        duplicate_mad_threshold=2.5,
        min_keep=20,
    )
    report["frame_filtering"] = frame_stats
    print(
        f"Kept {frame_stats['kept_frames']} / {frame_stats['raw_frames']} frames "
        f"(blur threshold used: {frame_stats['blur_threshold_used']:.2f})"
    )

    print("\n=== STEP 3: Sparse reconstruction ===")
    best_model_dir, sparse_stats = run_colmap_sparse(
        images_dir=images_dir,
        sparse_dir=sparse_dir,
        db_path=db_path,
        camera_model=camera_model,
    )
    report["sparse_stats"] = sparse_stats
    report["best_sparse_model"] = str(best_model_dir)

    sparse_ply = sparse_dir / "best_sparse_points.ply"
    export_sparse_ply(best_model_dir, sparse_ply)
    report["sparse_ply"] = str(sparse_ply)

    print("\nBest sparse model:", best_model_dir)
    print("Registered images:", sparse_stats["best_registered_images"])
    print("3D points:", sparse_stats["best_points3D"])
    print("Sparse point cloud:", sparse_ply)

    print("\n=== STEP 4: Dense reconstruction (attempt if available) ===")
    dense_report = try_dense_reconstruction(
        images_dir=images_dir,
        model_dir=best_model_dir,
        dense_dir=dense_dir,
    )
    report["dense"] = dense_report

    build_report(workspace, report)

    print("\n=== FINAL SUMMARY ===")
    print(f"Sparse PLY: {sparse_ply}")

    if dense_report["fusion_ok"]:
        print(f"Dense PLY: {dense_report['fused_ply']}")
        if dense_report["poisson_ok"]:
            print(f"Poisson mesh: {dense_report['poisson_mesh']}")
        if dense_report["delaunay_ok"]:
            print(f"Delaunay mesh: {dense_report['delaunay_mesh']}")
    else:
        print("Dense mesh was not produced.")
        print("On non-CUDA Macs, this is expected with COLMAP.")

    if sparse_stats["best_registered_images"] < 12:
        print("\nWARNING:")
        print("Very weak reconstruction. Reshoot the video.")
        print("Move slower, keep constant distance, improve lighting, avoid blur,")
        print("and make the object fill more of the frame.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python photocam.py <video_path>")
        sys.exit(1)

    video_to_3d_model(
        video_path=sys.argv[1],
        workspace="reconstruction_workspace",
        fps=8,
        camera_model="SIMPLE_RADIAL",
    )