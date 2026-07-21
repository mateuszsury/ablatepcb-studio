AblatePCB Studio 0.2.1 fixes the Windows archive picker and makes LightBurn controls available immediately.

Highlights:

- asynchronous, application-owned Qt file and folder picker that no longer freezes the GUI;
- LightBurn connection and live status visible before Gerber import;
- open or focus LightBurn directly from the application;
- edit and apply the Pixi preset without loading a Gerber package;
- preset-only mode preserves the current LightBurn image size and position;
- Polish and English layouts verified at desktop and narrow viewport sizes.

Safety note: no import or preset action starts the laser. Start still requires the safety checkbox, a second confirmation, and a Ready state from LightBurn.
