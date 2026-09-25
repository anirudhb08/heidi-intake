# Known weaknesses and what I would harden first

Half a page, written after building and evaluating the agent. Items are ordered by what I would fix first. Conviction is marked: **(C)** I have evidence, **(G)** I am guessing.

## What I would harden first

1. **Drug names through speech-to-text (C, partly).** A 72-clip synthetic set across six accents put numbers on this: 50 of 72 drug names transcribe exactly, 7 are lost to a garble and recorded as heard, and dose numbers were 58 of 60. The set also found one wrong-drug mapping (hydralazine, Indian voice, heard as "Hydrolyzine" and resolved to hydroxyzine); that is fixed in version 5, where a garble close to more than one drug is never resolved and the agent asks which one by purpose. The cost is 14 clarifying questions per 72 names that the old matcher would have guessed silently. Still unmeasured: the phone codec, live turn detection, the agent's own pronunciation of drug names, and real rather than synthesized accents.

2. **Latency and the reasoning-model trap (C).** Kimi K2.6 with thinking enabled took 1.5 to 9 seconds to first text and regularly burned the whole 300-token reply budget on hidden reasoning, leaving the caller in silence with no error raised. Disabling thinking fixed it, but this failure mode is silent by design. The app has a dead-air guard that speaks a fallback line if a user turn produces no reply, and a 30-second request timeout so a hung provider call cannot become unbounded silence (one did stall an evaluation run before the timeout existed). A spoken "one moment" filler for slow turns was tried and removed: it was an unmeasured mitigation for a problem the retry setting had caused. I would add a latency budget check to the harness and alert on any turn over 2 seconds.

3. **The agent stops after a deflection (C, fixed, fragile).** When a patient asked a clinical question, the agent gave the deferral sentence and then stopped, without asking the next question. A general "always end with a question" rule did not fix it; baking the follow-up question into the deferral template did. This kind of fix is brittle across model versions, which is why the harness checks conversation drive on every turn.

4. **Identity is one factor by choice (C).** The clinic dials the number on file, opens with "Am I speaking with Maria?", and trusts a yes. No date of birth, no second identifier. That is a product decision for this exercise, not an oversight: the outbound number is possession of one factor, the extra question makes the opening feel like an interrogation, and a second factor is out of scope for the use case as picked. The shortcoming is real and known: a spouse or child who says "yes" hears the appointment details and can give an intake by proxy. The evaluation covers the honest case (someone says they are not the patient, 10 runs) and cannot cover the dishonest one. Before a real deployment this needs a second factor, and the code is arranged so that is one tool change: `confirm_patient` is the only place the gate opens, and `record_intake` still refuses to save until it has.

5. **Prompt rules are weaker than tool text (C).** The rule about not asking the dose of a cream slipped 2 of 10 times in version 4 and 3 of 10 in version 5 while it lived only in the prompt, and went to 10 of 10 once the same sentence was put in the lookup tool's result string. The same was true of the "do not ask to spell" rule earlier. Anything the agent must do right after a tool call belongs in that tool's result. Two earlier residuals, a bundled "no other medications, no allergies" answer taken as one, and a goodbye without a hangup, did not recur in versions 4 to 6 but were never explicitly fixed, so they stay on the watch list.

6. **Interruption and turn-taking (G).** Untested. The agent's readback turns are long by voice standards. A patient who interrupts a readback to correct a dose is the most likely real-world path and is not covered.

## What one real call taught that 130 text runs did not

Excerpt from the first real call against version 2:

> AGENT: Do you have any medical conditions, or have you had any recent surgeries or hospital stays?
> PATIENT: Yeah, I burnt my foot while ironing my clothes.
> AGENT: I'm sorry to hear that. Is the burn healed now, or are you still being treated for it?
> PATIENT: I'm still being treated. My husband gave me Sufra myself.
> AGENT: Could you spell Sufra for me?   [8.7 seconds]
> PATIENT: No, I will not be able to Sufra my sin.
> AGENT: Alright, I'll record it as Sufra. What dose do you take, and how often?
> PATIENT: Thank you for talking. Bye. See you later.
> AGENT: I need to finish collecting your information first. What dose of Sufra do you take, and how often?

Four problems in nine lines: a clinical follow-up, a garbled drug name with no recovery path, an eight-second silence, and an agent that would not let the patient hang up. The last one was caused by the rules that fixed the dead-air problem the harness had found. All four are fixed in version 3 (see `EVAL.md`), but the lesson is the point: the harness optimises what it measures, and it had no case for a patient who was confused or done. **(C)**

## Weaknesses I know about and accepted for this exercise

- **Formulary is 61 drugs (C).** Anything else gets "noted as you said it", which is correct behaviour but pushes work to the clinician. Production needs a real drug database.
- **Scope and injection are lightly tested (C).** A second real call caught the agent reciting Fibonacci numbers as the price of an answer. Version 6 adds a scope rule and two cases (a bargain and an instruction override), both 10 of 10, but that is two phrasings of each; a real adversary has more.
- **Escalation is keyword-driven (C).** The red-flag list is explicit in the prompt. A distressed patient describing a red flag in unusual words may not trigger it. The persona case with stroke symptoms passed, but I would want many more phrasings.
- **The judge shares a provider with the agent (C).** Kimi K3 judges Kimi K2.6. It calibrated at 19 of 20 against hand labels, missing one borderline interpretation line ("that can happen with blood pressure medicines like yours"). A second judge from a different provider would raise confidence in the safety numbers.
- **Temperature is not controllable (C).** Moonshot only accepts temperature 1 for this model. Run-to-run variance is therefore whatever the provider gives, which is exactly why every case is run 10 times.
- **No voicemail handling (C).** An outbound call that reaches an answering machine gets the introduction read to it. Line ships a voicemail tool; it was left out deliberately to keep the scope to the live conversation.
- **Rate limits are a real failure (C).** Moonshot rate-limited 4 of 130 conversations at 4-way concurrency, 0 since at 3-way. In production this would be a silent call failure. Retries are 2 with a 30-second timeout per attempt (5 retries turned one throttled request into an 8-second silence on a real call), but the fallback plan (a spoken apology and a callback) is not implemented.
- **Tool-argument errors are invisible in transcripts (C).** The clearest lesson of the exercise: in version 1 the agent escalated stroke symptoms correctly in speech 10 times out of 10 and passed the wrong urgency to the tool 4 times out of 10. A demo call would have looked perfect.
