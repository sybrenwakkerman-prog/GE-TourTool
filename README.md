# Grand Escape Tourtool

Eén HTML-bestand om drie ritten per dag tegen elkaar af te zetten, en om
overdag te zien of het hotel voor donker haalbaar is.

Voor Sybren, Luuk en Thijmen.

Verder is er niets nodig: geen netwerk, geen installatie, geen account. Alle
GPX-verwerking gebeurt in de browser zelf.

## Openen

**Bewaar `tourtool.html` eerst op je telefoon en open het daarna vanuit
Bestanden met Safari of Chrome.** Rechtstreeks aantikken in een chat-app of
mail werkt vaak niet: die openen het in een ingebouwde voorvertoning, en die
blokkeert scripts. Je krijgt dan wel de opmaak te zien maar niets werkt —
lege keuzelijsten, geen kaart, tabbladen die niet reageren.

Gebeurt dat, dan zie je nu bovenaan een rood vak dat vertelt wat er mis is.
Verdwijnt dat vak, dan draait alles. Het bestand hoort ongeveer 165 kB te
zijn; is het kleiner, dan is de download afgebroken.

Op de iPhone: in Safari op de link → Delen → *Bewaar in Bestanden*, daarna
openen vanuit de app Bestanden. Eenmaal geopend werkt alles offline, ook in
de vliegtuigmodus.

## De route

De referentieroute is gebouwd uit de vier dag-GPX'en in `gpx/`, aan elkaar
geketend tot een gesloten lus:

| Dag | van km | tot km | km | hm |
|---|---|---|---|---|
| 1 | 0,0 | 187,6 | 187,6 | +1.727 |
| 2 | 187,6 | 386,6 | 199,0 | +2.113 |
| 3 | 386,6 | 532,2 | 145,6 | +2.401 |
| 4 | 532,2 | 579,1 | 46,9 | +429 |
| | | | **579,1** | **+6.690** |

Start en finish liggen op 46,3035 / 14,2863, even ten noorden van Kranj.
Hoogste punt: Vršič, 1.608 m, op km 507.

> De oude `gpx/final_route_oud.gpx` is de Cividale-lus uit de eerste
> opzet. Die staat er alleen nog als naslag; de km-punten daaruit gelden
> niet meer voor de huidige route.

## Strijdsegmenten

De zwaarste klim van elke dag, zodat er elke dag wat te winnen valt:

| Segment | Dag | van km | tot km | km | hm | gem. |
|---|---|---|---|---|---|---|
| Rakitna | 1 | 59,2 | 68,8 | 9,5 | +528 | 5,6% |
| km 257 | 2 | 257,0 | 263,0 | 6,0 | +370 | 6,2% |
| Vršič | 3 | 492,5 | 507,2 | 14,8 | +1.028 | 7,0% |
| km 532 | 4 | 532,5 | 536,0 | 3,5 | +199 | 5,7% |

Twee ervan konden niet met zekerheid op naam worden gebracht en heten nu
naar hun kilometer. Hernoemen kan in `DEFAULT_SEGMENTS`, onderin
`build_route.py` gegenereerd en in `tourtool.html` ingebakken.

Andere gedetecteerde klimmen boven +150 hm die geen strijdsegment werden:
km 113 (+199), km 250 (+163), km 265 (+303) en Predel (+249, km 456,8).

## De drie tabbladen

**Vandaag** — vul je huidige km in (of laat de GPS hem bepalen) plus hoe
lang je onderweg bent, en je krijgt drie aankomsttijden: zonder stops, met
20 minuten koffie, met 45 minuten lunch. Rood als het na zonsondergang is.
De zonsondergang wordt astronomisch berekend, zonder netwerk.

Uit alleen een km-stand en een verstreken tijd zijn een klimsnelheid en een
vlakke snelheid niet allebei af te leiden — dat is één vergelijking met twee
onbekenden. In plaats daarvan wordt gezocht naar het vermogen dat jouw tijd
over het gereden profiel verklaart, en dat wordt losgelaten op wat er nog
komt. Zo weegt een klim vanzelf zwaarder dan een vlak stuk. Heb je het spoor
van vandaag al ingeladen, dan worden beide snelheden gewoon gemeten.

Kies bij **Ik ben** wie je bent; dat bepaalt alleen welk gewicht het
vermogensmodel gebruikt. De dagindeling is aanpasbaar, want het echte schema
mag afwijken van de GPX-splits.

**Analyse** — laad één tot drie GPX'en, kies de dag en druk op Analyseer.
Naam en gewicht worden voorgevuld uit de `RIDERS`-constante, in de volgorde
waarin je de bestanden kiest — dus even controleren of Sybren ook echt
Sybren is. Je krijgt:

- **Lossingen.** De sporen worden naast elkaar gelegd op de afstand-as, niet
  op de tijd-as. Een breuk is een tijdgat boven 20 s dat langer dan een
  minuut aanhoudt; hij sluit zodra het gat onder 10 s zakt. Per breuk: het
  km-punt, wie gelost werd, hoe lang, het grootste gat in seconden én meters,
  en waar het weer dicht was.
- **VAM per strijdsegment**, met de hoogtewinst van de referentieroute in
  plaats van drie verschillend gekalibreerde barometers.
- **Virtuele watts**, maar alleen op segmenten boven 4%. Daaronder domineert
  de CdA-gok de uitkomst en staat er niets — een leeg vakje is eerlijker dan
  een grijs getal.
- **Stilstand**: elapsed tegen moving, langste enkele stop met km-punt en
  tijdstip, aantal stops boven twee minuten, en wie het langst stilstond.
- **Overig**: maximumsnelheid met km-punt, temperatuur als de Garmin die
  meelevert, aankomstvolgorde, en de spreiding in snelheid als proxy voor
  wie zat te accelereren aan kop.

**Klassement** — cumulatief over de dagen.

De rijders staan bovenaan hetzelfde scriptblok. Het gewicht is rijder + fiets +
bagage, en de virtuele watts hangen eraan:

```js
const RIDERS = [
  { naam: "Sybren", gewicht: 80 },
  { naam: "Luuk", gewicht: 77 },
  { naam: "Thijmen", gewicht: 75 }
];
```

Punten in `POINTS`, daar vlak onder:

```js
const POINTS = {
  segment: [3, 2, 1],   // 1e, 2e, 3e op elk strijdsegment
  besteVam: 2,          // hoogste VAM van de dag
  minsteStiltijd: 2,    // kortst stilgestaan
  gelost: -1,           // per keer gelost worden
  langsteStop: -1       // langste enkele stop van de dag
};
```

Er wordt niets bewaard als je het tabblad sluit — geen localStorage, dat was
de afspraak. **Exporteer aan het eind van elke dag naar JSON en importeer dat
de volgende avond terug.** Er is ook een tekst-export voor in de groepsapp.

## Controles

De knop **Draai zelftest** bouwt drie synthetische rijders op de echte route
met gaten op vooraf bepaalde kilometers, schrijft die weg als GPX en jaagt ze
door precies dezelfde molen als een echt bestand. Vindt de detector die gaten
niet terug, dan zie je het meteen. 38 controles.

Op geïmporteerde data draaien er sanity checks mee: afstand binnen 5% van het
routesegment, geen snelheden boven 90 km/u, geen VAM boven 2.000, en een
waarschuwing als meer dan 20% van de punten verder dan 500 m van de route
ligt. Wat faalt komt bovenaan de analyse te staan, in het rood.

## De route opnieuw bouwen

Wijzigt de route, vervang dan de bestanden in `gpx/` en draai:

```
python3 build_route.py
```

Dat leest de dagbestanden, ketent ze, downsamplet naar 2.000 punten,
detecteert de klimmen, schrijft `route_data.js` en plakt het resultaat tussen
de `ROUTE DATA`-markers in `tourtool.html`. Alleen de standaardbibliotheek,
geen dependencies.

Twee dingen die daar minder vanzelfsprekend zijn dan ze lijken:

- Er wordt gedownsampled op de geometrie **en** op het hoogteprofiel. Alleen
  op het profiel simplificeren snijdt bochten af, en dan projecteren de
  sporen straks honderden meters verkeerd.
- De RDP knipt op de dagovergangen. Zonder die knip valt bij een lus het
  eerste punt samen met het laatste, is de basislijn ontaard en houdt de
  simplificatie twee punten over.

`ROUTE_PTS` bewaart de **echte wegafstand** per punt. De polyline zelf is
korter, omdat 2.000 punten de haarspelden van Vršič niet kunnen uittekenen.
Dat is met opzet: km-standen moeten met je fietscomputer overeenkomen, en een
echte GPS-log volgt de bocht wel.

## Tests

```
node tests/run.js
```

Trekt de scriptblokken uit `tourtool.html` en draait ze in Node met een
kleine XML-lezer, zodat de analyse te controleren is zonder telefoon. Draait
de 38 zelftest-controles plus de vier echte dagbestanden door de projectie en
de afstandscontrole.

## Wat er bewust niet in zit

Geen frameworks, geen build step, geen kaarttegels, geen Strava-koppeling,
geen opslag, en geen velden voor hartslag, vermogen of cadans — die data
hebben we niet, en lege kolommen zijn erger dan geen kolommen.
