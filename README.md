# Desktop Cat

Small PyQt5 script that loads GIF frames from the `gif/` folder and shows a little animated cat in the bottom corner of the screen. It respects the Windows work area (so it will sit above the taskbar when the taskbar is visible, or at the bottom of the screen when the taskbar is hidden).

Usage

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run:

```bash
python Cat.py
```

Controls

- Click the cat to make it jump toward the click.

Notes

- GIF files are loaded from the `gif/` folder next to `Cat.py`.
- Playback speed has been reduced slightly for smoother visuals.
