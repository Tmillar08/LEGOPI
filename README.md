# LEGO Pi Clean Stack — 2026-08-29

This is the rebuilt runtime stack for the currently working LEGO Pi system.

The design intentionally preserves the proven hardware path and HTTP routes while moving
all runtime logic into one `runtime/` package. The old duplicate/experimental `src/legopi`
application is not required by this stack.

## Important

- API secrets are intentionally excluded.
- The normal inventory database is included only as the supplied snapshot; deployment must
  never overwrite the Pi's live database.
- Demo and normal databases are selected dynamically.
- Common commands are routed locally and immediately.
- Qwen 1.5B is retained as a local fallback for ambiguous natural-language commands.
- Brickognize remains the LEGO visual recognition service.
- OpenAI remains the speech transcription and general camera-vision service.

See `docs/DEPLOYMENT.md` for the Pi update procedure.
