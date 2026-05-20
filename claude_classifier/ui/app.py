"""Streamlit UI for the claude_classifier pipeline.

Run with:
    uv run streamlit run claude_classifier/ui/app.py

Features:
  * List runs with status + cost
  * Trigger pass 1 (submit + collect) and pass 2 from the browser
  * Per-page reviewer: image alongside parsed JSON fields
  * Filters by article_type and brand
  * Pass 1 vs pass 2 diff (revised pages)
  * Cost summary per run
  * Raw GoogleVision OCR text viewer
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Streamlit puts the script's directory on sys.path, not the cwd. Add the repo
# root so ``claude_classifier`` is importable regardless of how it's launched.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import streamlit as st

from claude_classifier import db, io_paths, pass1 as pass1_mod, pass2 as pass2_mod
from claude_classifier.config import GOOGLEVISION_DIR, INPUTS_DIR, IMAGE_EXTENSIONS

# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Claude Classifier",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Helpers ──────────────────────────────────────────────────────────────────


@st.cache_data(show_spinner=False)
def _list_input_folders() -> list[str]:
    if not INPUTS_DIR.exists():
        return []
    return sorted(
        p.name
        for p in INPUTS_DIR.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    )


def _list_runs() -> list[dict]:
    with db.connect() as conn:
        rows = db.list_runs(conn)
    return [dict(r) for r in rows]


def _run_input_folder(run_row: dict) -> str | None:
    """Recover the input-folder name from the run_id (strip the trailing timestamp)."""
    rid = run_row["run_id"]
    # run_id format: <folder>_<YYYYMMDDTHHMMSS>
    parts = rid.rsplit("_", 1)
    return parts[0] if len(parts) == 2 else None


def _load_pass2_results(run_id: str) -> dict[str, dict]:
    """Prefer current_pass2 results; fall back to pass1 if pass 2 hasn't run."""
    link = io_paths.current_pass2_symlink(run_id)
    if link.exists():
        results_dir = link.resolve() / "results"
        if results_dir.is_dir():
            return {
                p.stem: json.loads(p.read_text())
                for p in sorted(results_dir.glob("*.json"))
            }
    return {}


def _load_pass1_results(run_id: str) -> dict[str, dict]:
    p1 = io_paths.pass1_dir(run_id)
    if not p1.is_dir():
        return {}
    return {p.stem: json.loads(p.read_text()) for p in sorted(p1.glob("*.json"))}


def _load_metadata(run_id: str) -> dict:
    meta_path = io_paths.metadata_path(run_id)
    if meta_path.exists():
        return json.loads(meta_path.read_text())
    return {}


def _input_image_path(input_folder: str, image_id: str) -> Path | None:
    folder = INPUTS_DIR / input_folder
    for ext in IMAGE_EXTENSIONS:
        candidate = folder / f"{image_id}{ext}"
        if candidate.exists():
            return candidate
    return None


def _ocr_text(input_folder: str, image_id: str) -> str | None:
    path = GOOGLEVISION_DIR / input_folder / f"{image_id}.json"
    if not path.exists():
        return None
    try:
        from claude_classifier.reconcile import extract_ocr_text

        return extract_ocr_text(path)
    except Exception as e:  # noqa: BLE001
        return f"(error reading OCR: {e})"


def _fmt_money(v: float | None) -> str:
    return f"${v:.4f}" if v else "—"


# ── Sidebar: run picker ──────────────────────────────────────────────────────


def _sidebar() -> tuple[str, dict | None]:
    st.sidebar.title("Claude Classifier")
    section = st.sidebar.radio(
        "Section",
        ["Runs", "New run", "Review"],
        label_visibility="collapsed",
    )

    selected_run = None
    runs = _list_runs()
    if section == "Review":
        if not runs:
            st.sidebar.info("No runs yet. Submit one from the **New run** tab.")
        else:
            labels = [f"{r['run_id']}  ·  {r['pass1_status']}" for r in runs]
            idx = st.sidebar.selectbox(
                "Run", range(len(runs)), format_func=lambda i: labels[i]
            )
            selected_run = runs[idx]
    return section, selected_run


# ── Section: Runs list ───────────────────────────────────────────────────────


def section_runs() -> None:
    st.header("Runs")
    runs = _list_runs()
    if not runs:
        st.info("No runs yet.")
        return

    rows = []
    for r in runs:
        rows.append(
            {
                "run_id": r["run_id"],
                "publication": r["publication_name"] or "—",
                "issue": r["issue_date"] or "—",
                "pages": r["page_count"],
                "pass1": r["pass1_status"],
                "pass1_cost": _fmt_money(r["pass1_cost_usd"]),
                "pass2_runs": r["pass2_run_count"] or 0,
                "pass2_cost": _fmt_money(r["pass2_cost_usd_total"]),
                "submitted": r["submitted_at"],
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)

    total_p1 = sum((r["pass1_cost_usd"] or 0) for r in runs)
    total_p2 = sum((r["pass2_cost_usd_total"] or 0) for r in runs)
    cols = st.columns(3)
    cols[0].metric("Total runs", len(runs))
    cols[1].metric("Total pass-1 cost", f"${total_p1:.4f}")
    cols[2].metric("Total pass-2 cost", f"${total_p2:.4f}")


# ── Section: New run (full lifecycle) ────────────────────────────────────────


def section_new_run() -> None:
    st.header("New run")
    folders = _list_input_folders()
    if not folders:
        st.warning(f"No subfolders found in {INPUTS_DIR}")
        return

    folder = st.selectbox("Input folder", folders)
    folder_path = INPUTS_DIR / folder
    img_count = sum(
        1 for p in folder_path.iterdir() if p.suffix.lower() in IMAGE_EXTENSIONS
    )
    st.caption(f"{img_count} images detected in `{folder_path}`")

    st.subheader("1 · Submit pass 1 batch")
    if st.button("Submit pass 1", type="primary"):
        with st.spinner("Submitting batch to Anthropic…"):
            try:
                run_id = pass1_mod.submit(folder_path)
                st.session_state["last_submitted_run"] = run_id
                st.success(f"Submitted. Run id: `{run_id}`")
            except Exception as e:  # noqa: BLE001
                st.error(f"Submit failed: {e}")

    st.divider()
    st.subheader("2 · Collect pass 1 (poll batch)")
    runs = _list_runs()
    in_flight = [r for r in runs if r["pass1_status"] in ("submitted", "in_progress")]
    default_run = st.session_state.get("last_submitted_run") or (
        in_flight[0]["run_id"] if in_flight else (runs[0]["run_id"] if runs else None)
    )
    collect_run = st.selectbox(
        "Run to collect",
        [r["run_id"] for r in runs] or [""],
        index=(
            (
                [r["run_id"] for r in runs].index(default_run)
                if default_run and default_run in [r["run_id"] for r in runs]
                else 0
            )
            if runs
            else 0
        ),
        key="collect_run_select",
    )
    if collect_run and st.button("Collect pass 1"):
        with st.spinner("Polling batch…"):
            try:
                pass1_mod.collect(collect_run)
                st.session_state["last_collected_run"] = collect_run
                st.success("Pass 1 collected.")
            except SystemExit as e:
                st.warning(f"Batch not ready yet (exit {e.code}). Try again shortly.")
            except Exception as e:  # noqa: BLE001
                st.error(f"Collect failed: {e}")

    st.divider()
    st.subheader("3 · Run pass 2")
    collectable = [r["run_id"] for r in runs if r["pass1_status"] == "complete"]
    if not collectable:
        st.info("No completed pass-1 runs available yet.")
    else:
        # Default to the most recently collected / submitted run if present.
        preferred = st.session_state.get("last_collected_run") or st.session_state.get(
            "last_submitted_run"
        )
        default_idx = collectable.index(preferred) if preferred in collectable else 0
        pass2_run = st.selectbox(
            "Run to revise", collectable, index=default_idx, key="pass2_run_select"
        )
        if st.button("Run pass 2"):
            with st.spinner("Running pass 2 (this can take a minute)…"):
                try:
                    pass2_run_id = pass2_mod.run(pass2_run)
                    st.success(f"Pass 2 complete: `{pass2_run_id}`")
                except Exception as e:  # noqa: BLE001
                    st.error(f"Pass 2 failed: {e}")


# ── Section: Review ──────────────────────────────────────────────────────────


def _all_brands(pages: dict[str, dict]) -> list[str]:
    brands: set[str] = set()
    for p in pages.values():
        for b in (p.get("brands") or {}).get("claude_visual") or []:
            brands.add(b)
        for c in (p.get("brands") or {}).get("canonical") or []:
            if isinstance(c, dict) and c.get("name"):
                brands.add(c["name"])
    return sorted(brands)


def _page_label(image_id: str, page: dict) -> str:
    pno = page.get("printed_page_number")
    seq = page.get("sequence_index")
    label = f"#{seq}" if seq is not None else "?"
    if pno:
        label += f" · p.{pno}"
    return f"{label}  ·  {image_id}"


def _render_page_panel(image_id: str, page: dict, input_folder: str | None) -> None:
    cols = st.columns([3, 4])

    with cols[0]:
        if input_folder:
            img_path = _input_image_path(input_folder, image_id)
            if img_path:
                st.image(str(img_path), use_container_width=True)
            else:
                st.caption(f"(image not found for {image_id})")
        else:
            st.caption("(input folder unknown — cannot resolve image)")

    with cols[1]:
        at = page.get("article_type") or {}
        final = at.get("final") or at.get("initial") or "—"
        initial = at.get("initial") or "—"
        conf = at.get("confidence")
        revised = "final" in at and "initial" in at and at["final"] != at["initial"]
        badge_cols = st.columns(3)
        badge_cols[0].metric(
            "Article type",
            final,
            delta=(f"was {initial}" if revised else None),
            delta_color="off" if revised else "normal",
        )
        badge_cols[1].metric(
            "Confidence", f"{conf:.2f}" if isinstance(conf, (int, float)) else "—"
        )
        badge_cols[2].metric("Structural", page.get("structural_role") or "—")

        with st.expander("Brands", expanded=True):
            brands = page.get("brands") or {}
            st.write("**Claude visual:**", brands.get("claude_visual") or [])
            st.write("**Dominant:**", brands.get("dominant") or "—")
            canonical = brands.get("canonical") or []
            if canonical:
                st.write("**DMR canonical:**")
                st.dataframe(canonical, use_container_width=True, hide_index=True)
            else:
                st.write("**DMR canonical:** —")

        with st.expander("Signals", expanded=False):
            st.json(page.get("signals") or {})

        with st.expander("Byline / celebrity / bridal / monography", expanded=False):
            st.write("**Byline:**", page.get("byline") or {})
            st.write("**Celebrity:**", page.get("celebrity") or {})
            st.write("**Bridal:**", page.get("bridal") or {})
            st.write("**Monography:**", page.get("monography") or {})

        if at.get("evidence"):
            with st.expander("Evidence (pass 1)", expanded=False):
                st.write(at["evidence"])
        if at.get("revision_reason"):
            with st.expander("Revision reason (pass 2)", expanded=True):
                st.write(at["revision_reason"])
        if page.get("notes"):
            with st.expander("Notes", expanded=False):
                st.write(page["notes"])

        with st.expander("Raw JSON", expanded=False):
            st.json(page)

        if input_folder:
            with st.expander("OCR text (GoogleVision)", expanded=False):
                text = _ocr_text(input_folder, image_id)
                if text:
                    st.text_area("OCR", text, height=300, label_visibility="collapsed")
                else:
                    st.caption("(no OCR JSON for this page)")


def section_review(run_row: dict | None) -> None:
    if not run_row:
        st.info("Pick a run from the sidebar.")
        return

    run_id = run_row["run_id"]
    input_folder = _run_input_folder(run_row)
    st.header(run_id)

    # Top: status + costs.
    cols = st.columns(5)
    cols[0].metric("Pages", run_row["page_count"])
    cols[1].metric("Pass 1", run_row["pass1_status"])
    cols[2].metric("Pass 1 cost", _fmt_money(run_row["pass1_cost_usd"]))
    cols[3].metric("Pass 2 runs", run_row["pass2_run_count"] or 0)
    cols[4].metric("Pass 2 cost", _fmt_money(run_row["pass2_cost_usd_total"]))

    pages = _load_pass2_results(run_id)
    source = "pass 2 (current_pass2)"
    if not pages:
        pages = _load_pass1_results(run_id)
        source = "pass 1"
    if not pages:
        st.warning("No results on disk yet for this run.")
        return
    st.caption(f"Showing **{len(pages)}** pages from **{source}**")

    tab_pages, tab_diff, tab_meta = st.tabs(["Pages", "Pass 1 → 2 diff", "Metadata"])

    with tab_pages:
        # Filters
        f1, f2, f3 = st.columns(3)
        article_types = sorted(
            {
                (p.get("article_type") or {}).get("final")
                or (p.get("article_type") or {}).get("initial")
                or "unknown"
                for p in pages.values()
            }
        )
        type_filter = f1.multiselect(
            "Article type", article_types, default=article_types
        )
        brand_choices = _all_brands(pages)
        brand_filter = f2.multiselect("Brand (visual or canonical)", brand_choices)
        only_revised = f3.checkbox("Only pages revised by pass 2", value=False)

        def _matches(page: dict) -> bool:
            at = page.get("article_type") or {}
            final = at.get("final") or at.get("initial") or "unknown"
            if type_filter and final not in type_filter:
                return False
            if brand_filter:
                bs = set((page.get("brands") or {}).get("claude_visual") or [])
                for c in (page.get("brands") or {}).get("canonical") or []:
                    if isinstance(c, dict) and c.get("name"):
                        bs.add(c["name"])
                if not bs.intersection(brand_filter):
                    return False
            if only_revised:
                if "initial" not in at or "final" not in at:
                    return False
                if at["initial"] == at["final"]:
                    return False
            return True

        filtered = {iid: p for iid, p in pages.items() if _matches(p)}
        st.caption(f"{len(filtered)} / {len(pages)} pages match filters")

        if not filtered:
            return

        # Picker
        ids = list(filtered.keys())
        labels = [_page_label(iid, filtered[iid]) for iid in ids]
        idx = st.selectbox(
            "Page",
            range(len(ids)),
            format_func=lambda i: labels[i],
            key=f"page_pick_{run_id}",
        )
        st.divider()
        _render_page_panel(ids[idx], filtered[ids[idx]], input_folder)

    with tab_diff:
        diffs = []
        for iid, p in pages.items():
            at = p.get("article_type") or {}
            init = at.get("initial")
            final = at.get("final")
            if init and final and init != final:
                diffs.append(
                    {
                        "image_id": iid,
                        "sequence_index": p.get("sequence_index"),
                        "printed_page_number": p.get("printed_page_number") or "",
                        "initial": init,
                        "final": final,
                        "confidence": at.get("confidence"),
                        "revision_reason": at.get("revision_reason") or "",
                    }
                )
        st.write(f"**{len(diffs)} pages revised** by pass 2")
        if diffs:
            st.dataframe(
                sorted(diffs, key=lambda d: d["sequence_index"] or 0),
                use_container_width=True,
                hide_index=True,
            )

    with tab_meta:
        meta = _load_metadata(run_id)
        if meta:
            st.json(meta)
        else:
            st.caption("(no run_metadata.json found)")


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    section, run_row = _sidebar()
    if section == "Runs":
        section_runs()
    elif section == "New run":
        section_new_run()
    elif section == "Review":
        section_review(run_row)


if __name__ == "__main__":
    main()
else:
    main()
