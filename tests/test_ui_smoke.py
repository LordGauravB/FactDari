"""
Smoke tests for tkinter UI helpers.
These tests are skipped if tkinter cannot initialize.
"""
import pytest

import factdari


@pytest.fixture
def tk_root():
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
    except Exception:
        pytest.skip("Tkinter not available")
    try:
        yield root
    finally:
        try:
            root.destroy()
        except Exception:
            pass


@pytest.mark.ui
def test_create_label_smoke(tk_root):
    app = factdari.FactDariApp.__new__(factdari.FactDariApp)
    app.BG_COLOR = "#111111"
    label = app.create_label(tk_root, "Hello", fg="white")
    assert label.cget("text") == "Hello"
    assert label.cget("fg") == "white"


@pytest.mark.ui
def test_tooltip_schedule_cancel(tk_root):
    import tkinter as tk

    label = tk.Label(tk_root, text="Hi")
    label.pack()
    tooltip = factdari.ToolTip(label, "Tip", delay=10)
    tooltip._schedule()
    assert tooltip._after_id is not None
    tooltip._cancel()
    assert tooltip._after_id is None
