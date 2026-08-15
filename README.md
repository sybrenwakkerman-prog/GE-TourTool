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

## Op de iPhone: als web-app

Safari kan geen `file://` openen, en de voorvertoning in Bestanden voert geen
scripts uit — daar krijg je het rode vak van. De weg eromheen is de tool als
web-app installeren. `docs/` staat daarvoor klaar (gemaakt door
`build_web.py`): een manifest, iconen en een service worker die de hele app
in de kast legt.

Eenmalig instellen, op github.com:

1. **Settings → General → Change visibility → Make public.** GitHub Pages
   hostet geen privérepo's op een gratis account.
2. **Settings → Pages → Source: Deploy from a branch.** Kies branch
   `claude/slovenija-bike-tour-tool-fa6s4w` en map **`/docs`**. Opslaan.
3. Na een minuut staat hij op
   `https://sybrenwakkerman-prog.github.io/GE-TourTool/`

Daarna op de telefoon, één keer met wifi:

4. Open die link in **Safari** (niet in een andere browser — alleen Safari
   mag op iOS iets op je beginscherm zetten).
5. Deelknop → **Zet op beginscherm**.
6. Open hem één keer vanaf je beginscherm terwijl je nog bereik hebt. De
   service worker legt dan alles vast.

Vanaf dat moment werkt hij zonder bereik, full-screen, met een eigen
icoontje. Vliegtuigmodus maakt niet uit.

Wijzigt de tool, draai dan `python3 build_web.py` en push. De service worker
krijgt een nieuwe cachenaam uit de inhoud, dus de oude versie wordt
weggegooid in plaats van blijven hangen.

## Delen met anderen

Twee manieren, met een verschil dat ertoe doet:

**Het bestand doorsturen** — via AirDrop, WhatsApp als document, of mail.
De ontvanger moet het opslaan en daarna in Safari of Chrome openen, precies
zoals hierboven. Dit is de enige manier die onderweg zonder bereik werkt, en
dus de manier die telt zodra je in Slovenië zit.

**Een link delen** — stuur de Pages-link hierboven; die kunnen ze zelf ook
op hun beginscherm zetten. Voor hosten elders maakt `build_web.py` daarnaast
`tourtool-web.html`, zonder eigen `<html>`-omhulsel. Bij een ingesloten
pagina werken twee dingen anders:

- Opslaan gaat via de host, die eerst toestemming vraagt. De tool vangt dat
  af; weigert iemand, dan staat de tekst er alsnog om te kopieren.
- De GPS-knop werkt meestal niet, want een ingesloten pagina krijgt geen
  locatietoestemming. De km met de hand invullen kan altijd.

Kopieren en plakken werkt overal: naast Exporteer JSON staat de tekst om te
kopieren, en onder Importeer zit een veld om hem terug te plakken. Zo blijft
de stand van vier dagen ook overeind als het downloaden ergens strandt.

## De route

De referentieroute is gebouwd uit de vier dag-GPX'en in `gpx/`, aan elkaar
geketend tot een gesloten lus:

| Dag | van km | tot km | km | hm |
|---|---|---|---|---|
| 1 | 0,0 | 167,1 | 167,1 | +1.564 |
| 2 | 167,1 | 366,1 | 199,0 | +2.100 |
| 3 | 366,1 | 511,7 | 145,6 | +2.395 |
| 4 | 511,7 | 578,1 | 66,4 | +614 |
| | | | **578,1** | **+6.673** |

Start en finish liggen op 46,1738 / 14,4157. Hoogste punt: Vršič, 1.609 m,
op km 486,5.

> De oude `gpx/final_route_oud.gpx` is de Cividale-lus uit de eerste
> opzet. Die staat er alleen nog als naslag; de km-punten daaruit gelden
> niet meer voor de huidige route.

## De 26 klimmen

Het bergklassement loopt over 26 klimmen, verdeeld 8 / 9 / 6 / 3 over de
dagen. Van een bult van 42 hoogtemeters tot Vršič — liever veel plekken waar
wat te pakken valt dan drie beslissende bergen.

De zwaarte komt uit een index (`hoogtewinst² / lengte`), zodat steil zwaarder
weegt dan lang. Dat is wat een klim in de benen doet.

Het steilste stuk van de hele route ligt vlak onder de top van Vršič, rond
km 485: **13% over honderd meter, 12% over een halve kilometer**. De steilste
afdaling is dezelfde berg aan de andere kant.

| Cat | Aantal | Zwaarste voorbeeld |
|---|---|---|
| HC | 1 | Vršič, km 472,0 — 14,5 km, +1.028 hm, 7,1% |
| 1 | 2 | Rakitna, km 38,5 — 9,8 km, +529 hm, 5,4% |
| 2 | 3 | Predel, km 436,2 — 4,5 km, +245 hm, 5,4% |
| 3 | 2 | km 92 — 3,8 km, +197 hm, 5,2% |
| 4 | 6 | Predel-aanloop, km 428,8 — 5,2 km, +145 hm |
| 5 | 12 | km 197 — 5,8 km, +115 hm |

Wie alles zou winnen komt op 137 punten. Vršič is daar 10 van, dus 7% — de
zwaarste klim is het meest waard maar beslist niets. Het kleinste klimmetje
levert 4 punten tegen 10 voor Vršič: een factor 2,5, geen factor 10. Wie
elke dag meedoet wint de bollen, niet wie één keer een col uitzit.

Het aantal is een keuze, geen toeval: `build_route.py` detecteert ruim en
houdt de `TARGET_CLIMBS` zwaarste over. Zet dat getal hoger of lager en draai
opnieuw. Klimmen zonder herkenbare naam heten naar hun kilometer; hernoemen
kan in `DEFAULT_CLIMBS`.

## De drie tabbladen

**Vandaag** — vul je huidige km in (of laat de GPS hem bepalen) plus hoe
lang je vandaag al rijdt (twee velden: uren en minuten, of leeg laten als je
een starttijd invult), en je krijgt drie aankomsttijden: zonder stops, met
20 minuten koffie, met 45 minuten lunch. Rood als het na zonsondergang is.
De zonsondergang wordt astronomisch berekend, zonder netwerk.

Uit alleen een km-stand en een verstreken tijd zijn een klimsnelheid en een
vlakke snelheid niet allebei af te leiden — dat is één vergelijking met twee
onbekenden. In plaats daarvan wordt gezocht naar het vermogen dat jouw tijd
over het gereden profiel verklaart, en dat wordt losgelaten op wat er nog
komt. Zo weegt een klim vanzelf zwaarder dan een vlak stuk. Heb je het spoor
van vandaag al ingeladen, dan worden beide snelheden gewoon gemeten.

Bovenaan staat je **voortgang door de hele lus**: hoeveel procent van de 579 km
je hebt gereden, met de hoogtemeters die je gehad hebt en die nog komen.

Daaronder staat **wat komt eraan**: de eerstvolgende klim en sprint vanaf je
huidige km, met afstand, categorie en wat het waard is, plus hoeveel punten er
die dag nog liggen. Zonder dat werkt het klassement onderweg niet — dan rijd je
een cat 2 op zonder te weten dat je hem oprijdt.

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
- **Elke klim afzonderlijk**: tijd, gat, VAM en de bergpunten die eruit
  volgen. De hoogtewinst komt van de referentieroute in plaats van uit drie
  verschillend gekalibreerde barometers.
- **Sprints**: wie er als eerste over was, met het gat en je gemiddelde over
  de laatste kilometer ervoor.
- **Koers**: tijd op kop, aanvallen, je snelste vijf kilometer en je snelste
  vijf kilometer bergaf.
- **Virtuele watts**, maar alleen op segmenten boven 4%. Daaronder domineert
  de CdA-gok de uitkomst en staat er niets — een leeg vakje is eerlijker dan
  een grijs getal.
- **Stilstand**: elapsed tegen moving, met de langste stop. Telt nergens voor
  mee, staat er omdat het de rijtijd verklaart.
- **De dag**: het profiel van de dag met de klimmen erop en waar je stilstond,
  met de duur van elke stop. Daaronder de dag als tijdlijn — vertrek, stops,
  de voet en de top van elke serieuze klim met hoogte en klimtijd, je hoogste
  punt, je snelste moment, en hoe laat je binnen was. Niet wie won, maar hoe
  de dag verliep. Kies bovenin wiens dag je bekijkt.
- **Terugkijken**: een schuif over de kaart. Sleep naar 14:32 en je ziet waar
  alle drie stonden, met de gaten ertussen. Er zit een afspeelknop op die de
  dag in ongeveer een minuut doorloopt.
- **Dagverslag**: de dag in een alinea, om in de groepsapp te plakken. Droog
  en feitelijk — dat leest harder dan grappig proberen te zijn.
- **Overig**: maximumsnelheid met km-punt, temperatuur als de Garmin die
  meelevert, aankomstvolgorde, en de spreiding in snelheid als proxy voor
  wie zat te accelereren aan kop.

**Klassement** — drie truien, cumulatief over de dagen.

- **Algemeen** op opgetelde rijtijd, met het gat naar de leider. Stops tellen
  niet mee: een lekke band of een lange koffie hoort je klassement niet te
  kosten, het gaat om de rit. Iedereen wordt over hetzelfde stuk vergeleken —
  het deel dat jullie alle drie hebben gereden — zodat wie zijn computer wat
  later aanzette daar niets van merkt.
- **Berg** op punten boven op elke klim, naar categorie.
- **Sprint** op punten bij de tussensprints en bij de streep. Twee
  tussensprints per dag, automatisch op de vlakste stukken gelegd, want
  bergop is het gewoon klimmen.

Daaronder staat wat niet meetelt voor een trui maar wel het nakijken waard
is: **tijd op kop**, **aanvallen** en hoe vaak je gelost werd. Tijd op kop is
de tijd dat jij van de drie het verst op de route was — wie voorop rijdt vangt
de wind, en dat is uit drie GPS-sporen gewoon af te lezen. Een aanval is een
gat van meer dan 100 m dat je zelf opende.

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
  berg: {                    // voor de eerste drie boven, per categorie
    "HC": [10, 7, 5],
    "1":  [8, 6, 4],
    "2":  [7, 5, 3],
    "3":  [6, 4, 3],
    "4":  [5, 3, 2],
    "5":  [4, 2, 1]
  },
  sprintTussen: [5, 3, 1],   // bij een tussensprint
  sprintFinish: [10, 6, 4]   // bij de streep aan het eind van de dag
};
```

Er wordt niets bewaard als je het tabblad sluit — geen localStorage, dat was
de afspraak. **Exporteer aan het eind van elke dag naar JSON en importeer dat
de volgende avond terug.** Er is ook een tekst-export voor in de groepsapp.

## Controles

De knop **Draai zelftest** bouwt drie synthetische rijders op de echte route
met gaten op vooraf bepaalde kilometers, schrijft die weg als GPX en jaagt ze
door precies dezelfde molen als een echt bestand. Vindt de detector die gaten
niet terug, dan zie je het meteen. 62 controles.

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
de 62 zelftest-controles plus de vier echte dagbestanden door de projectie en
de afstandscontrole.

## Wat er bewust niet in zit

Geen frameworks, geen build step, geen kaarttegels, geen Strava-koppeling,
geen opslag, en geen velden voor hartslag, vermogen of cadans — die data
hebben we niet, en lege kolommen zijn erger dan geen kolommen.
