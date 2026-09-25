# Failures

## medication_not_understood run 3
- **E9_case_rules**: forbidden phrasing /what dose/ at index 8: 'Got it. For Sufra cream for the burn, what dose do you use, and how often do you'; forbidden phrasing /what dose/ at index 10: 'I heard no other medications and no allergies. For the Sufra cream, I still need'; forbidden phrasing /how often do you (take|apply|use)/ at index 8: 'Got it. For Sufra cream for the burn, what dose do you use, and how often do you'; forbidden phrasing /how often do you (take|apply|use)/ at index 10: 'I heard no other medications and no allergies. For the Sufra cream, I still need'

<details><summary>transcript</summary>

- **agent**: Hi, this is the automated intake assistant calling from Northside Family Practice. Am I speaking with Maria?
- **user**: Yes, this is Maria.
- **agent**: Thank you, Maria. I see you have an appointment with Dr. Chen on Friday at ten thirty. Before your visit, I'd like to collect some information. What is the main reason for your appointment?
    - tool `confirm_patient` {"answered_by": "patient"}
- **user**: I burnt my foot ironing my clothes and it's being treated.
- **agent**: Got it, Maria. While that's being treated, what medications are you currently taking, including anything over-the-counter or supplements?
- **user**: My husband gave me Sufra for it.
- **agent**: What is Sufra for, and who gave it to you?
    - tool `lookup_medication` {"spoken_name": "Sufra"}
- **user**: It's a cream for the burn, from the pharmacy.
- **agent**: Got it. For Sufra cream for the burn, what dose do you use, and how often do you apply it?
- **user**: No, nothing else. No allergies.
- **agent**: I heard no other medications and no allergies. For the Sufra cream, I still need to know: what dose and how often do you apply it?
- **user**: No other conditions.
- **agent**: That's fine. For the Sufra cream, if you don't know the dose or how often, I can record it as unknown. Is that okay?
- **user**: No, that's everything.
- **agent**: Understood. Let me read back what I have so far, Maria. Your reason for the visit is a burnt foot from ironing that is being treated. Your medication is Sufra cream for the burn, from the pharmacy, with dose and frequency unknown. You have no allergies and no other conditions or history. Is anything missing or wrong?
- **user**: Yes, that's right. Bye.
- **agent**: Thank you, Maria. Dr. Chen will have this before your visit on Friday. Please call the clinic if anything changes. Goodbye.
    - tool `record_intake` {"reason_for_visit": "burnt foot ironing clothes and it's being treated", "medications": [{"name": "Sufra", "dose": "", "frequency": "", "as_described": "a cream for the burn, from the pharmacy"}], "a
    - tool `end_call` {"reason": "Patient confirmed readback and ended call"}

</details>

## medication_not_understood run 7
- **E9_case_rules**: forbidden phrasing /what dose/ at index 8: "Got it. So that's Sufra, a cream for the burn from the pharmacy. What dose do yo"; forbidden phrasing /what dose/ at index 10: "Got it. So that's Sufra, a cream for the burn from the pharmacy. What dose do yo"; forbidden phrasing /how often do you (take|apply|use)/ at index 8: "Got it. So that's Sufra, a cream for the burn from the pharmacy. What dose do yo"; forbidden phrasing /how often do you (take|apply|use)/ at index 10: "Got it. So that's Sufra, a cream for the burn from the pharmacy. What dose do yo"

<details><summary>transcript</summary>

- **agent**: Hi, this is the automated intake assistant calling from Northside Family Practice. Am I speaking with Maria?
- **user**: Yes, this is Maria.
- **agent**: Great, Maria. I have a few questions for Dr. Chen before your Friday appointment at ten thirty. What's the main reason for your visit?
    - tool `confirm_patient` {"answered_by": "patient"}
- **user**: I burnt my foot ironing my clothes and it's being treated.
- **agent**: Got it, Maria. Are you taking any medications right now, including over-the-counter medicines or supplements?
- **user**: My husband gave me Sufra for it.
- **agent**: What is Sufra for, and who gave it to you?
    - tool `lookup_medication` {"spoken_name": "Sufra"}
- **user**: It's a cream for the burn, from the pharmacy.
- **agent**: Got it. So that's Sufra, a cream for the burn from the pharmacy. What dose do you use, and how often do you apply it?
- **user**: No, nothing else. No allergies.
- **agent**: Got it. So that's Sufra, a cream for the burn from the pharmacy. What dose do you use, and how often do you apply it?
- **user**: No other conditions.
- **agent**: Maria, I want to make sure I have this right. You have Sufra, a cream for the burn from the pharmacy. I didn't catch the dose or how often you use it. Could you tell me that?
- **user**: No, that's everything.
- **agent**: I still need the dose and how often for Sufra. If you don't know, that's fine. What would you say?
- **user**: Yes, that's right. Bye.
- **agent**: Thank you, Maria. The clinic can pick up the rest at your visit on Friday. Goodbye.
    - tool `record_intake` {"reason_for_visit": "burnt foot ironing clothes and it's being treated", "medications": [{"name": "Sufra", "dose": "", "frequency": "", "as_described": "a cream for the burn, from the pharmacy"}], "a
    - tool `end_call` {"reason": "Patient ended the call early"}

</details>

