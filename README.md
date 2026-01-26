# CS487-REFLEX (Recursive Epistemic Feedback LLM eXecutor)

REFLEX is an AI-assisted research system designed to produce more cautious, transparent, self-critical, and more detailed outputs than a standard single-prompt chatbot.

Rather than optimizing for speed or fluency, REFLEX optimizes for epistemic correctness by orchestrating a large language model through multiple structured reasoning stages, including self-critique and revision.

This project was built for CS$87, a Generative AI course with the explicit goal of using AI as the "primary development agent", while the human acts as a system designer, evaluator, and supervisor.

---

## Motivation

Single-prompt LLM responses often appear confident even when:
- assumptions are implicit or incorrect
- definitions are ambiguous
- counterarguments are ignored
- uncertainty is underreported

REFLEX addresses this by making assumptions explicit, forcing claims to be critiqued, and exposing where confidence may be unjustified.

The system intentionally trades latency and cost for epistemic caution

---

## System Overview

### Input
- A research directive, which may be:
  - a question  
  - an imperative (e.g., “Research all plausible theories of FTL”)  
  - a comparative or evaluative request  

### Output
- Structured research synthesis
- Explicit assumptions and definitions
- Identified weaknesses and counterarguments
- Confidence calibration
- Logged ambiguity resolutions

---

## Architecture

REFLEX uses a single AI model operating under multiple roles, coordinated by an API-based backend.

### Pipeline Stages

1. Intent Parser
   - Converts user input into a structured research brief
   - Extracts goals, scope, definitions, assumptions, and ambiguities

2. Decomposition Agent
   - Breaks the research brief into research dimensions or sub-problems

3. Claim Generator
   - Produces explicit, falsifiable claims with confidence estimates

4. Critic Agent
   - Adversarially challenges the claims
   - Identifies missing evidence, weak assumptions, and likely hallucinations

5. Revision Agent
   - Updates claims based on critique
   - Lowers confidence where uncertainty remains



