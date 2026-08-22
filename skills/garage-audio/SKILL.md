---
name: garage-audio
description: Engine-noise triage from voice notes — spectrogram heuristic (stage 1), hypothesis ranking, and labeled data collection for the future classifier.
version: 0.1.0
author: owner
license: MIT
metadata:
  hermes:
    tags: [Automotive, Diagnosis, Audio]
---

# Audio Diagnosis (stage 1: spectrogram heuristic)

When the owner sends a voice note or audio clip of an engine noise:

1. **Ask for conditions if unknown**: cold/hot, idle/RPM, standing/driving,
   when it started, what makes it better/worse.
2. **Generate a spectrogram**:
   `ffmpeg -i <audio> -lavfi "showspectrumpic=s=1024x512:legend=1:scale=log" /tmp/spec.png`
   (or `scripts/spectrogram.py`), then look at it with vision.
3. **Analyze**: periodic vertical lines → rotating/meshing frequencies
   (ticks, knocks, whine harmonics); broadband bursts → impacts; narrow
   rising/falling band → whine (bearings, alternator, water pump).
4. **Report hypotheses ranked by likelihood**, each with:
   the sound signature that supports it, a cheap confirmatory check
   (stethoscope point, RPM dependency test, wheel-turn test), and the
   manual section for the repair if applicable.
5. **Confidence honesty**: spectrogram reading is a heuristic. Never state
   "it is X" — state "consistent with X, verify by Y". Safety-relevant
   noises (brakes, rod knock) get an explicit "stop driving until checked".

## Data collection (feeds the future classifier — do this always)

Store the clip with metadata:
`~/.hermes/garage/audio/YYYY/YYYY-MM-DD_<slug>.<ext>` plus sidecar JSON:
`{"conditions": "cold start, idle", "heard": "metallic tick, ~2 Hz",
"cause": null, "confirmed": false}`.
When the owner later confirms the cause (teardown, repair), update
`cause` and `confirmed: true`. These labeled clips train the stage-2 model.
