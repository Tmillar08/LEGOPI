# LEGO Pi Clean Runtime Architecture

## Goal

This rebuild keeps the proven August 29 behavior while removing duplicated command logic,
scattered database paths, the broken `demo.demo_database` import, and the slow LLM-first
intent path.

## Runtime flow

```text
Hey Jarvis
   |
   v
openWakeWord
   |
   v
6-second maximum command capture with early silence stop
   |
   v
OpenAI gpt-4o-mini-transcribe (speech recognition)
   |
   v
Fast local rule router
   |-------------------------------|
   | known command                 | ambiguous command
   v                               v
immediate action              local Qwen 1.5B via Ollama
                                   |
                                   v
                              JSON action
   |
   +--> /scan ------------------> Brickognize --> color classifier --> spoken result
   +--> /inventory -------------> Brickognize --> color --> selected inventory DB
   +--> /inventory/add ---------> Brickognize --> color --> selected inventory DB
   +--> /vision ----------------> OpenAI vision --> spoken result
   +--> rebuild ----------------> selected Rebrickable catalog DB
   +--> demo -------------------> atomic mode state switch
   +--> volume -----------------> local ALSA control
```

## Database isolation

There are two independent database pairs:

- Normal inventory: `/home/ty/legopi-data/lego_inventory.db`
- Demo inventory: `/home/ty/legopi/demo/demo_inventory.db`
- Normal Rebrickable catalog/build DB: `/home/ty/legopi/data/db/legopi.sqlite3`
- Demo Rebrickable catalog/build DB: `/home/ty/legopi/demo/legopi_demo.sqlite3`

The selected database is resolved at the moment a request executes. Demo mode therefore
protects both physical inventory writes and rebuild-session writes.

## Intent routing

The old router sent every non-exact command through a model and waited up to 8–20 seconds.
The clean router does the opposite:

1. Normalize speech.
2. Match common/natural aliases locally.
3. Execute immediately when confidence is sufficient.
4. Ask Qwen only for genuinely ambiguous requests.
5. If Qwen is unavailable or too slow, return `UNKNOWN` instead of blocking the assistant.

This means adding an alias does not require model inference and does not add latency.

## Preserved capabilities

- Wake word: `Hey Jarvis`
- Brick scan via Brickognize
- General camera vision via OpenAI vision
- Color classification using the calibrated HSV references
- Inventory lookup by detected part + color
- Inventory add with existing-part, new-color, and new-part paths
- Location selection from the 960-bin location table
- Inventory history records
- Owned-set rebuild startup
- Active rebuild status
- Visible-piece check placeholder
- Mark-found placeholder
- Rebrickable sync placeholder response
- Demo mode on/off/status/reset
- Demo database protection
- Voice volume 0–10
- Capability response
- Web camera stream
- `/color-test`, `/color-test-frame`, `/color-sample`, `/camera-metadata`

## Intent actions

`SCAN_BRICK`, `ADD_INVENTORY`, `LOOKUP_INVENTORY`, `START_REBUILD`, `GET_ACTIVE_SET`,
`CHECK_VISIBLE_PIECES`, `MARK_FOUND`, `SYNC_REBRICKABLE`, `GENERAL_VISION`,
`DEMO_MODE_ON`, `DEMO_MODE_OFF`, `DEMO_STATUS`, `DEMO_RESET`, `SET_VOLUME`,
`WHAT_CAN_YOU_DO`, `UNKNOWN`.
