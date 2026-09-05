# SecondChance

SecondChance is an ML-assisted revenue-recovery decision engine, not an LLM chatbot.
For each failed payment it estimates `P(success | observable transaction, candidate action)`,
calculates expected recovered value minus customer-friction cost, and applies deterministic
safety guardrails before returning a recommendation.

The prototype trains on reproducible synthetic historical examples. Run the explicit training
command from `backend`: `python -m app.ml.train`. The runtime never trains; if the generated
model artifact is unavailable it uses the deterministic intelligence fallback. In production,
failed-payment events would arrive from a payment-provider webhook. The bundled simulation truth
is backend-only evaluation data and is never sent through the API or frontend.
