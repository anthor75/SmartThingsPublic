# VESUVIUS — Il primo capitolo

> *Ogni uomo ha un vulcano dentro.*

## Soggetto del primo film

**Antonello** è un manager di successo a Napoli: ingegnere elettronico, sportivo,
velista, motociclista, appassionato di ogni tecnologia. È brillante e ironico, e
ha una profondità filosofica che pochi conoscono. Vive una vita in pieno controllo.
Numeri, decisioni, responsabilità.

**L'origine.** Durante una regata nel Golfo, uno sciame sismico dei Campi Flegrei
apre una frattura nel fondale. Antonello si tuffa per salvare l'equipaggio di
una barca rovesciata e viene risucchiato in una camera magmatica sommersa.
Non muore: il cuore del vulcano lo *riconosce*. Ne riemerge con un battito che non
è più solo suo. Il Vesuvio è un'anima antica che si è legata alla sua.

**Il conflitto interiore.** Vesuvius è forza pura, giustizia senza filtri, fuoco.
Antonello è misura, ragione, etica. Per tutto il film i due si contendono lo stesso
corpo: ogni volta che Antonello «lascia uscire lui», rischia di non tornare indietro.
Il battito del cuore (il tema musicale del film) è il segnale: quando accelera,
Vesuvius sta arrivando.

**L'antagonista.** **Cenere**, alias Dario Valente, è un ex socio di Antonello e
un geniale ingegnere geotermico. Con il consorzio criminale *La Caldera* vuole
provocare un'eruzione controllata per evacuare Napoli, spingere il valore dei
terreni a zero e comprare la città intera. Il suo esoscheletro assorbe il calore:
è l'unico essere capace di spegnere Vesuvius.

**Arco in tre atti**
1. *La superficie.* La vita di Antonello, i primi terremoti, l'incidente in mare,
   la trasformazione. Primi interventi notturni: un incendio al porto, una rapina
   sulla Tangenziale.
2. *La frattura.* Antonello scopre il piano di Cenere usando le sue competenze da
   ingegnere: dati sismici manipolati, sensori hackerati. Il primo scontro con
   Cenere va male: Vesuvius perde il controllo e una parte della città paga il prezzo.
   Antonello deve imparare che la forza senza ragione è solo un'altra catastrofe.
3. *L'eruzione.* Cenere innesca il Vesuvio. Antonello entra nel cratere e, invece di
   combattere il vulcano, lo *ascolta*: uomo e vulcano diventano un'unica anima.
   Rallenta il proprio battito e con esso il magma, salva la città e spegne Cenere.

**Scena dopo i titoli di coda:** sul fondo del Golfo qualcosa si sveglia. Anche
l'Etna ha un battito.

## Il trailer (60 s)

Montaggio a ritmo cardiaco: il battito parte a 56 bpm e accelera fino a 158 bpm,
poi lascia un secondo di silenzio prima della trasformazione.

| Tempo | Immagine | Voce (Antonello) | Musica / SFX |
|---|---|---|---|
| 0:00–0:03 | Nero, «NAPOLI. OGGI.» | — | Battito lento, drone grave |
| 0:03–0:08 | Antonello di profilo in ufficio, colori freddi, flash subliminale di Vesuvius | «Di giorno, guido aziende.» «Numeri. Decisioni.» | Battito 60 bpm |
| 0:08–0:13 | Antonello guarda in camera. INGEGNERE / MANAGER / SPORTIVO / VISIONARIO | «Ho sempre cercato il limite.» | Whoosh sulle parole |
| 0:13–0:20 | Push lento negli occhi, la luce si scalda, glitch verso Vesuvius | «Ma sotto la superficie, qualcosa si muove.» | Rombo della terra, battito → 88 bpm |
| 0:20–0:29 | Cartelli rossi: QUANDO LA TERRA TREMA / QUANDO LA GIUSTIZIA TACE / QUALCUNO DEVE RISPONDERE | «Quando la terra trema, e la giustizia tace…» «qualcuno deve rispondere.» | Impatti, riser, battito → 158 bpm |
| 0:29–0:30 | Nero | — | **Silenzio** |
| 0:30–0:35 | Il volto diviso uomo/vulcano, push sull'occhio incandescente | «Allora, lascio uscire lui.» | BRAAAM + esplosione |
| 0:35–0:46 | Vesuvius in azione, intervallato da UN UOMO. / UN VULCANO. / UN'ANIMA SOLA. | — | Ostinato d'archi a 140 bpm, timpani, battito come cassa |
| 0:46–0:50 | Bianco → nero | «Io sono Antonello.» | Un solo battito |
| 0:50–0:55 | Titolo **VESUVIUS** tra le braci | «Vesuvius.» | BRAAAM finale |
| 0:55–1:00 | OGNI UOMO HA UN VULCANO DENTRO. / PROSSIMAMENTE | «Ogni uomo ha un vulcano dentro.» | Nota di piano, l'ultimo battito si spegne |

## La voce

La voce nel file `vesuvius_trailer.mp4` è una **voce guida sintetica** che serve
solo per i tempi. Quella vera deve essere la tua. Per registrarla:

- usa `vesuvius_trailer_noVO.mp4` (solo musica ed effetti) e leggi le battute
  della tabella in sincrono;
- parla 20–30 cm dal microfono, a voce bassa e lenta, quasi sussurrata, con il
  petto e non con la gola, lasciando cadere il tono a fine frase;
- in post: un leggero pitch a −1/−2 semitoni, compressione 4:1, +4 dB intorno a
  110 Hz e un riverbero corto. Così ottieni la classica voce da trailer.

## Rigenerare il trailer

```bash
python3 build_trailer.py \
  --office1 profilo_ufficio.jpg --office2 selfie_ufficio.jpg \
  --headshot ritratto.jpg --poster poster_vesuvius.png \
  --clip vesuvius_clip.mp4 --out out/
```

Requisiti: `numpy`, `pillow`, `scipy`, `ffmpeg` (con rubberband), `espeak-ng`,
`mbrola`, `mbrola-it3`. Battute, cartelli e tempi si trovano in cima allo script
(`VO_LINES`, `CARDS`).
