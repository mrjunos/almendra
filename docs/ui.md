# Local UI (Phase 6)

The `almendra ui` command launches a local Streamlit app that wraps the whole
toolkit — tray capture, training, evaluation, prediction and settings — so a
non-technical user can run the pipeline end-to-end without touching the CLI.

The UI is **bilingual ES/EN** with a sidebar toggle (Spanish default).

## 1 — Install

```bash
# Minimum extras for a full end-to-end run:
uv sync --extra ui --extra train --extra export --extra capture
```

| Extra | Why you need it |
|---|---|
| `ui` | Streamlit + Plotly (the app itself) |
| `train` | PyTorch + torchvision (Train, Evaluate, mis-classified gallery) |
| `export` | ONNX Runtime (Predict page) |
| `capture` | OpenCV (Tray Capture page) |

If you skip an extra, the page that depends on it shows a clear error instead
of crashing. You can come back and install it later.

## 2 — Launch

```bash
make ui
# equivalent: uv run almendra ui
```

This exec's `streamlit run` against `src/almendra/ui/app.py`. By default the
app opens at <http://localhost:8501> and your browser auto-opens.

Flags:

```bash
uv run almendra ui --port 8888          # use a different port
uv run almendra ui --headless           # don't auto-open a browser (SSH)
```

The first launch may take a few seconds — Streamlit warms up its caches.

## 3 — End-to-end test flow

The pages are designed to be exercised in order. The **inline wizard on Home**
gives you a fast-path button for each step.

### 3a — Have public data already?

If you've already run `make data && make ingest` (Roboflow Robusta dataset),
the manifest at `data/processed/manifest.jsonl` will show up on Home and you
can skip straight to **Train**.

### 3b — Cold start (proprietary tray photos)

1. **🏠 Home** — confirm the health panel says Python/PyTorch/Taxonomy are all
   green. Manifest will show ❌ if you haven't ingested anything yet — fine.
2. **📷 Tray Capture** — drag in *Side A* (required) and *Side B* (optional)
   tray photos. Set:
   - **Rows / Cols** — wells in your tray.
   - **Flip** — `mirror_cols` if you flipped the tray horizontally, `mirror_rows`
     if vertically. `identity` if no flip.
   - Leave **Margin frac** and **Well frac** at defaults to start.
   Hit **Procesar / Process photos**. You should see the original photo next
   to a rectified+overlay view (green squares = occupied wells, red = empty).
   If markers aren't detected the page tells you so — check the corners are
   sharp and in-frame.
   Enter a session ID (defaults to a timestamp) and hit **Save crops**. Crops
   land in `data/raw/proprietary_tray/sessions/<id>/`.
3. *(out of UI for now)* — convert the saved session into a manifest entry.
   The proprietary tray ingester is a Phase 3 task; until then, public-data
   `almendra ingest` is the path that gives the Train page something to chew.
4. **🧠 Train** — pick a backbone (start with `mobilenet_v3_small` — fastest),
   set **Épocas / Epochs** to 3 for a smoke test, press **Iniciar /  Start**.
   The progress bar fills and the Plotly chart updates in real time as each
   epoch completes. The **Best macro-F1** metric tracks the best checkpoint
   saved. Press **Detener / Stop** if you want to kill the run early.
5. **📊 Evaluate** — pick the run you just trained from the dropdown, leave
   `split = test`, press **Ejecutar / Run**. You get headline accuracy /
   macro-F1 / missed-defect-rate cards, a per-class table, a confusion-matrix
   heatmap, and a gallery of mis-classified beans.
6. **🚀 Predict** — works once a run has been **exported**. From a terminal:
   ```bash
   uv run almendra export --checkpoint outputs/ui-<timestamp>/best.pt
   ```
   Then refresh the Predict page, pick the ONNX file from the dropdown, upload
   a single bean photo, and check the predicted class + Top-3 + accept/reject
   verdict.
7. **⚙️ Settings** — read-only view of the canonical taxonomy, data sources
   and current Hydra config. Useful for sanity-checking the project paths.

### 3c — Sanity-check checklist

Use this to make sure the UI is *actually* doing what it should:

- [ ] Language toggle in the sidebar instantly swaps every visible string.
- [ ] Home health panel shows ✅ for Taxonomy and the manifest icon flips
      between ✅/❌ depending on whether `data/processed/manifest.jsonl` exists.
- [ ] On Train, the live chart **starts appearing within ~2 s of the first
      epoch finishing** — confirms the JSONL tail is working.
- [ ] Stopping training mid-run kills the subprocess (check `ps` or `pgrep -f
      almendra.cli`).
- [ ] On Evaluate, mis-classified gallery shows real bean thumbnails (not just
      captions) when the manifest has accessible image paths.
- [ ] On Predict, the page lists every ONNX under `outputs/*/model*.onnx` and
      defaults to the most recently modified INT8 if present.
- [ ] On Settings, every YAML under `data/sources/` is browsable.

## Troubleshooting

- **"OpenCV is not installed"** on the Tray Capture page → `uv sync --extra
  capture`, then click the page again.
- **"onnxruntime is not installed"** on Predict → `uv sync --extra export`.
- **The Train chart never updates** → check `outputs/ui-<timestamp>/live_metrics.jsonl`
  exists and grows; if the file isn't being written, the subprocess didn't
  inherit the `ALMENDRA_LIVE_METRICS` env var (file a bug).
- **Port already in use** → `uv run almendra ui --port 8888`.
- **Stuck training subprocess after closing the tab** → `pkill -f
  "almendra.cli train"`. The UI's Stop button uses SIGTERM on the process
  group, but if you close the browser before pressing Stop the subprocess
  keeps running. This is intentional — long runs should survive a tab close.

## What's *not* in v1

These ship in **Phase 6.1**, not this PR:

- A dedicated **Labelling** page with keyboard hotkeys and inter-annotator
  agreement reporting.
- An **Export & Bench** page (currently you drop to the CLI for both).
- A **model-package zip exporter** (ONNX + INT8 + model card + manifest
  snapshot).
- A **demo mode** using the public Roboflow data baseline.
