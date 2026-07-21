AblatePCB Studio 0.2.3 fixes LightBurn mask placement and project navigation.

Highlights:

- loading TOP or BOTTOM now imports the PNG and applies the project position in one operation;
- LightBurn numeric fields are read back, so a no-op UI Automation write cannot be reported as success;
- with a 62 x 30 mm board and origin X 10 / Y 10, the verified center is X 41 / Y 25 and the image lower-left is X 10 / Y 10;
- the Source, Review, Setup, and Export steps can be used in both directions without losing the analyzed project;
- PNG import preserves the current LightBurn project instead of triggering an unsaved-project replacement dialog.

No import, placement, or navigation action starts the laser.
