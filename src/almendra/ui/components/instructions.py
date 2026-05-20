"""Plain-language help/instruction blobs.

Kept separate from i18n strings because they are paragraph-length and meant to
be rendered as Markdown blocks, not short labels.
"""

from __future__ import annotations

from almendra.ui.components.i18n import Lang

TRAY_HELP: dict[Lang, str] = {
    "es": """
**Cómo tomar buenas fotos de bandeja**

1. Coloca la bandeja sobre una superficie plana, con luz pareja (sin sombras
   duras).
2. Pon **un grano por pozo**. Es OK dejar pozos vacíos — el sistema los detecta.
3. Asegúrate de que los **4 marcadores ArUco** de las esquinas estén en cuadro
   y nítidos. La cámara debe estar lo más cenital posible.
4. Toma la foto de **Cara A**. Anota la orientación de la bandeja.
5. Voltea la bandeja **horizontal o verticalmente** (no la rotes) y toma la foto
   de **Cara B**. El modo de volteo debe coincidir con el campo *Flip*.
6. Si un grano se mueve al voltear, ignóralo — el emparejamiento se basa en
   coincidencia de pozo, no de grano.

Más detalle en `capture/protocol.md` del repo.
""",
    "en": """
**How to take good tray photos**

1. Place the tray on a flat surface with even light (no harsh shadows).
2. Put **one bean per well**. Empty wells are fine — the system detects them.
3. Make sure all **4 corner ArUco markers** are in frame and sharp. Shoot as
   top-down as possible.
4. Take the **Side A** photo. Note the tray's orientation.
5. Flip the tray **horizontally or vertically** (don't rotate it) and take the
   **Side B** photo. The flip mode must match the *Flip* field.
6. If a bean shifts during the flip, ignore it — pairing is by well address,
   not by bean appearance.

More detail in `capture/protocol.md`.
""",
}

TRAIN_HELP: dict[Lang, str] = {
    "es": """
**Cómo leer las gráficas**

- `train_loss` (naranja) debería bajar consistente. Si rebota mucho, baja el
  learning rate.
- `val_macro_f1` (turquesa) debería subir y estabilizarse. El mejor checkpoint
  se guarda automáticamente.
- *Early stopping* corta el entrenamiento si val_macro_f1 no mejora por varias
  épocas seguidas.
""",
    "en": """
**Reading the charts**

- `train_loss` (orange) should fall steadily. If it bounces a lot, lower the
  learning rate.
- `val_macro_f1` (teal) should rise then plateau. The best checkpoint is saved
  automatically.
- Early stopping cuts training if val_macro_f1 doesn't improve for several
  epochs in a row.
""",
}


def tray_help(lang: Lang) -> str:
    return TRAY_HELP.get(lang, TRAY_HELP["en"])


def train_help(lang: Lang) -> str:
    return TRAIN_HELP.get(lang, TRAIN_HELP["en"])
