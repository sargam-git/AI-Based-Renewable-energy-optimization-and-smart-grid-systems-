# Validation logs

These are captured outputs from the final verification runs. See `../VALIDATION.md` for interpretation, commands, scenario results and disclosed limitations.

- `backend-tests.log`: isolated Pytest suite.
- `frontend-tests.log`: Vitest unit suite.
- `browser-tests.log`: Playwright integration suite against the running application.
- `frontend-build.log`: Vite production build.

The browser suite intentionally creates temporary maintenance/upload/scenario records in the running demo database. After capture, the demo database was reinitialized for delivery; datasets and trained models were preserved.
