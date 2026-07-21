# LightBurn integration

AblatePCB Studio is an independent application, not an official LightBurn product. The integration was tested with LightBurn 2.1.03 on Windows. Compatibility language identifies the intended interoperable product and does not imply affiliation, endorsement, or sponsorship by LightBurn Software.

## Transport

LightBurn listens for documented automation commands on `127.0.0.1:19840` and returns responses on port `19841`. This app uses `PING`, `STATUS`, `LOADFILE:<path>`, and `START`.

The app never sends `FORCELOAD`. If LightBurn has unsaved changes, LightBurn remains responsible for asking the user what to do.

## Windows UI Automation

The live panel reads the Laser status label, console tail, active-layer speed, power, passes, and interval. It invokes the standard Frame, Pause, and Stop controls. Preset application modifies the active layer and selected image only while LightBurn is not busy.

The live panel and open/focus button are available before Gerber import. In this project-free mode, preset application changes only the active layer's speed, power, interval, and pass count; image geometry and coordinate mode are intentionally left untouched.

UI Automation identifiers may change between LightBurn releases or languages. The integration degrades to an offline/error message rather than silently guessing a control.

## Start boundary

Start is accepted only when:

1. LightBurn reports `Ready`;
2. the in-app safety checkbox is selected;
3. the user accepts the second confirmation dialog.

The app does not automatically start after import, generation, file loading, or preset application.
