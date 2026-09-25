# STT evaluation: `ink-whisper` on 72 clips

Drug names recognised exactly: **50/72**. Dose numbers recognised: **58/60**. Mean WER 0.15.

After the agent's lookup: exact 55, ambiguous (asks which, or records as heard with candidates) 10, lost (recorded as heard) 7, **mapped to a wrong drug 0** of 72.

## By accent

| accent | drug names | dose numbers | mean WER | clips |
|---|---|---|---|---|
| american_neutral | 9/12 | 10/10 | 0.13 | 12 |
| australian | 9/12 | 10/10 | 0.15 | 12 |
| british | 7/12 | 10/10 | 0.19 | 12 |
| indian | 18/24 | 19/20 | 0.15 | 24 |
| singaporean | 7/12 | 9/10 | 0.12 | 12 |

## By utterance kind

| kind | drug names | dose numbers | mean WER | clips |
|---|---|---|---|---|
| case_line | 0/0 | 0/0 | 0.00 | 6 |
| distractor | 6/6 | 0/0 | 0.00 | 12 |
| drug | 29/42 | 35/36 | 0.19 | 30 |
| sound_alike | 15/24 | 23/24 | 0.21 | 24 |

## Every drug-name miss

- american_neutral (Grant): expected **levothyroxine**, lookup -> lost, heard: "Live with Iroxine 75 micrograms every morning before breakfast."
- american_neutral (Grant): expected **atorvastatin**, lookup -> exact, heard: "I'm on adervastatin 40 at night and a baby aspirin."
- american_neutral (Grant): expected **hydralazine**, lookup -> ambiguous, heard: "Hydrolazine 25 mg 3 times a day."
- indian (Devansh): expected **atorvastatin**, lookup -> exact, heard: "I'm on Etovastatin 40 at night and a baby aspirant."
- indian (Devansh): expected **aspirin**, lookup -> exact, heard: "I'm on Etovastatin 40 at night and a baby aspirant."
- indian (Devansh): expected **klonopin**, lookup -> lost, heard: "I take Clonopan, half a milligram at night for anxiety."
- indian (Devansh): expected **hydralazine**, lookup -> ambiguous, heard: "Hydrolyzine 25 mg 3 times a day"
- indian (Kiara): expected **atorvastatin**, lookup -> lost, heard: "I'm on 8 or was starting 40 at night and a baby aspirin."
- indian (Kiara): expected **klonopin**, lookup -> lost, heard: "I take Clonopane at night for anxiety."
- british (Gemma): expected **atorvastatin**, lookup -> lost, heard: "I'm on Eta Barstatin 40 at night and a baby Aspirin."
- british (Gemma): expected **metoprolol**, lookup -> ambiguous, heard: "Metaprolol 50mg twice a day and Eliquis 5mg twice a day."
- british (Gemma): expected **klonopin**, lookup -> ambiguous, heard: "I take clonopin, half a milligram, at night for anxiety."
- british (Gemma): expected **hydroxyzine**, lookup -> ambiguous, heard: "Hydroxazine 25mg as needed for itching"
- british (Gemma): expected **hydralazine**, lookup -> ambiguous, heard: "Hydrolazine 25mg 3 times a day."
- australian (Arlo): expected **atorvastatin**, lookup -> lost, heard: "I'm on 8 of our statin 40 at night and a baby aspirin."
- australian (Arlo): expected **metoprolol**, lookup -> ambiguous, heard: "Metaprolol 50 mg twice a day, and Eliquis 5 mg twice a day."
- australian (Arlo): expected **hydroxyzine**, lookup -> ambiguous, heard: "Hydroxizine 25mg, as needed for itching."
- singaporean (Nadia): expected **lisinopril**, lookup -> exact, heard: "I take Lysinopril 20 milligrams once a day in the morning."
- singaporean (Nadia): expected **levothyroxine**, lookup -> exact, heard: "Leavity Roxine 75 micrograms every morning before breakfast."
- singaporean (Nadia): expected **atorvastatin**, lookup -> lost, heard: "I'm on October 14th at night and the baby aspirin."
- singaporean (Nadia): expected **metoprolol**, lookup -> ambiguous, heard: "Mesoprolol 50 mg twice a day and Eliquis 5 mg twice a day."
- singaporean (Nadia): expected **klonopin**, lookup -> ambiguous, heard: "I take clonopin, half a milligram at night for anxiety."
