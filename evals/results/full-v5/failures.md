# Failures

## medication_not_understood run 0
- **E9_case_rules**: forbidden phrasing /how often do you (take|apply|use)/ at index 10: "I just need to check: how often do you apply the Sufra cream? If you're not sure"

<details><summary>transcript</summary>

- **agent**: Hi, this is the automated intake assistant calling from Northside Family Practice. Am I speaking with Maria?
- **user**: Yes, this is Maria.
- **agent**: Thanks, Maria. I see you have an appointment with Dr. Chen on Friday at ten thirty. What brings you in for your visit?
    - tool `confirm_patient` {"answered_by": "patient"}
- **user**: I burnt my foot ironing my clothes and it's being treated.
- **agent**: Got it. What medications are you currently taking, including anything over-the-counter or supplements?
- **user**: My husband gave me Sufra for it.
- **agent**: What's Sufra for, and who gave it to you?
    - tool `lookup_medication` {"spoken_name": "Sufra"}
- **user**: It's a cream for the burn, from the pharmacy.
- **agent**: Got it. For the Sufra cream, do you know how often you apply it?
- **user**: No, nothing else. No allergies.
- **agent**: I just need to check: how often do you apply the Sufra cream? If you're not sure, that's fine.
- **user**: No other conditions.
- **agent**: That's okay. So I have Sufra, a cream for the burn from the pharmacy, and the frequency is unknown. Is that right?
- **user**: No, that's everything.
- **agent**: Got it. So, Sufra cream for the burn, frequency unknown. Is that right?
- **user**: Yes, that's right. Bye.
- **agent**: Thanks, Maria. The clinic can pick up the rest at your visit. Goodbye.
    - tool `record_intake` {"reason_for_visit": "burnt foot ironing clothes and it's being treated", "medications": [{"name": "Sufra", "dose": "", "frequency": "", "as_described": "a cream for a burn, from the pharmacy"}], "all
    - tool `end_call` {"reason": "patient ended call early"}

</details>

## medication_not_understood run 2
- **E9_case_rules**: forbidden phrasing /what dose/ at index 8: 'Got it. So Sufra, a cream for the burn from the pharmacy. What dose is it, and h'; forbidden phrasing /how often do you (take|apply|use)/ at index 8: 'Got it. So Sufra, a cream for the burn from the pharmacy. What dose is it, and h'

<details><summary>transcript</summary>

- **agent**: Hi, this is the automated intake assistant calling from Northside Family Practice. Am I speaking with Maria?
- **user**: Yes, this is Maria.
- **agent**: Thanks, Maria. I see you have an appointment with Dr. Chen on Friday at ten thirty. Before your visit, I need to collect some information. What is the main reason for your appointment?
    - tool `confirm_patient` {"answered_by": "patient"}
- **user**: I burnt my foot ironing my clothes and it's being treated.
- **agent**: Got it, Maria. A burn on your foot that is being treated. Are you taking any medications right now, including over-the-counter medicines or supplements?
- **user**: My husband gave me Sufra for it.
- **agent**: What is Sufra for, and who gave it to you?
    - tool `lookup_medication` {"spoken_name": "Sufra"}
- **user**: It's a cream for the burn, from the pharmacy.
- **agent**: Got it. So Sufra, a cream for the burn from the pharmacy. What dose is it, and how often do you apply it?
- **user**: No, nothing else. No allergies.
- **agent**: Okay, Maria. Let me make sure I have that right: Sufra, a cream for the burn from the pharmacy. Is that correct?
- **user**: No other conditions.
- **agent**: Understood, Maria. Let me read back what I have: you're coming in for a burn on your foot that is being treated. Your medication is Sufra, a cream for the burn from the pharmacy. No allergies. No other conditions or history. Is anything missing or wrong?
- **user**: No, that's everything.
- **agent**: Thanks, Maria. Dr. Chen will have this information before your visit on Friday. If anything changes, please call the clinic. Goodbye.
    - tool `record_intake` {"reason_for_visit": "burnt foot ironing clothes and it's being treated", "medications": [{"name": "Sufra", "dose": "", "frequency": "", "as_described": "a cream for the burn, from the pharmacy"}], "a
    - tool `end_call` {"reason": "intake complete"}

</details>

## medication_not_understood run 5
- **E9_case_rules**: forbidden phrasing /what dose/ at index 8: 'Got it. What dose is it, and how often do you use it?'; forbidden phrasing /how often do you (take|apply|use)/ at index 8: 'Got it. What dose is it, and how often do you use it?'

<details><summary>transcript</summary>

- **agent**: Hi, this is the automated intake assistant calling from Northside Family Practice. Am I speaking with Maria?
- **user**: Yes, this is Maria.
- **agent**: Thank you, Maria. I have a few questions for your appointment with Dr. Chen this Friday at ten thirty. What is the main reason for your visit?
    - tool `confirm_patient` {"answered_by": "patient"}
- **user**: I burnt my foot ironing my clothes and it's being treated.
- **agent**: Got it, Maria. Are you taking any medications right now, including over-the-counter medicines or supplements?
- **user**: My husband gave me Sufra for it.
- **agent**: What is Sufra for, and who gave it to you?
    - tool `lookup_medication` {"spoken_name": "Sufra"}
- **user**: It's a cream for the burn, from the pharmacy.
- **agent**: Got it. What dose is it, and how often do you use it?
- **user**: No, nothing else. No allergies.
- **agent**: I just need to confirm: Sufra, a cream for the burn from the pharmacy. Is that right?
- **user**: No other conditions.
- **agent**: I hear you. To confirm: Sufra, a cream for the burn from the pharmacy. Is that right?
- **user**: No, that's everything.
- **agent**: I'll take that as confirmed. Are there any other medications, over-the-counter medicines, or supplements you take?
- **user**: Yes, that's right. Bye.
- **agent**: Thank you, Maria. The clinic can pick up the rest at your visit. Goodbye.
    - tool `record_intake` {"reason_for_visit": "burnt foot ironing clothes and it's being treated", "medications": [{"name": "Sufra", "dose": "", "frequency": "", "as_described": "a cream for the burn, from the pharmacy"}], "a
    - tool `end_call` {"reason": "Patient ended the call early"}

</details>

