# Gerber2LightBurn PCB

[English README](../README.md)

Gerber2LightBurn PCB to lokalna aplikacja Windows, która zamienia paczki produkcyjne Gerber/Excellon na zweryfikowane maski ablacji farby dla jednostronnych i dwustronnych płytek PCB, a następnie bezpiecznie współpracuje z LightBurn.

## Najważniejsze możliwości

- rozpoznawanie EasyEDA, KiCad, Altium, RS-274X i Excellon;
- wykrywanie TOP/BOTTOM, obrysu, przelotek, PTH, NPTH i slotów;
- maski 1270 DPI, oba warianty odwrócenia BOTTOM, podglądy i prowadnice;
- domyślna pozycja lewego dolnego rogu laminatu X=10 mm, Y=10 mm;
- konfigurowalne: rozmiar laminatu, pozycja, moc, prędkość, interwał, overscan i liczba przejść;
- preset startowy AlgoLaser Pixi 5 W z 2 przejściami;
- LightBurn Live: stan, ETA, XY, prędkość, moc, Frame, Pauza, Stop i potwierdzony Start;
- przełącznik PL/EN zapamiętywany lokalnie;
- całkowicie lokalne przetwarzanie plików.

## Szybki start

```powershell
git clone https://github.com/mateuszsury/gerber2lightburn-pcb.git
cd gerber2lightburn-pcb
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python app.py
```

## Zalecany proces

1. Wyeksportuj ZIP produkcyjny z programu EDA.
2. Upuść go w aplikacji i sprawdź wszystkie walidacje.
3. Podaj wymiary surowego laminatu i jego lewy dolny narożnik na stole.
4. Wybierz fizyczny sposób odwrócenia płytki.
5. Wygeneruj pakiet.
6. Wczytaj stronę TOP lub BOTTOM do LightBurn i zastosuj preset.
7. Wykonaj Frame oraz sprawdź pozycję, wentylację, ochronę oczu i bezpieczeństwo pożarowe.
8. Dopiero wtedy potwierdź Start i pozostań przy urządzeniu.

Wczytanie pliku ani zastosowanie presetu nie uruchamia lasera. Start wymaga checkboxa bezpieczeństwa oraz dodatkowego potwierdzenia.

## Ograniczenia

Aplikacja nie zastępuje DRC ani kontroli netlisty. Domowe trawienie nie metalizuje otworów, dlatego przelotki trzeba połączyć drutem, nitami lub inną metodą. Parametry lasera są tylko punktem startowym i wymagają kalibracji dla konkretnej farby oraz laminatu.

Projekt jest niezależny od LightBurn Software, AlgoLaser, EasyEDA, KiCad i Altium. Nazwy produktów opisują wyłącznie kompatybilność.

