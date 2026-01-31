# CS487-REFLEX (Recursive Epistemic Feedback LLM eXecutor)

REFLEX is an AI-assisted research system designed to produce more cautious, transparent, self-critical, and more detailed outputs than a standard single-prompt chatbot.

Rather than optimizing for speed or fluency, REFLEX optimizes for epistemic correctness by orchestrating a large language model through multiple structured reasoning stages, including self-critique and revision.

This project was built for CS487, a Generative AI course with the explicit goal of using AI as the "primary development agent", while the human acts as a system designer, evaluator, and supervisor.

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

## Core Concept

Standard LLM interactions are "one-shot": you ask, and the model predicts the most likely next tokens. This often hides uncertainty and hallucinations behind polished prose.

REFLEX trades speed for honesty. It breaks the "black box" into six observable stages:

1. **Intent Parsing:** Converting vague queries into strict research directives.
2. **Decomposition:** Breaking the problem into orthogonal search dimensions.
3. **Claim Generation:** Producing falsifiable hypotheses with confidence scores.
4. **Adversarial Critique:** A distinct "Critic Agent" attempts to falsify the claims.
5. **Revision:** Synthesizing critique into a more epistemically sound verdict.
6. **Evaluation:** Assigning a final reliability score to the run.

---

# Installation Guide

### Prerequisites

- Python 3.10+
- A Google AI Studio API Key (Get one [here](https://aistudio.google.com/))

### 1. Clone & Setup

```bash
git clone https://github.com/lavendevo/CS487-REFLEX.git
cd reflex
```

### 2. Backend Installation
```bash
# Create and activate virtual env
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install fastapi uvicorn pydantic python-dotenv google-genai
```

### 3. Configure API Key
You must set your Google API Key as an environment variable (don't ever hardcode your API key) by running either of the following:
#### Mac/Linux
```bash
export GEMINI_API_KEY="YOUR_KEY_HERE"
```

### 4. Run the System
#### Terminal 1: Start Backend
```bash
# Must be run from the REFLEX/ directory (not frontend or backend)
uvicorn backend.main:app --reload
```
You should see: Uvicorn running on http://127.0.0.1:8000

#### Terminal 2: Launch the Frontend
Since the frontend is vanilla HTML/JS, you can often just double-click frontend/index.html. **However**, for the smoothest experience issue-free, it is recommended to do the following:
```bash
cd frontend
python -m http.server 5173
```
Then open your browser to: http://localhost:5173

## Usage Guide
**Initialize Run:** Enter a complex research question (e.g., "Assess the viability of space-based solar power by 2040"). The "Consumer Baseline" button is a typical chat bot response for comparison whereas the six stages below it are the actual components of REFLEX. Please note that it is advised you take things slowly and do not rush running stages as to avoid a 429 error as REFLEX can be demanding on context and token usage.

## Known Issues
**Error: 429 RESOURCE_EXHAUSTED (Rate Limiting)**
The system relies on the Google Gemini Free Tier. If you run many stages in rapid succession, you may hit the requests-per-minute limit.
- Fix: It is recommended to wait 30-60 seconds after each stage. If you hit a 429 error, refresh the page and try again. 

**Scope Sprawl & Context Exhaustion**
Open-ended questions on topics with great contention (e.g., *"Does social media meaningfully increase political polarization?"*) can cause the Decomposition stage to generate too many search dimensions. This creates a massive amount of text in the downstream Claims and Critique stages, potentially exceeding the model's output token limit or causing timeouts.
- Fix: Keep directives in the initial specific (e.g., "Analyze the economic feasibility of X" rather than "Tell me about X") seems to reduce this issue. Alternatively, changing the model to something more advanced in engine.py may also solve this issue.

**Error: NetworkError / Failed to fetch**
This usually means the backend isn't running or CORS is blocking the request.
- Fix: Ensure uvicorn is running in Terminal 1 and that you are accessing the frontend via localhost:5173.
