# 0002: Claude for every agent
Decision: all agents use Claude (Haiku for volume, Sonnet for planning and checking, Opus for fixes). Gemini is dropped.
Why: keep business data away from a free tier that may be used to improve another company's products; simpler setup.
Trade-offs: the Reviewer shares blind spots with the agents it checks, and the Claude API costs money.
Mitigations: fresh-context adversarial Reviewer, scripts (not AI) for margin and budget maths, owner approval, manual mode on a Claude plan until the API is worth it.
