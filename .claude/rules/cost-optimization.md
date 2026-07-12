# Cost optimization rules (Step 7)

## Model assignment
- CONVERSATION_MODEL = "claude-haiku-4-5-20251001" — all send_turn calls
- EXTRACTION_MODEL = "claude-sonnet-5" — run_extraction only
- Never downgrade EXTRACTION_MODEL — profile quality depends on it
- Always verify model strings against Anthropic docs before changing

## Caching
- System prompt caching active on both call sites (cache_control: ephemeral)
- Confirmed via cache_read_input_tokens: 35,685 tokens on turn 2
- Conversation history is NOT message-cached (growing history billed as
  regular input — ~$0.04 per 20-turn assessment, accepted at this scale)

## Cost reference (standard rates, verified 2026-07-12)
- Full 20-turn assessment + extraction: ≈ $0.26
- Conversation (Haiku, 20 turns): ≈ $0.16
- Extraction (Sonnet, 1 call): ≈ $0.10
- Done-condition: meaningfully less than $1 ✓
