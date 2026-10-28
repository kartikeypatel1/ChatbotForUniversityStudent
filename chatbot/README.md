# AI-Powered Chatbot for University Student Support
HCLTech Career Shaper - Project 30. Python, scikit-learn, NLTK/VADER, SQLite, Streamlit.

## How it works
```
message -> PII scrub -> crisis / small-talk checks
        -> intent classifier (TF-IDF + Logistic Regression)  \  fused score decides the intent
        -> FAQ retrieval (word + char TF-IDF cosine)          /  and the FAQ topic
        -> sentiment (VADER) + escalation rules -> answer  OR  hand-off to a human agent
        -> log scrubbed text to SQLite (skipped if the student opted out)
```
Escalation reasons: `crisis`, `user_requested`, `negative_sentiment`, `low_confidence`.
The UI always shows a visible "Escalated to a human agent" banner with the reason.

## Setup (once)
```
python -m venv venv
venv\Scripts\activate          # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
```

## Run order
1. Put your project file at `data/dataset.csv` (columns: session_id, user_query, intent,
   confidence_score, bot_response, escalated, rating).
2. `python src/clean_and_eda.py` -> `data/dataset_clean.csv`, `report/data_dictionary.csv`,
   `report/cleaning_log.txt`, `report/figures/eda_*.png`  (or run `notebooks/eda.ipynb`).
3. `python src/train.py` (add `--use-chatlog` to also learn from your chat log; intent names must match the
   FAQ categories - the script prints any that don't).
4. `python src/evaluate.py` -> `report/metrics.json`, `report/errors.csv`, confusion matrix.
5. `streamlit run src/app.py` -> the chatbot (use this for the demo video).

## Before you submit - checklist
- [ ] Edit `HELPDESK_CONTACT` and `CRISIS_RESOURCES` in `src/nlp.py` with real contacts (they are placeholders).
- [ ] Write **your own** test queries in `data/test_queries.csv` (100+ in your own words). The 75 provided are only a
      starter set, and I added a few synonyms (`SYNONYMS` in `nlp.py`) after seeing which of them failed, so the
      numbers on that file are optimistic. Report results on queries you wrote **after** freezing the code.
- [ ] Tune `FUSED_MIN`, `W_RETR`, `SENT_MIN` in `src/nlp.py` on one set of queries, then report on another.
- [ ] The FAQ answers are generic template text. State that in the report; real use needs the university's own policies.
- [ ] Keep the ethics features: PII scrubbing, opt-out, delete-my-data button, visible escalation banner.
- [ ] Sign the Ethical Compliance Declaration; add the demo video and the 8+ page report.

## Report outline (8+ pages)
1. Problem and objectives  2. Data and EDA (the 5 figures + data dictionary + cleaning log)
3. Architecture (diagram above)  4. Implementation of each module  5. Evaluation: intent accuracy / macro-F1
(classifier-only vs fused), retrieval top-1/top-3, escalation precision/recall, latency, confusion matrix, error analysis
from `report/errors.csv`  6. Ethics and privacy  7. Limitations and future work  8. Conclusion

## Demo script (1-2 minutes)
Normal question -> question with an audience ("as an international student ...") -> message containing a phone number
(show it masked in the Agent view) -> angry message (escalation banner) -> "I want a human" -> opt-out checkbox ->
delete-my-data button.

## Known limitations (write these in your report)
- PII scrubbing is regex-based: it catches emails, phone numbers and long ID numbers, **not names or addresses**.
- Crisis detection is a keyword list and can miss indirect wording; a real deployment needs clinical review.
- VADER is rule-based and English-only; a few domain words were added to its lexicon.
- Intent training data is template-generated, so it is much cleaner than real student messages.
- Only English is supported; no real agent system exists - the Agent view is a demo.
