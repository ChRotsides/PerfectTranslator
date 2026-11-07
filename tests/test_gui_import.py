import pytest


def test_gui_module_imports():
    pytest.importorskip("tkinter")
    pytest.importorskip("FreeSimpleGUI")
    from perfect_translator import gui

    assert callable(gui.main)
