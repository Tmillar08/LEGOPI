# LEGO Pi Voice Commands

## Fast local commands

### Vision
- "scan this brick"
- "what brick is this"
- "what piece is this"
- "identify this part"
- "what do you see"

### Inventory
- "where do I have this brick"
- "where is this piece stored"
- "what do you have this brick stored"
- "add this brick"
- "put this piece in my inventory"

### Demo mode
- "put me in demo mode"
- "turn demo mode on"
- "switch back to normal mode"
- "turn demo mode off"
- "are you in demo mode"
- "what mode are you in"
- "reset the demo"
- "reset the demonstration"

### Volume
- "volume ten"
- "volume three"
- "set volume to five"
- "change volume to seven"
- "volume up"
- "volume down"

### Rebuild
- "start rebuilding set 42110"
- "start building 42110-1"
- "start rebuilding the Land Rover Defender"
- "what set are we building"
- "what set is active"

### Other preserved actions
- "check the visible pieces"
- "mark these found"
- "sync Rebrickable"
- "what can you do"

## LLM fallback

If a request does not match the fast local rules, the assistant asks the local Qwen 1.5B
model to classify it. The LLM is never allowed to execute arbitrary commands or shell code.
It can only select the fixed action list above.
