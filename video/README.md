# Claude in 15 secondi

`claude-in-15-secondi.mp4` — 1920×1080, 30 fps, 15 s, con audio.

Tutto è generato da codice, senza template né asset esterni:

- `source/scene.html` — animazione deterministica: `render(t)` disegna lo stato del fotogramma all'istante `t`.
- `source/render.js` — Playwright/Chromium cattura i 450 fotogrammi.
- `source/music.py` — colonna sonora sintetizzata con NumPy (120 BPM, Am–F–C–G), sincronizzata con le scene.
- `source/paths.json` — percorsi reali dei file `.groovy` di questo repository, mostrati nella scena “Leggo”.

Per rigenerarlo (sostituisci `__PATHS__` in `scene.html` con il contenuto di `paths.json` → `built.html`):

```sh
node render.js                    # → frames/f0000.png … f0449.png
python3 music.py music.wav
ffmpeg -framerate 30 -i frames/f%04d.png -i music.wav -c:v libx264 -pix_fmt yuv420p -crf 18 -c:a aac -shortest claude-in-15-secondi.mp4
```
