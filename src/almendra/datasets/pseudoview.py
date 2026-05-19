"""Pseudo-views — an honest stand-in for real multi-view data.

Real multi-view data — a bean's *actual* other faces — needs the tray capture
rig (see ``capture/protocol.md``). Until that data exists, pseudo-views let the
multi-view model and the train/eval path be exercised and characterised: each
pseudo-view is the single real image under a distinct fixed orientation.

What this validates: the multi-view machinery (fusion, view-dropout, variable
view counts) and angular robustness.

What it does **not** validate: face coverage — a pseudo-view shows the *same*
face. RQ1 (does seeing the hidden face lower the missed-defect rate) genuinely
needs real tray data; pseudo-views must never be reported as if they answered it.
"""

from __future__ import annotations

from PIL import Image

# (rotation degrees, horizontal flip) — pseudo-view i uses ORIENTATIONS[i % len].
ORIENTATIONS: list[tuple[int, bool]] = [
    (0, False),
    (90, False),
    (180, False),
    (270, False),
    (0, True),
    (90, True),
    (180, True),
    (270, True),
]


def pseudo_view(image: Image.Image, index: int) -> Image.Image:
    """Return the ``index``-th pseudo-view of ``image`` (a fixed distinct orientation).

    A bean has no canonical orientation, so a rotation/flip is a legitimate
    stand-in for an angular viewpoint change — but not for a different face.
    """
    angle, flip = ORIENTATIONS[index % len(ORIENTATIONS)]
    out = image.rotate(angle, expand=True) if angle else image
    if flip:
        out = out.transpose(Image.FLIP_LEFT_RIGHT)
    return out
