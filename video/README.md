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

# Genesi (trailer cinematografico)

`claude-genesi.mp4` — 1920×1080 in formato 2.39:1, 24 fps, 50 s, con colonna sonora.

Tutta la regia è scritta in codice: 90.000 particelle-glifo prese dal codice Groovy del repository. Prima formano una galassia, poi una città di 381 grattacieli (uno per file, altezza in base alle righe), poi un globo e infine il logo.

- `genesi-source/index.html` — scena Three.js (shader GLSL, bloom, grana, aberrazione cromatica); `render(t)` è deterministica.
- `genesi-source/render.js` — cattura i fotogrammi con Playwright. Servire la cartella via HTTP e lanciare `node render.js <porta> <da> <a> <cartella>`.
- `genesi-source/score.py` — colonna sonora orchestrale sintetizzata con NumPy (Re minore → Re maggiore, riverbero a convoluzione FFT).
- `genesi-source/files.json` — elenco dei file `.groovy` con il numero di righe. `code.txt` (i glifi) si rigenera concatenando i sorgenti `.groovy` senza spazi.
