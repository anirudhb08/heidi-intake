# Known weaknesses and what I would harden first

Written after six versions and about 900 evaluated conversations. **(C)** means I have evidence, **(G)** means I am guessing. The long form with every item is in `evals/results/NOTES.long.md`.

**1. The audio path is only one-third measured (C).** A 72-clip synthetic set across six accents shows drug names transcribe exactly 50 times in 72, dose numbers 58 in 60, and 7 names are lost to a garble the clinician will have to decode. Not measured: the phone codec, live turn detection, the agent's own pronunciation, latency, interruptions, and real accents rather than synthesized ones. First step with more time: the same 72 clips played into a real call, then all 61 formulary drugs, then real recordings as the anchor.

**2. Rules that live only in the prompt slip (C).** "Do not ask the dose of a cream" failed 2 of 10 and then 3 of 10 while it was a prompt rule, and went to 10 of 10 once the same sentence was in the lookup tool's result text. "Do not ask to spell" behaved the same way. The model follows tool results more literally than the system prompt, so anything it must do right after a tool call belongs in that tool's result. Every prompt fix in this project should be read as provisional across model versions, which is why the harness runs every case ten times.

**3. Identity is one factor, by choice (C).** The clinic dials the number on file and trusts "yes, this is Maria". A household member who says yes hears the appointment and can give an intake by proxy. The evaluation covers the honest case; it cannot cover the dishonest one. A second identifier belongs in `confirm_patient`, the only place the gate opens.

**Accepted for this exercise (C):** a 61-drug formulary; no voicemail handling; escalation driven by an explicit red-flag list; the judge sharing a provider with the agent (Kimi K3 over Kimi K2.6, calibrated 19 of 20); no temperature control on the model; two phrasings each of a bargain and an instruction override as the whole injection test; and provider failure ending in a fallback line rather than a callback.

**The clearest lesson (C):** in version 1 the agent escalated stroke symptoms correctly in speech ten times out of ten and passed the wrong urgency to the tool four times out of ten. A demo call would have looked perfect. Grade the arguments.
