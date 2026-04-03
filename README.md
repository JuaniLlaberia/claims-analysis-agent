# Claims Analysis Workflow

`claims-analysis-agent` is a Flask-based microservice for fact-checking and citation verification of textual claims.  
It works on short text snippets, extracts claims with an LLM, validates via Google Fact Check and web search, and returns structured evidence + coverage.

---

## API Endpoints

### `GET /health`

- Purpose: health check
- Response: `{ "status": "healthy" }`

### `POST /snippet`

- Purpose: core analysis endpoint
- Input JSON:
  - `snippet`: string (length < 500)
- Workflow:
  1. `SnippetAnalyzer` uses Gemini LLM model `GEMINI_MODEL_SNIPPET_EXTRACTION` to identify and normalize claims.
  2. `Orquestrator` sends each claim through `Validator`.
  3. `Validator`:
     - checks Google Fact Check API (`GOOGLE_FACTCHECK_API_KEY`)
     - falls back to Tavily web search (`TAVILY_API_KEY`)
     - then ground-truths with Gemini LLM
  4. Output includes claims list with evidence summary, coverage data, citations, and `insufficient_evidence` flag.
- Response:
  - `200`: `{ "results": [ ... analyzed claims ... ] }`
  - `400`: missing JSON or missing/long snippet
  - `500`: analysis failure

---

## Required ENV vars

`src/__main__.py` enforces these env vars:

- `GOOGLE_GEMINI_KEY`
- `GEMINI_MODEL_SNIPPET_EXTRACTION`
- `GEMINI_MODEL_VALIDATION`
- `GOOGLE_FACTCHECK_API_KEY`
- `TAVILY_API_KEY`
- `PORT`

Optional helpful setup:

- `.env` file via `python-dotenv` (already loaded by `load_dotenv()` in `__main__.py`)

---

## Run locally

1. `python -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. Set env vars or `.env`
4. `python __main__.py`
5. Service defaults to `http://localhost:5001`

---

## Notes

- The analysis is snippet-based only (route is `/snippet`).
- The app currently does `app.run(..., port=5001)` in code.
- Validate step ensures missing env fails fast with helpful error message.

---

## Future Work

- Handle full-length article claims analysis with chunking and parallel analysis.
