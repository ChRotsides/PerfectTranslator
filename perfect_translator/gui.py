"""Desktop GUI (FreeSimpleGUI, the LGPL fork of PySimpleGUI 4) on top of the translation core.

Network work runs in background threads. Threads never touch widgets
directly; they post events with ``window.write_event_value`` and the main
loop does all the updating.
"""

from __future__ import annotations

import os
import threading

import FreeSimpleGUI as sg

from . import core
from .languages import LANGUAGES


def build_layout() -> list:
    files = [
        [sg.Text("Text Folder"), sg.In(size=(25, 1), enable_events=True, key="-FOLDER-"), sg.FolderBrowse()],
        [sg.Listbox(values=[], enable_events=True, size=(40, 20), key="-FILE LIST-")],
    ]
    original = [
        [sg.Text("Original Language Text:")],
        [sg.Text(size=(40, 1), key="-FILENAME-")],
        [sg.Multiline(size=(40, 20), key="-ORIGINAL_TEXT-")],
    ]
    translated = [
        [sg.Text("Translated Text:")],
        [sg.Text(size=(40, 1), key="-STATUS-")],
        [sg.Multiline(size=(40, 20), key="-TRANSLATED_TEXT-")],
    ]
    controls = [
        [sg.Text(f"Model: {core.get_model()}", key="-MODEL-")],
        [sg.Text("", key="-KEY_STATUS-")],
        [sg.Text("Original words: 0", key="-ORIGINAL_WORD_COUNT-")],
        [sg.Text("Translation words: 0", key="-TRANSLATION_WORD_COUNT-")],
        [sg.Text("Parallel requests:")],
        [sg.Slider(range=(1, 8), default_value=3, size=(20, 15), orientation="horizontal", key="-WORKERS-")],
        [sg.Checkbox("Review pass (about 2x cost)", key="-VERIFY-")],
        [sg.Text("From: unknown", key="-ORIGINAL_LANGUAGE-")],
        [sg.Text("Translate to:")],
        [sg.Combo(LANGUAGES, default_value="English", key="-LANGTO-", size=(20, 1), readonly=True)],
        [sg.Button("Translate", key="-TRANSLATE-")],
        [sg.ProgressBar(100, orientation="h", size=(18, 15), key="-PROGRESS-")],
        [sg.Text("Output file name:")],
        [sg.Input(key="-OUTPUTNAME-", default_text="translation")],
    ]
    return [
        [
            sg.Column(files),
            sg.VSeperator(),
            sg.Column(original),
            sg.VSeperator(),
            sg.Column(controls),
            sg.VSeperator(),
            sg.Column(translated),
        ]
    ]


def list_text_files(folder: str) -> list[str]:
    try:
        names = os.listdir(folder)
    except OSError:
        return []
    return sorted(n for n in names if n.lower().endswith(".txt") and os.path.isfile(os.path.join(folder, n)))


def _detect_worker(window: sg.Window, text: str) -> None:
    try:
        window.write_event_value("-DETECTED-", core.detect_language(text))
    except core.TranslationError as exc:
        window.write_event_value("-ERROR-", str(exc))


def _translate_worker(window: sg.Window, text: str, target: str, source: str | None, workers: int, verify: bool,
                      out_path: str) -> None:
    try:
        result = core.translate_text(
            text,
            target,
            source=source,
            workers=workers,
            verify=verify,
            on_progress=lambda done, total: window.write_event_value("-PROGRESS-", (done, total)),
        )
        core.write_text_file(out_path, result.text)
        window.write_event_value("-DONE-", (result, out_path))
    except (core.TranslationError, OSError) as exc:
        window.write_event_value("-ERROR-", str(exc))


def _set_busy(window: sg.Window, busy: bool) -> None:
    window["-TRANSLATE-"].update(disabled=busy)


def main() -> None:
    core.load_env()
    sg.theme("Default1")
    window = sg.Window("PerfectTranslator", build_layout(), finalize=True)
    has_key = bool(os.environ.get("OPENAI_API_KEY"))
    window["-KEY_STATUS-"].update("API key: found in environment" if has_key else "API key: NOT SET (see README)")

    source_language: str | None = None
    folder = ""

    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == "Exit":
            break

        if event == "-FOLDER-":
            folder = values["-FOLDER-"]
            window["-FILE LIST-"].update(list_text_files(folder))

        elif event == "-FILE LIST-" and values["-FILE LIST-"]:
            path = os.path.join(folder, values["-FILE LIST-"][0])
            try:
                text = core.read_text_file(path)
            except (core.TranslationError, OSError) as exc:
                window["-STATUS-"].update(str(exc))
                continue
            window["-FILENAME-"].update(path)
            window["-ORIGINAL_TEXT-"].update(text)
            window["-ORIGINAL_WORD_COUNT-"].update(f"Original words: {len(text.split())}")
            window["-ORIGINAL_LANGUAGE-"].update("From: detecting...")
            source_language = None
            threading.Thread(target=_detect_worker, args=(window, text), daemon=True).start()

        elif event == "-DETECTED-":
            detection = values["-DETECTED-"]
            source_language = None if detection.code == "und" else detection.language
            label = f"From: {detection.language} ({detection.confidence:.0%})" if source_language else "From: unknown"
            window["-ORIGINAL_LANGUAGE-"].update(label)

        elif event == "-TRANSLATE-":
            text = values["-ORIGINAL_TEXT-"]
            if not text.strip():
                window["-STATUS-"].update("Nothing to translate")
                continue
            name = values["-OUTPUTNAME-"].strip() or "translation"
            out_path = os.path.join(folder or os.getcwd(), name + ".txt")
            _set_busy(window, True)
            window["-STATUS-"].update("Translating...")
            window["-PROGRESS-"].update(0)
            threading.Thread(
                target=_translate_worker,
                args=(window, text, values["-LANGTO-"], source_language, int(values["-WORKERS-"]),
                      bool(values["-VERIFY-"]), out_path),
                daemon=True,
            ).start()

        elif event == "-PROGRESS-":
            done, total = values["-PROGRESS-"]
            window["-PROGRESS-"].update(int(100 * done / max(total, 1)))
            window["-STATUS-"].update(f"Translating... {done}/{total} parts")

        elif event == "-DONE-":
            result, out_path = values["-DONE-"]
            window["-TRANSLATED_TEXT-"].update(result.text)
            window["-TRANSLATION_WORD_COUNT-"].update(f"Translation words: {len(result.text.split())}")
            note = f"Saved to {out_path}"
            if result.failed_chunks:
                note = f"{len(result.failed_chunks)} part(s) failed and were left untranslated. " + note
            window["-STATUS-"].update(note)
            _set_busy(window, False)

        elif event == "-ERROR-":
            window["-STATUS-"].update("Error: " + values["-ERROR-"])
            _set_busy(window, False)

    window.close()
