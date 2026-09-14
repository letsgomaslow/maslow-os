"""Built-in voices offered by Maslow's cloud providers.

OpenAI's Realtime list differs from its text-to-speech list. LiveKit's list is a
curated Inworld selection, not the complete provider catalog or custom voices.
"""

OPENAI_VOICES = ("cedar", "marin", "alloy", "ash", "ballad", "coral", "echo", "sage", "shimmer", "verse")
LIVE_VOICES = (*OPENAI_VOICES, "quartz", "ripple", "vesper", "willow", "stone", "gleam", "meridian", "bossa", "tempo", "beacon", "delta", "cinder")
LIVEKIT_VOICES = ("Ashley", "Edward", "Olivia", "Alex", "Dennis")
