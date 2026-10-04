# Maslow Voice expressive Orb review

Date: 2026-10-03. Status: reference review and design proposal. The recommendation is to keep Maslow's blue glass Orb and make conversation states easier to read through restrained expressions, distinct input/output movement and clear interruption feedback. An isolated browser concept demonstrates the direction with simulated audio. Native Voice behavior has not changed.

## Source and branch findings

Reviewed runtime `56bbb37a`, clean branch `codex/voice-preferences`, in the existing `maslow-os` checkout. Git ancestry checks confirm `origin/codex/maslow-voice`, `origin/codex/livekit-setup`, `codex/gemini-live-voice-closeout` and `codex/voice-mvp` are ancestors of HEAD. The sibling `maslow-os-gemini` worktree holds the older closeout branch at `b993e17f`. Returning to those older tips would omit subsequent integrated work; use the current branch as the source baseline for a future scoped Orb branch.

The production [provider factory](../../voice/maslow_voice/providers/__init__.py) keeps the routes distinct. `gemini_live` selects the Google realtime model through LiveKit Agents with local audio; it does not require a LiveKit room or project credentials. `livekit` selects the native LiveKit Expressive room route. `openai` selects direct OpenAI Realtime WebSocket with interruption handling, while `gpt_live` selects the separate OpenAI Live adapter. Factory selection is strict. These source findings do not establish successful live-account or physical full-duplex acceptance. See [Gemini architecture](../../voice/docs/gemini-live.md), [Voice architecture](../maslow-voice.md) and the existing dated acceptance evidence.

## What the reference demonstrates

[Bloub](https://bloub.vercel.app/) is an avatar editor and animation demonstration. Its [repository](https://github.com/jeremy-prt/bloub) describes a measured recreation of the x.ai avatar, with independent eye morphing, 14 public animation states and a framework-independent time-sampled engine. Browser inspection covered the customization view, expression control, animation controls and frozen state gallery.

Useful ideas are readable expressions, smooth transitions, restrained gaze/blinks and an easy way to inspect each state. Maslow should develop its own visual language using those principles. The reference's large silhouette changes and decorative states would need evaluation at desktop sizes and should not imply microphone or task events that did not occur. The editor does not demonstrate live speech integration.

## Current Orb findings

The [Orb](../../voice/ui/VoiceOrb.qml) already handles idle, connecting, listening, thinking/working, speaking, muted, error and disabled states through a GPU shader and software fallback. It keeps a stable circular silhouette and supports reduced motion. Its published audio level is microphone amplitude; speaking uses a synthetic cadence. There is no playback amplitude input or explicit interruption transition.

The [panel](../../voice/ui/Panel.qml) already separates task activity through a small dot, preserves manual placement and prevents movement during interaction. However, running, waiting for input, awaiting approval and stopping all produce the same working dot. The compact controls expose microphone state, but the closed Orb does not independently show capture while the speaking animation is active. Transport reconnect text exists in the [controller](../../voice/ui/VoiceController.qml), rather than a dedicated provider reconnect state.

## Proposed behavior

| Situation | Proposed expression and signal |
| --- | --- |
| Ready with microphone off | Calm body and neutral expression; activation remains obvious |
| Connecting | A short directional rim movement with explicit connection text |
| Listening | Attentive expression; input-reactive internal movement and a persistent microphone indicator |
| Preparing a reply | Focused expression and slow inward movement distinct from speech |
| Speaking with capture active | Output-reactive movement while the microphone indicator remains visible |
| User interrupts | Output animation stops when playback is cleared; a brief acknowledgement settles into listening |
| Background task | A separate task mark leaves the conversational expression available |
| Approval or required input | A distinct persistent mark and concise review text; expression is secondary |
| Finished | Brief acknowledgement followed by a calm result mark; no indefinite busy animation |
| Muted or connection failed | Static explicit glyph and text; recovery remains available |

Expressions should describe system behavior such as attentiveness and acknowledgement, rather than infer the user's emotional state. Start with subtle eyes over glass and retain an abstract-glass alternative. Maintain one reliable click target, current shortcuts, manual positioning, accessible names, optional captions and reduced-motion status distinctions. Keep exact permissions and task results in their existing review surfaces.

The technical starting point is a shared presentation model built from actual capture, user-speech, playback, connection and task events. Input and output levels must remain separate. Measure output where PCM is consumed for playback, rather than where cloud packets arrive; clear output activity on cancellation and queue flush. Inspect both the shared [audio transport](../../voice/maslow_voice/audio.py) and the native SDK audio paths before implementation. PortAudio callbacks must continue avoiding blocking work and UI/provider calls. Smooth visual envelopes without delaying interruption, and treat the interruption acknowledgement as a transient transition rather than a permanent provider mode. Any future event/schema change needs separately scoped implementation authorization and compatibility review.

## Concept and verification

The conversation concept is stored outside the runtime repository at workspace-relative `review-output/maslow-orb-expressions.html`. It shows the proposed 56- and 88-pixel Orb allocations, ten state selectors, simulated input/output movement, and host design choices for subtle eyes versus abstract glass, background work and reduced motion. It is a browser drawing, not the native shader or a provider integration.

Browser checks passed for all ten state selections, simultaneous microphone/speaker indicators, interruption acknowledgement returning to listening, identical canvas output under reduced motion, no horizontal overflow at 375-pixel viewport width and no browser runtime errors. The optional host design-control bindings were exercised with a local stub: abstract glass and independent task activity update correctly. Desktop, narrow-screen and dark-theme screenshots were inspected. The reference page and concept ran in existing headless Chromium; no dependency was added. Documentation links, referenced revisions and whitespace were checked separately.

Native Quickshell rendering, shader/fallback parity, actual capture/playback timing, echo cancellation, live accounts and physical speech were not retested. Existing LiveKit Expressive acceptance remains pending. No installed configuration, credentials, package, ISO, deployment or branch tip was changed. No commit or publication is part of this review.

Next action: settle subtle eyes versus abstract glass, then scope the native implementation around truthful playback signals and interruption transitions. Verify with real Quickshell renders at both sizes and the scenario speak, interrupt, resume conversation while a task runs, then review a decision.
