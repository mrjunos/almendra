# almendra

> *almendra* — what coffee farmers call the green coffee bean itself.

A fast, re-trainable system for classifying **green (unroasted) coffee beans** by
defect and grade — built to eventually run on a high-throughput sorting machine.

almendra is **not just a model**. It is a replicable framework: a versioned data
pipeline, a config-driven training system with a swappable model architecture, a
hardware-agnostic export/benchmark toolchain, and a documented physical capture
protocol. The model is the focus — reliable and fast — but it must stay easy to
re-train as better data arrives.

> **Status: Phase 0 — scaffolding.** The pipeline is built phase by phase; see
> [`docs/research-log.md`](docs/research-log.md) for live progress and
> [the project plan](#roadmap) below.

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

To work on the full pipeline (training, export, datasets):

```bash
make setup               # install everything (torch, onnx, dvc, ...)
```

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

- **Phase 0** — Scaffolding *(current)*
- **Phase 1** — Data pipeline + single-view public baseline
- **Phase 2** — Multi-view fusion model
- **Phase 3** — Physical capture protocol + proprietary Arabica data
- **Phase 4** — Multi-spectral illumination (UV, transillumination)
- **Phase 5** — Speed: backbone sweep, INT8, hardware benchmark
- **Phase 6** — Deployment reference + sorting-machine spec
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
