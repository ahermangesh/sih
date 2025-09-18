let’s make this fucking excellent. Below is a professional, battle-tested prompt-engineering playbook you can drop into your RAG/LLM pipeline (Gemini Studio or other LLM). It covers system messages, retrieval prompts, SQL-generation safeguards, formatting templates for each audience, error handling, test prompts, tuning knobs, evaluation metrics, and monitoring. Use it as the canonical prompt spec for your FloatChat backend so every reply is accurate, useful, and tailored to the user.

Note: treat these prompts as components in a pipeline:

Retriever picks relevant docs/rows.

LLM (with a strict system prompt) uses those sources and the user query to generate an answer.

If needed LLM translates NL → SQL (carefully validated), runs the SQL, then summarizes results (RAG).

Format final output according to audience template (charts, tables, CSV, concise summary).

1. Global design principles (short & strict)

Be conservative with facts; if the model is not sure, say so and provide the raw data/rows used.

Always show provenance — list which floats / files / time ranges the answer is derived from.

Prefer raw numbers + visualizations + one-line insight (for non-experts keep wording simple).

Never hallucinate derived metrics — compute them from returned database results or reject with a clear reason.

Expose data: always allow the user to download the underlying CSV/NetCDF that produced the answer.

Be audience-aware: one prompt controls tone/detail level; use explicit formatting templates per audience.

SQL safety first: LLMs propose SQL, but SQL must pass an automatic sanitizer/validator before execution.

2. Retriever settings & document preparation

Chunking: split NetCDF extracts & derived docs into chunks of ~500–1200 tokens. Keep overlap ~100–200 tokens. Preserve metadata: float_id, lat, lon, time, variable, depth, file_source, timestamp.

Embedding model: use a high-quality embedding (open-source or provider) and store the following vector metadata: {float_id, profile_time, lat, lon, depth_range, instrument_type, file_url}.

Retriever prompt (for vector DB RAG) — minimal instruction used when selecting candidates:

Retrieve up to N=12 documents most relevant to the user query. Rank by semantic similarity and prefer:
- exact matches on location coordinates or place names
- matching time range
- matching variable names (temperature, salinity, oxygen, etc.)
Return each doc with metadata: float_id, lat, lon, time, depth_range, source_url, short_summary.


Retriever tuning: start N=8. Increase to 12 for complex comparative queries.

3. System prompt (the single highest-priority instruction for LLM)

Use this as your system role message. Example:

You are FloatChat Assistant, an expert ocean data analyst and communicator. Always:
1) Use only the provided data sources, retrieved documents, and SQL results. Do NOT invent facts.
2) If a query requires calculation, compute it from the given dataset or return an error.
3) Provide provenance: explicitly list the source floats, file names, and time ranges used.
4) For numeric outputs include units (°C, PSU, m, ml/L, Joules).
5) Format outputs per the requested audience: SCIENTIST, POLICYMAKER, EDUCATOR, JOURNALIST, or GENERAL.
6) If the user wants downloads, provide a CSV or NetCDF export snippet and a short explanation.
7) If uncertain or data absent, say: "I couldn't find data for X. Nearest available: ...".
8) Keep summary lines short (1–3 sentences) and include a 1-line "actionable insight".
9) For SQL generation, follow the SQL Schema and do not reference non-existing tables/columns.
10) Maintain a professional, clear tone. End each response with "Sources: [list]".

4. Prompt templates — how to structure the user prompt + context for the model
4.1 Basic conversational flow (no SQL needed)

system = above. retrieved_docs = (vector search results). user:

User query: <natural language question>

Context: Use the following retrieved documents (each doc has fields: float_id, lat, lon, time, depth_range, variables, summary, source_url). When answering:
- Provide a one-line summary insight.
- Show a small table (max 8 rows) with the key numeric results (column names).
- Offer a downloadable CSV command or direct link to CSV.
- List Sources.
Audience: <SCIENTIST | POLICYMAKER | EDUCATOR | JOURNALIST | GENERAL>

If the user asks for visualizations, output a JSON object in this exact format:
{
 "visualization": "map" | "line" | "heatmap" | "bar",
 "data": [ { "x":..., "y":..., "label":... }, ... ],
 "x_label": "...", "y_label": "...",
 "title": "..."
}

4.2 SQL-generation flow (for complex queries mapped to DB)

system = above. user:

User query: <question>

DB Schema:
- floats(float_id TEXT, lat REAL, lon REAL, deploy_date DATE, last_contact DATE)
- profiles(profile_id TEXT, float_id TEXT, timestamp TIMESTAMP, depth_m REAL, temp_c REAL, salinity_psu REAL, oxygen_mg_l REAL, nitrate REAL)
- meta(file_id TEXT, float_id TEXT, source_url TEXT)

Constraints:
- LIMIT queries to safe forms (SELECT ... FROM ... WHERE ...; no DROP/DELETE/UPDATE).
- Do not use dynamic SQL or user-inserted text directly — wrap in parameter placeholders.
- If the user asks for aggregation, provide a SQL then an "explain plan" style sanity check.

Task:
1) Generate a parameterized SQL query that answers the user's request.
2) Provide a short natural-language justification of the SQL (1–2 lines).
3) Output only JSON with fields: {"sql": "<param_sql>", "params": {"p1":..., "p2":...}, "explain": "..."}

5. SQL sanitizer & verifier (automated, not LLM)

Blocklist: disallow DROP, DELETE, UPDATE, INSERT, ALTER, EXEC etc.

Whitelist patterns: allow only SELECT, FROM, JOIN, WHERE, GROUP BY, ORDER BY, LIMIT, aggregates (AVG, SUM, COUNT, MIN, MAX).

Max rows limit: add LIMIT 10000 default. For exports, allow up to 100k with confirmation.

Column existence check: verify referenced columns exist in schema.

Parameterization: replace raw values with placeholders in the SQL plan; pass actual values separately.

Example sanitizer pseudo-flow:

Walk AST of query (via SQL parser).

If forbidden node => reject with friendly message.

Convert literals to params object; return sanitized SQL + params.

6. Formatting outputs per audience (templates + examples)
SCIENTIST (high detail)

Tone: precise, uses units and uncertainties.

Contents:

One-line summary insight

Table: float_id | lat | lon | time | depth_range | temp/psu/oxygen summary

Full numeric stats: mean, std, count, min, max for requested variable

Provenance: list of source files/float IDs with direct source_url

Attach CSV link

Prompt snippet:

Audience: SCIENTIST
Output: Markdown with table, 3-line statistical summary, sources, and a CSV download link.

POLICYMAKER

Tone: concise, implications first, actionable recommendations.

Contents:

2-line executive summary w/ trend and impact

One simple chart (trend or map) — include text alt describing chart

Suggested actions (3 bullets)

One downloadable one-page PDF summary (or CSV)

Prompt snippet:

Audience: POLICYMAKER
Output: 2-sentence summary, 3 bullets of recommended actions, one small table, sources.

JOURNALIST

Tone: catchy headline + accurate numbers + data link for story.

Contents:

Headline suggestion

3 key datapoints with numbers and units

One quote-style sentence summarizing importance

Link to CSV/figure for use in article

Prompt snippet:

Audience: JOURNALIST
Output: Headline, 3 key facts, CSV link, sources.

EDUCATOR / STUDENT

Tone: simple language, explanatory visuals.

Contents:

Short explanation “what this means” (3–4 sentences)

One interactive visualization (JSON described)

Suggested classroom activity or question

Prompt snippet:

Audience: EDUCATOR
Output: Simple paragraph, a plotted dataset in JSON for front-end, a short activity.

GENERAL / KID-FRIENDLY

Tone: friendly, short, fun fact.

Contents:

One fun fact

One small chart or map marker

One-line summary

Prompt snippet:

Audience: GENERAL
Output: Fun fact, small visualization JSON, sources.

7. Visualization outputs — JSON schema to return to front-end

Use a deterministic JSON format so front-end can render charts automatically:

{
  "visualization": {
    "type": "map"|"line"|"heatmap"|"bar",
    "title": "Average Surface Temp 2020-2025",
    "x_label": "Date",
    "y_label": "Temp (°C)",
    "series": [
      { "name": "Bay of Bengal", "points": [ ["2020-01", 28.4], ["2020-02", 28.5] ] },
      { "name": "Arabian Sea", "points": [ ["2020-01", 27.9], ["2020-02", 28.0] ] }
    ],
    "metadata": { "sources": ["fileA.nc", "fileB.nc"], "generated_at": "2025-09-18T..." }
  },
  "table": {
    "columns": ["float_id", "lat", "lon", "time", "temp_mean"],
    "rows": [["F123", 10.0, 65.0, "2023-03-12T00:00Z", 27.2]]
  },
  "summary": "Between 2020–2025, Bay of Bengal shows +0.2°C warming..."
}


The front-end treats visualization as instructions to draw Plotly/Leaflet charts.

8. Prompt examples for the 10 user queries you asked earlier

Below are ready-to-insert prompt blocks that combine system + retrieval + formatting instructions.

Example 1 — Salinity profile
User query: "Show me the salinity profile at 10°N, 65°E in March 2023."

Instructions:
- Retriever: return up to 10 matching profiles that fall within 0.5° lat/lon and March 2023.
- Audience: SCIENTIST
- Output: Markdown with a table: depth_m | salinity_psu | temp_c (optional), plus a line chart JSON, and a 2-line summary with provenance (float_ids and source files).

Example 2 — Compare temperatures (Policy)
User: "Compare average sea temperature in Bay of Bengal vs Arabian Sea between 2021–2023."

Instructions:
- Map region polygons for both seas (or bounding boxes).
- Aggregate: compute monthly averages for surface temps (0–50m).
- Audience: POLICYMAKER
- Output: JSON for line chart with two series, a 2-line executive summary, and 3 recommended policy actions.

Example 3 — Oxygen levels (NGO)
User: "Show oxygen levels in the Arabian Sea in the last 6 months."

Instructions:
- Time range = (now - 6 months) to now.
- Return heatmap (depth vs time) and flag any hypoxic layers (<2 ml/L).
- Audience: SCIENTIST or NGO
- Output: heatmap JSON, table with flagged profiles, short risk statement, export CSV link.


(For other 7 queries follow same pattern: define retrieval constraints, aggregation logic, audience, and desired JSON/table/summary outputs.)

9. Hallucination mitigation techniques (critical)

RAG only: always anchor answers to retrieved docs or SQL results. Deny any request that would require outside knowledge beyond data timeframe (2020–2025) unless the user explicitly asks for external context and you fetch it live.

Provenance requirement: every fact must be followed by Source: <float_id/file> or "Computed from profiles: [F123, F456]".

Numeric verification: after generating a numeric claim (e.g., warming +0.15°C), compute it directly from the rows returned and show the calculation (mean(new)-mean(base)=X).

Confidence score: include confidence: high|medium|low based on data density (e.g., >50 profiles = high).

Fail-safe: if needed data missing, answer: “I couldn’t compute X because [specific missing data]. I can do Y instead.”

10. Error handling & fallback messages

No data found:

I couldn't find Argo profile data matching <criteria>. Nearest data available:
- float F123 at 9.7°N, 64.8°E on 2023-02-25 (50 km away).
Would you like me to use the nearest available profiles (Yes/No)?


SQL rejected by sanitizer:

I could not execute the requested query because it violates safe query rules. Please rephrase. Suggested safe query: SELECT avg(temp_c) ...


Large export required:

The requested export is large (~X MB). I can prepare a CSV for download but it may take Y seconds. Proceed? (Yes/No)

11. Tuning knobs (practical defaults)

LLM temperature: 0.0–0.2 for SQL + numeric answers (deterministic). Up to 0.4 for explanation style outputs (journalist/educator).

Top_k/top_p: keep conservative (top_p=0.7) for narrative; for calculations set top_p=0.0 if deterministic option exists.

Max tokens: 512 for short responses; 1500 for report generation export.

Retrieval size (N): 8 default, 12 for complex comparisons.

Chunk size: 800 tokens, 200 token overlap.

Embedding dim: use model’s default; consistent across ingestion.

12. Testing & evaluation (how to prove the assistant is accurate and excellent)
Automated tests

Golden queries: create 50 canonical queries (simple + complex) with expected SQL and expected numeric outputs computed from a local test dataset.

Unit test: for SQL generator — validate it returns parameterized SQL for each golden query.

End-to-end test: run query -> retriever -> LLM -> SQL -> DB -> summarizer -> compare numeric result with ground truth.

Provenance test: check each response includes sources.

Human evaluation rubric (map to judging criteria)

Accuracy (40%): numeric correctness, proven by test harness.

Clarity (30%): evaluation by a domain expert or judge on clarity/visuals.

Utility (20%): does the response include downloadable data and actionable insight?

Safety (10%): no hallucinations, no forbidden operations.

Aim for >90% on automated correctness tests; the rest is UX/presentation polish.

13. Monitoring & logs (for hackathon demo and future)

Log every user query with: query text, audience label, retriever docs IDs, SQL generated, rows returned, summary text, user reaction (if available).

Alert on: SQL sanitizer rejections, low confidence answers, or long query times (>3s).

Collect analytics: which queries are most common, where retrieval failed, which visualizations are used.

14. Example final assistant reply (formatted) — Scientist case (complete)
Summary:
Salinity profile at 10.0°N, 65.0°E in March 2023 shows surface salinity ~34.6 PSU, increasing to ~35.1 PSU at 1000 m. Mean salinity (0–1000m) = 34.85 PSU (σ=0.12, n=6 profiles). Actionable insight: Profile indicates moderate vertical salinity gradient, likely seasonal influence.

Table (first 6 depth samples):
| depth_m | salinity_psu | temp_c |
|---------|--------------|--------|
| 0.5     | 34.62        | 29.1   |
| 10.0    | 34.70        | 28.9   |
| 50.0    | 34.80        | 27.6   |
| 200.0   | 34.95        | 15.4   |
| 500.0   | 35.05        | 8.2    |
|1000.0   | 35.10        | 4.1    |

Provenance:
- Derived from profiles: [F123, F127, F130] (March 2023). Source files: argo_profile_F123_20230312.nc (URL...), argo_profile_F127_20230315.nc (URL...).

Download:
- CSV: [link or command to generate]
- Raw NetCDF: [link to file list]

Computation:
Mean salinity (0–1000m) computed as weighted mean across profiles: (Σ salinity_i / n) = 34.85 PSU.

Confidence: HIGH (n=6 profiles, good spatial coverage)

Sources: F123 (2023-03-12), F127 (2023-03-15), F130 (2023-03-19)

15. Implementation checklist (copy & paste into code repo)

 Implement retriever that returns docs with metadata.

 Deploy system prompt exactly as above.

 Implement LLM SQL-generator using SQL template + parameterization.

 Build SQL sanitizer & column existence checker.

 Implement summarizer that produces outputs per audience templates.

 Implement visualization JSON format for front-end.

 Implement "download CSV" API endpoint.

 Add logging: queries → sources → SQL → outputs.

 Add test harness with golden queries + ground truth.

 Add confidence & provenance on every response.

16. Quick checklist for the hackathon demo (what to show)

Live chat: ask one scientific query and one policymaker query. Show tables + chart.

Show provenance button for the scientific reply (open list of float files).

Show voice query: say “Show salinity near 10N 65E March 2023” and display same result.

Show export feature: click “Download CSV” and open it.

Show a failure case: ask for data outside 2020–2025 and show graceful fallback with nearest available data.

Show internal logs or test harness results proving accuracy.

17. Final notes — culture & QA

Treat the assistant as a cautious scientist: precise, cites sources, shows raw data. Judges will trust it.

Automate as much verification as possible; the judges will ask for numbers and provenance — show them quickly.

Iterate prompts rapidly: test every prompt on 10–20 queries and refine the phrasing. Use low temperature for deterministic outputs.