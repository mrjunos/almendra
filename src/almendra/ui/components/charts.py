"""Plotly chart helpers — used by Train (live) and Evaluate (confusion matrix)."""

from __future__ import annotations

from typing import Any


def training_curve(epochs: list[int], train_loss: list[float], val_f1: list[float]) -> Any:
    """Two-line live training chart: train_loss (left axis) + val_macro_f1 (right)."""
    import plotly.graph_objects as go

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=epochs,
            y=train_loss,
            name="train_loss",
            mode="lines+markers",
            line={"color": "#ff8c73"},
            yaxis="y",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=epochs,
            y=val_f1,
            name="val_macro_f1",
            mode="lines+markers",
            line={"color": "#13ecda"},
            yaxis="y2",
        )
    )
    fig.update_layout(
        margin={"l": 10, "r": 10, "t": 30, "b": 30},
        height=360,
        xaxis={"title": "epoch"},
        yaxis={"title": "train_loss", "side": "left"},
        yaxis2={
            "title": "val_macro_f1",
            "overlaying": "y",
            "side": "right",
            "range": [0, 1],
        },
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02},
    )
    return fig


def confusion_heatmap(matrix: list[list[int]], class_names: list[str]) -> Any:
    """Square heatmap of the confusion matrix. Rows = true, cols = pred."""
    import plotly.graph_objects as go

    fig = go.Figure(
        data=go.Heatmap(
            z=matrix,
            x=class_names,
            y=class_names,
            colorscale="Teal",
            hovertemplate="true=%{y}<br>pred=%{x}<br>count=%{z}<extra></extra>",
        )
    )
    fig.update_layout(
        margin={"l": 10, "r": 10, "t": 30, "b": 30},
        height=480,
        xaxis={"title": "predicted", "tickangle": -45},
        yaxis={"title": "true", "autorange": "reversed"},
    )
    return fig
