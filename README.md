# almendra

> *almendra* — what coffee farmers call the green coffee bean itself.

A fast, re-trainable system for classifying **green (unroasted) coffee beans** by
defect and grade — built to eventually run on a high-throughput sorting machine.

almendra is **not just a model**. It is a replicable framework: a versioned data
pipeline, a config-driven training system with a swappable model architecture, a
hardware-agnostic export/benchmark toolchain, and a documented physical capture
protocol. The model is the focus — reliable and fast — but it must stay easy to
re-train as better data arrives.

> **Status: Phase 6 — local UI.** The full pipeline (`ingest → train → eval →
> export → bench`) runs on public data; Phase 5's Pareto sweep picked
> **MobileNetV3-Large + static INT8** as the current deploy choice (0.86 macro-F1,
> 3.6 MB, ~430 beans/s on a single CPU thread); and a local Streamlit UI now
> wraps the whole toolkit. See [`docs/research-log.md`](docs/research-log.md)
> for the full log.

## The idea

A green bean can hide damage on a face a single photo never sees. So almendra
treats one **sample** as a *set* of images of one bean — several **viewing
angles** under several **illumination spectra** (front-light, back-light
transillumination, and UV fluorescence) — and a multi-view model fuses them into
one per-bean decision.

Two design principles make this both thorough and fast:

- **Collect rich, deploy lean.** The model accepts a variable number of views and
  is trained with *view-dropout*. A slow, exhaustive rig collects the richest
  possible training data; the production machine captures fewer-but-sufficient
  views at high speed — the *same model* serves both.
- **The model is never the bottleneck.** A tiny INT8 backbone, batched across all
  views in flight, runs faster than beans can be singulated or ejected. Speed
  comes from parallel lanes and strobed capture, not from rushing each bean.

See [`docs/methodology.md`](docs/methodology.md) for the full rationale.

## Quickstart

Requires [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync --extra dev      # fast, torch-free: enough to lint, test and explore
make info                # print the canonical taxonomy and project status
make test                # run the test suite
```

To run the full pipeline:

```bash
make setup               # install everything (torch, onnx, dvc, ...)
make data                # download public datasets (needs ROBOFLOW_API_KEY)
make ingest              # crop instances + build data/processed/manifest.jsonl
make train               # train the baseline defect classifier
make eval                # evaluate on the test split
make export              # export to ONNX (+ INT8) with a parity check
make bench               # benchmark inference latency
```

## Local UI

A Streamlit app wraps the whole pipeline behind a bilingual ES/EN interface —
tray capture, training (with live charts), evaluation, prediction and settings.
A non-technical user can run almendra end-to-end without touching the CLI.

![almendra Home page in Spanish](docs/images/ui-home.png)

### Launch

```bash
uv sync --extra ui --extra train --extra export --extra capture
make ui
# equivalent: uv run almendra ui
```

The app opens at <http://localhost:8501>. Flags:

```bash
uv run almendra ui --port 8888       # use a different port
uv run almendra ui --headless        # don't auto-open a browser (SSH / CI)
```

| Extra installed | Page it unlocks |
|---|---|
| `ui` | the app itself (Streamlit + Plotly) |
| `train` | Train + Evaluate + mis-classified gallery (PyTorch) |
| `export` | Predict (ONNX Runtime) |
| `capture` | Tray Capture (OpenCV) |

Skipping an extra is fine — the page that depends on it shows a clear error
instead of crashing. Install later and reload.

### What's in the app

1. **🏠 Inicio / Home** — dataset stats, recent runs, a health panel, and an
   inline wizard that walks first-time users through Ingest → Train → Eval.
2. **📷 Bandeja / Tray Capture** — drag-and-drop tray photos, see the original
   next to the rectified+overlay preview, save per-bean crops to
   `data/raw/proprietary_tray/sessions/<id>/`.
3. **🧠 Entrenar / Train** — pick a backbone and the key knobs (advanced
   controls live behind an expander), launch training as a subprocess, and
   watch `train_loss` + `val_macro_f1` update **in real time** as each epoch
   completes.

   ![Train page](docs/images/ui-train.png)

4. **📊 Evaluar / Evaluate** — pick a checkpoint and split, run it, see
   accuracy / macro-F1 / missed-defect-rate, per-class breakdown, confusion
   matrix heatmap, and a gallery of mis-classified beans.
5. **🚀 Predecir / Predict** — upload a single-bean photo, get the predicted
   class, confidence, Top-3, and an accept/reject verdict from the canonical
   taxonomy. Uses the most recent ONNX for speed (prefers INT8).
6. **⚙️ Ajustes / Settings** — browse the canonical taxonomy, the YAML data
   sources, and the current Hydra config.

### End-to-end test in 5 minutes

```bash
# 1. install everything the UI exercises
uv sync --extra ui --extra train --extra export --extra capture

# 2. (optional) ingest the public Robusta baseline so Train/Evaluate have data
export ROBOFLOW_API_KEY=...    # see your Roboflow workspace
make data && make ingest

# 3. launch the UI
make ui
```

Then in the browser:

1. **Inicio** — confirm the health panel shows Python/PyTorch/Taxonomy green;
   the manifest icon flips to ✅ once `data/processed/manifest.jsonl` exists.
2. **Entrenar** — backbone `mobilenet_v3_small`, **3 épocas** (for a smoke
   test), **Iniciar entrenamiento**. The Plotly chart should start updating
   within a couple of seconds of the first epoch landing.
3. **Evaluar** — pick the run you just trained, leave `split = test`,
   **Ejecutar**. You get the headline metrics + confusion matrix + error
   gallery.
4. **Predecir** — from a terminal, `uv run almendra export --checkpoint
   outputs/ui-<timestamp>/best.pt`. Refresh the Predict page, pick the ONNX
   from the dropdown, upload any single-bean image.

See [`docs/ui.md`](docs/ui.md) for the deeper troubleshooting guide
(stuck subprocesses, port conflicts, missing extras).

## Repository layout

| Path | Purpose |
|------|---------|
| `data/taxonomy.yaml` | Canonical SCA-aligned label schema (single source of truth) |
| `data/sources/` | Per-dataset adapters + class mappings |
| `configs/` | Hydra configs — compose models, data and training runs |
| `src/almendra/` | The package: datasets, models, train, eval, export, bench, infer |
| `capture/` | The physical data-capture protocol and bill of materials |
| `docs/` | Methodology, research log, model cards, dataset datasheets, ADRs |
| `scripts/` | Utilities (e.g. public-dataset download) |

## Research questions

almendra is run as a rigorous investigation. Each question has a measurable
answer, tracked in [`docs/research-log.md`](docs/research-log.md):

1. Does multi-view fusion measurably lower the missed-defect rate vs a single view?
2. Does multi-spectral illumination catch defects RGB front-light reflectance misses?
3. What is the accuracy / latency / model-size Pareto frontier across backbones?
4. What accuracy is lost to INT8 quantization, per class?
5. How few deployment views can we use before per-class recall degrades?

## Roadmap

- **Phase 0** — Scaffolding ✓
- **Phase 1** — Data pipeline + single-view public baseline ✓
- **Phase 2** — Multi-view fusion model ✓
- **Phase 3** — Physical capture protocol + proprietary Arabica data *(blocked on data)*
- **Phase 4** — Multi-spectral illumination (UV, transillumination)
- **Phase 5** — Speed: backbone sweep, INT8, hardware benchmark ✓
- **Phase 6** — Local Streamlit UI for the whole toolkit ✓
- *Parallel research track* — NIR / hyperspectral internal-defect inspection

## Data & licensing

- **Code:** [Apache-2.0](LICENSE).
- **Datasets** are **never redistributed** — adapter scripts download each one
  from its original host under its own licence; provenance and licences are
  recorded in [`docs/datasheets/`](docs/datasheets/).
- The label taxonomy is currently **provisional** and aligned to — but not yet
  verified against — the official SCA Arabica Green Coffee Defect Handbook.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Contributions to data, defect taxonomy
review, and hardware/capture design are especially welcome.
