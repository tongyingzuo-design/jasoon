# Label-Based AI Music Composition Assistant MVP

This is a FastAPI MVP for a label-based AI music composition assistant.

Users choose a chord progression, select labels and intensity values, then generate a customized MusicXML score rendered in the browser with OpenSheetMusicDisplay.

## Local Run

```bash
pip install -r requirements.txt
python run_mvp.py --host 127.0.0.1 --port 8765
```

Open:

```text
http://127.0.0.1:8765/heartmula-web.html
```

## Render Deploy

This repo includes `render.yaml` and pins Python to 3.11.9 for Render.

Render should use:

```bash
pip install -r requirements.txt
python run_mvp.py --host 0.0.0.0
```
