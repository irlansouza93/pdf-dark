"""Testes da matemática de layout do leitor (sem abrir uma janela)."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from pdf_dark.viewer import PageBox, compute_layout, fit_scale

A4 = (595.0, 842.0)


def test_fit_scale_uses_the_widest_page() -> None:
    scale = fit_scale([(400.0, 600.0), (800.0, 400.0)], 1000, margin=20)
    assert scale == (1000 - 40) / 800


def test_fit_scale_ignores_empty_document() -> None:
    assert fit_scale([], 800) == 1.0


def test_compute_layout_stacks_pages_with_gaps() -> None:
    sizes = [A4, A4, A4]
    boxes, width, height = compute_layout(
        sizes, scale=1.0, viewport_width=700, margin=26, gap=16
    )

    assert [box.index for box in boxes] == [0, 1, 2]
    assert width == 595
    for previous, current in zip(boxes, boxes[1:]):
        assert current.y == previous.y + previous.height + 16
    assert height == boxes[-1].y + boxes[-1].height + 26


def test_compute_layout_centers_pages() -> None:
    boxes, _, _ = compute_layout([(300.0, 500.0)], scale=1.0, viewport_width=700, margin=20)
    assert boxes[0].x == (700 - 300) / 2


def test_compute_layout_keeps_a_margin_when_page_is_wider_than_window() -> None:
    boxes, _, _ = compute_layout([(900.0, 400.0)], scale=1.0, viewport_width=500, margin=20)
    assert boxes[0].x == 20


def test_compute_layout_scales_page_sizes() -> None:
    boxes, width, height = compute_layout(
        [(200.0, 400.0)], scale=0.5, viewport_width=400, margin=10
    )
    assert (boxes[0].width, boxes[0].height) == (100, 200)
    assert width == 100
    assert height == 10 + 200 + 10


def test_compute_layout_empty_document() -> None:
    boxes, width, height = compute_layout([], scale=1.0, viewport_width=800)
    assert boxes == []
    assert (width, height) == (0, 0)


def test_page_box_is_immutable() -> None:
    box = PageBox(0, 10.0, 20.0, 30, 40)
    with pytest.raises(FrozenInstanceError):
        box.width = 99  # type: ignore[misc]
