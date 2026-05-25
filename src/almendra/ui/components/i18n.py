"""Bilingual ES/EN string table.

Text lives in a single dict so adding a third language later is a translation
job — not a rewrite. Pages call ``t("home.title")`` instead of inlining strings.
"""

from __future__ import annotations

from typing import Literal

Lang = Literal["es", "en"]

DEFAULT_LANG: Lang = "es"

_STRINGS: dict[str, dict[Lang, str]] = {
    # --- generic ---
    "app.title": {"es": "almendra", "en": "almendra"},
    "app.tagline": {
        "es": "Clasificador de café verde — herramienta local",
        "en": "Green coffee classifier — local toolkit",
    },
    "sidebar.language": {"es": "Idioma", "en": "Language"},
    "sidebar.nav": {"es": "Navegación", "en": "Navigation"},
    "common.advanced": {"es": "Avanzado", "en": "Advanced"},
    "common.start": {"es": "Empezar", "en": "Start"},
    "common.stop": {"es": "Detener", "en": "Stop"},
    "common.save": {"es": "Guardar", "en": "Save"},
    "common.run": {"es": "Ejecutar", "en": "Run"},
    "common.required": {"es": "obligatorio", "en": "required"},
    "common.optional": {"es": "opcional", "en": "optional"},
    "common.not_found": {"es": "no disponible", "en": "not available"},
    "common.no_runs": {
        "es": "Aún no hay corridas — entrena un modelo para empezar.",
        "en": "No runs yet — train a model to get started.",
    },
    # --- nav labels ---
    "nav.home": {"es": "🏠 Inicio", "en": "🏠 Home"},
    "nav.tray": {"es": "📷 Bandeja", "en": "📷 Tray Capture"},
    "nav.train": {"es": "🧠 Entrenar", "en": "🧠 Train"},
    "nav.evaluate": {"es": "📊 Evaluar", "en": "📊 Evaluate"},
    "nav.quantize": {"es": "⚡ Cuantizar", "en": "⚡ Quantize"},
    "nav.predict": {"es": "🚀 Predecir", "en": "🚀 Predict"},
    "nav.settings": {"es": "⚙️ Ajustes", "en": "⚙️ Settings"},
    # --- home ---
    "home.title": {"es": "Inicio", "en": "Home"},
    "home.dataset_stats": {
        "es": "Estadísticas del dataset",
        "en": "Dataset statistics",
    },
    "home.no_manifest": {
        "es": "Aún no hay manifest. Ve a **Bandeja** para preparar fotos, o "
        "ejecuta `almendra ingest` si ya descargaste datasets públicos.",
        "en": "No manifest yet. Open **Tray Capture** to prepare photos, or run "
        "`almendra ingest` if you've downloaded public datasets.",
    },
    "home.recent_runs": {"es": "Corridas recientes", "en": "Recent runs"},
    "home.wizard_header": {
        "es": "🪄 ¿Primera vez? Asistente",
        "en": "🪄 First time? Wizard",
    },
    "home.wizard_intro": {
        "es": "Te guío en 3 pasos con valores por defecto sensatos. Puedes "
        "ajustar todo después en las páginas de Entrenar y Evaluar.",
        "en": "I'll walk you through 3 steps with sensible defaults. You can "
        "tweak everything later on the Train and Evaluate pages.",
    },
    "home.wizard_step1": {
        "es": "1️⃣ Cargar fotos de bandeja",
        "en": "1️⃣ Upload tray photos",
    },
    "home.wizard_step2": {
        "es": "2️⃣ Entrenar con valores por defecto",
        "en": "2️⃣ Train with defaults",
    },
    "home.wizard_step3": {
        "es": "3️⃣ Evaluar el resultado",
        "en": "3️⃣ Evaluate the result",
    },
    "home.health": {"es": "Estado", "en": "Health"},
    "home.health_python": {"es": "Python", "en": "Python"},
    "home.health_torch": {"es": "PyTorch", "en": "PyTorch"},
    "home.health_taxonomy": {"es": "Taxonomía", "en": "Taxonomy"},
    "home.health_manifest": {"es": "Manifest", "en": "Manifest"},
    # --- tray ---
    "tray.title": {"es": "Captura de bandeja", "en": "Tray Capture"},
    "tray.help_banner": {
        "es": "Toma fotos cenitales de una bandeja con marcadores ArUco en las "
        "4 esquinas. Una foto por cara; volteas la bandeja, otra foto. "
        "Ver `capture/protocol.md` para detalle.",
        "en": "Take top-down photos of a tray with ArUco markers in the 4 "
        "corners. One photo per side; flip the tray, take the other. "
        "See `capture/protocol.md` for detail.",
    },
    "tray.side_a": {"es": "Cara A (obligatoria)", "en": "Side A (required)"},
    "tray.side_b": {
        "es": "Cara B (opcional — habilita emparejamiento)",
        "en": "Side B (optional — enables pairing)",
    },
    "tray.rows": {"es": "Filas", "en": "Rows"},
    "tray.cols": {"es": "Columnas", "en": "Columns"},
    "tray.flip": {"es": "Modo de volteo", "en": "Flip mode"},
    "tray.marker_dict": {"es": "Diccionario ArUco", "en": "ArUco dictionary"},
    "tray.margin_frac": {
        "es": "Margen desde el cuadro de marcadores (0–0.5)",
        "en": "Margin inset from marker quad (0–0.5)",
    },
    "tray.well_frac": {
        "es": "Ancho de ventana de pozo (0.5–1.0)",
        "en": "Well window width (0.5–1.0)",
    },
    "tray.process": {"es": "Procesar fotos", "en": "Process photos"},
    "tray.original": {"es": "Original", "en": "Original"},
    "tray.rectified": {"es": "Rectificada + overlay", "en": "Rectified + overlay"},
    "tray.beans_found": {
        "es": "{n} granos encontrados en {total} pozos",
        "en": "{n} beans found across {total} wells",
    },
    "tray.paired_summary": {
        "es": "{two} granos con dos vistas, {one} con una vista",
        "en": "{two} two-view beans, {one} single-view",
    },
    "tray.save_crops": {"es": "Guardar recortes", "en": "Save crops"},
    "tray.session_id": {"es": "ID de sesión", "en": "Session ID"},
    "tray.saved_to": {"es": "Guardado en", "en": "Saved to"},
    "tray.error_markers": {
        "es": "No se detectaron los 4 marcadores. Tip: asegúrate de que las 4 "
        "esquinas estén en cuadro, sin reflejos.",
        "en": "Markers not detected. Tip: make sure all 4 corner markers are "
        "in frame and not glaring.",
    },
    # --- train ---
    "train.title": {"es": "Entrenar", "en": "Train"},
    "train.backbone": {"es": "Arquitectura", "en": "Backbone"},
    "train.epochs": {"es": "Épocas", "en": "Epochs"},
    "train.lr": {"es": "Learning rate", "en": "Learning rate"},
    "train.image_size": {"es": "Tamaño de imagen", "en": "Image size"},
    "train.batch_size": {"es": "Batch size", "en": "Batch size"},
    "train.pseudo_views": {
        "es": "Usar pseudo-vistas (rotaciones del mismo grano)",
        "en": "Use pseudo-views (rotations of the same bean)",
    },
    "train.view_dropout": {"es": "View dropout", "en": "View dropout"},
    "train.fusion": {"es": "Cabeza de fusión", "en": "Fusion head"},
    "train.augmentation": {"es": "Aumentación de datos", "en": "Data augmentation"},
    "train.start_btn": {"es": "Iniciar entrenamiento", "en": "Start training"},
    "train.stop_btn": {"es": "Detener", "en": "Stop"},
    "train.running": {"es": "Entrenando…", "en": "Training…"},
    "train.done": {"es": "Listo", "en": "Done"},
    "train.best_so_far": {"es": "Mejor macro-F1", "en": "Best macro-F1"},
    "train.chart_title": {"es": "Métricas por época", "en": "Per-epoch metrics"},
    # --- evaluate ---
    "evaluate.title": {"es": "Evaluar", "en": "Evaluate"},
    "evaluate.checkpoint": {"es": "Checkpoint", "en": "Checkpoint"},
    "evaluate.split": {"es": "Split", "en": "Split"},
    "evaluate.no_checkpoints": {
        "es": "No hay checkpoints. Entrena un modelo primero.",
        "en": "No checkpoints found. Train a model first.",
    },
    "evaluate.headline_acc": {"es": "Accuracy", "en": "Accuracy"},
    "evaluate.headline_f1": {"es": "Macro-F1", "en": "Macro-F1"},
    "evaluate.headline_mdr": {
        "es": "Defectos no detectados",
        "en": "Missed-defect rate",
    },
    "evaluate.per_class": {"es": "Por clase", "en": "Per class"},
    "evaluate.confusion": {"es": "Matriz de confusión", "en": "Confusion matrix"},
    "evaluate.gallery": {
        "es": "Galería de errores",
        "en": "Mis-classified gallery",
    },
    "evaluate.gallery_caption": {
        "es": "{pred} ⟵ {true}",
        "en": "{pred} ⟵ {true}",
    },
    # --- quantize ---
    "quantize.title": {"es": "Cuantizar / Exportar", "en": "Quantize / Export"},
    "quantize.help": {
        "es": "Exporta un checkpoint a ONNX y, opcionalmente, cuantiza a INT8 "
        "para desplegar más liviano y rápido.",
        "en": "Export a checkpoint to ONNX and optionally quantize to INT8 for a "
        "lighter, faster deployment artifact.",
    },
    "quantize.no_checkpoints": {
        "es": "No hay checkpoints. Entrena un modelo primero.",
        "en": "No checkpoints found. Train a model first.",
    },
    "quantize.checkpoint": {"es": "Checkpoint", "en": "Checkpoint"},
    "quantize.mode": {"es": "Modo de cuantización", "en": "Quantization mode"},
    "quantize.run_btn": {"es": "Exportar / Cuantizar", "en": "Export / Quantize"},
    "quantize.parity_ok": {
        "es": "✅ Exportado — la paridad numérica con PyTorch pasó.",
        "en": "✅ Exported — numerical parity with PyTorch passed.",
    },
    "quantize.float_model": {"es": "ONNX float", "en": "Float ONNX"},
    "quantize.int8_model": {"es": "ONNX INT8", "en": "INT8 ONNX"},
    "quantize.reduction": {"es": "Reducción de tamaño", "en": "Size reduction"},
    "quantize.int8_skipped": {
        "es": "INT8 omitido (ver logs).",
        "en": "INT8 skipped (see logs).",
    },
    # --- predict ---
    "predict.title": {"es": "Predecir", "en": "Predict"},
    "predict.upload": {
        "es": "Sube una foto de un grano",
        "en": "Upload a single-bean photo",
    },
    "predict.predicted": {"es": "Clase predicha", "en": "Predicted class"},
    "predict.confidence": {"es": "Confianza", "en": "Confidence"},
    "predict.top3": {"es": "Top-3", "en": "Top-3"},
    "predict.no_model": {
        "es": "No hay ONNX. Entrena y exporta un modelo primero.",
        "en": "No ONNX model. Train and export one first.",
    },
    "predict.verdict_accept": {"es": "✅ Acepta", "en": "✅ Accept"},
    "predict.verdict_reject": {"es": "❌ Rechaza", "en": "❌ Reject"},
    "predict.compare": {
        "es": "Comparar float vs INT8",
        "en": "Compare float vs INT8",
    },
    "predict.compare_unavailable": {
        "es": "La corrida seleccionada no tiene ambos modelos (float e INT8). "
        "Exporta con INT8 en la página Cuantizar.",
        "en": "The selected run does not have both float and INT8 models. Export "
        "with INT8 on the Quantize page.",
    },
    "predict.model_float": {"es": "Float", "en": "Float"},
    "predict.model_int8": {"es": "INT8", "en": "INT8"},
    "predict.agreement": {"es": "Coinciden", "en": "Agreement"},
    "predict.agreement_yes": {"es": "✅ Igual top-1", "en": "✅ Same top-1"},
    "predict.agreement_no": {"es": "⚠️ Difieren", "en": "⚠️ Differ"},
    "predict.latency": {"es": "Latencia", "en": "Latency"},
    # --- settings ---
    "settings.title": {"es": "Ajustes", "en": "Settings"},
    "settings.taxonomy": {"es": "Taxonomía canónica", "en": "Canonical taxonomy"},
    "settings.sources": {"es": "Fuentes de datos", "en": "Data sources"},
    "settings.config": {"es": "Configuración actual", "en": "Current config"},
    "settings.paths": {"es": "Rutas del proyecto", "en": "Project paths"},
}


def t(key: str, lang: Lang | None = None, **fmt: object) -> str:
    """Look up a string by key in the active language; format with ``str.format``."""
    if lang is None:
        lang = DEFAULT_LANG
    entry = _STRINGS.get(key)
    if entry is None:
        return key
    text = entry.get(lang) or entry.get("en") or next(iter(entry.values()))
    return text.format(**fmt) if fmt else text


def available_languages() -> list[Lang]:
    return ["es", "en"]
