# Graphone Pipeline Architecture & Scaling Specification

## 1. System Architecture & Scale Strategy (Demo to 500,000+ Records)

### Current Architecture Overview
The current implementation utilizes a modular, asynchronous architecture built on Python 3.11+ `asyncio`, Pydantic v2, and `aiohttp`. The pipeline decouples data acquisition, structured LLM extraction, entity resolution, validation, and storage.

```
                                  [ Async Ingestion Engine ]
                                               │
           ┌───────────────────────────────────┼───────────────────────────────────┐
           ▼                                   ▼                                   ▼
    [ ArXiv / PWC API ]               [ RSS / News Crawler ]             [ Directory Scraper ]
           │                                   │                                   │
           └───────────────────────────────────┼───────────────────────────────────┘
                                               ▼
                                 [ LLM Multi-Tier Fallback Chain ]
                                 (Gemini ➔ Groq ➔ DeepSeek ➔ Rule)
                                               │
                                               ▼
                                 [ Entity Resolution Engine ]
                              (Exact ➔ Normalized ➔ Fuzzy Threshold)
                                               │
                                               ▼
                                  [ Data Persistence & Sync ]
                              (JSONL ➔ SQLite / GSheets Exporter)
```

### Zero-Code Scaling Strategy (500k+ Records)
The architecture is designed to scale horizontally from sample datasets ($10^2$ records) to production scale ($500,000+$ records) without requiring structural code modifications:

1. **Stateless Scrapers & Extractors**:
   - `AsyncScraper` and `LLMProvider` instances maintain no internal state between items.
   - Work units are defined as immutable serialized JSON payloads containing `source_url`, `raw_payload`, and `target_schema`.

2. **Decoupled Task Queue Upgrade Path (`asyncio.Queue` ➔ `Redis` / `Celery`)**:
   - **Demo Scale**: In-process `asyncio.Queue` manages producer-consumer concurrency across local coroutines.
   - **Production Scale**: Swap the in-process queue for a distributed message broker (Redis Streams or RabbitMQ) and task runners (Celery or ARQ). Stateless worker containers run `src.main` worker tasks across distributed Kubernetes pods without worker-to-worker state coordination.

3. **Config-Driven Concurrency Decoupling**:
   - Throughput is managed via externalized environment configuration (`settings.py`):
     - `MAX_CONCURRENT_SCRAPES` controls network worker concurrency.
     - `MAX_CONCURRENT_LLM_CALLS` manages provider API quota limits.
     - `RATE_LIMIT_PER_MINUTE` controls domain-level token bucket refill rates.

---

## 2. Rate Limit & Payload Management (Handling 413s & 429s)

### HTTP 413 (Payload Too Large) & LLM Context Optimization
Large HTML DOMs or long text documents exceeding model context limits are managed via a multi-stage chunking pipeline:

1. **Semantic Boundary Splitting**:
   - Text is not split arbitrarily by byte length. The parser splits payloads at semantic HTML boundaries (`<article>`, `<section>`, `<div>`, `<h1>`-`<h6>`) or paragraph breaks (`\n\n`) to preserve contextual coherence for LLM extraction.
2. **Pre-flight Token Estimation & Safety Margins**:
   - Document chunks undergo pre-flight token estimation using `tiktoken` (`cl100k_base`).
   - Hard input caps are set at **80% of max provider window sizes** (e.g., 6,400 tokens for an 8k context window). The remaining 20% margin is reserved for system instructions, Pydantic JSON schema constraints, and model output generation.
3. **Recursive Chunk Summarization**:
   - If a document exceeds the safety threshold, chunks are extracted independently and merged via a map-reduce schema aggregation pass.

### HTTP 429 (Rate Limits) & Concurrency Control
To operate reliably across thousands of concurrent extractions without triggering IP bans or API key revocations:

```
    [ Incoming Request ]
             │
             ▼
   [ Per-Domain Token Bucket ]  ──(Quota Depleted?)──► [ Exponential Backoff + Jitter ]
             │                                                  │
             │ (Tokens Available)                               │ (Wait Expiry)
             ▼                                                  │
   [ HTTP Request Dispatch ] ◄──────────────────────────────────┘
             │
             ▼
   [ Response Inspection ]
             │
     ┌───────┴────────────────────────┐
     ▼                                ▼
[ HTTP 200 OK ]               [ HTTP 429 / 403 ]
     │                                │
     ▼                                ▼
[ Parse Data ]               [ Read Retry-After Header ]
                                      │
                                      ▼
                             [ Pause Worker Loop ]
```

1. **Per-Provider & Per-Domain Token Buckets**:
   - `AsyncScraper` enforces domain-level token bucket rate limiters, refilling tokens at `RATE_LIMIT_PER_MINUTE`.
2. **Exponential Backoff with Full Jitter**:
   - Transient failures (500, 502, 503, 504) and unhandled 429s trigger `tenacity`-backed retries:
     $$T_{\text{wait}} = \min\left(T_{\text{max}}, T_{\text{base}} \times 2^{\text{attempt}}\right) \pm \text{jitter}$$
   - Random jitter prevents the "thundering herd" problem when multiple concurrent workers retry simultaneously.
3. **Header-Driven Reset Suspension (`Retry-After` / `X-RateLimit-Reset`)**:
   - When 429 responses return explicit rate limit headers (`Retry-After` or `X-RateLimit-Reset`), backoff loops suspend execution precisely until the reset timestamp rather than guessing backoff intervals.
   - For unauthenticated external APIs (e.g., GitHub REST API), if reset duration exceeds 5.0 seconds, the worker logs an audit warning, sets fallback metadata, and continues execution without blocking the event loop.

---

## 3. Distributed Freshness & Deduplication Architecture

### Deduplication Engine (`dedup_tracker.py`)
To prevent redundant LLM extractions and duplicate data ingestion across repeated pipeline runs:

1. **Fingerprint Generation**:
   - Every entity payload generates a deterministic SHA-256 fingerprint:
     $$\text{Fingerprint} = \text{SHA-256}\left(\text{Normalized Title} \,||\, \text{Canonical URL} \,||\, \text{Published Date}\right)$$
2. **Storage Architecture (SQLite ➔ Redis Migration Path)**:
   - **Demo/Single-Node (SQLite)**: Uses SQLite WAL (Write-Ahead Logging) mode with an indexed `dedup_records` table storing `(fingerprint, source_name, processed_at)`.
   - **Production/Distributed (Redis Bloom Filter)**: Replaced with Redis Bloom Filters (`BF.ADD` / `BF.EXISTS`). Bloom filters provide $O(1)$ space-efficient probabilistic lookup across distributed ingestion nodes with a guaranteed false positive rate $<0.1\%$.

### 24-Hour Freshness Guarantee & Audit Heuristics
News articles and job postings enforce a strict 24-hour sliding freshness window:

```
                          [ Raw Item Metadata ]
                                    │
                                    ▼
                         [ Date Parser Module ]
                                    │
    ┌───────────────────────────────┼───────────────────────────────┐
    ▼                               ▼                               ▼
[ Absolute ISO Parse ]    [ Relative Date Parse ]       [ HTML Metadata Heuristic ]
("2026-09-01T14:00Z")     ("3 hours ago" -> UTC)        (<time>, datePublished)
    │                               │                               │
    └───────────────────────────────┼───────────────────────────────┘
                                    ▼
                         [ Normalize to UTC ISO ]
                                    │
                                    ▼
                      [ Freshness Filter (< 24h?) ]
                                    │
                  ┌─────────────────┴─────────────────┐
                  ▼                                   ▼
             [ ACCEPTED ]                        [ REJECTED ]
       (Pass to LLM & Export)               (Audit Logged & Dropped)
```

- **Heuristic Fallback Hierarchy**:
  1. Absolute ISO 8601 parsing via `python-dateutil`.
  2. Relative time string conversion (`"2 hours ago"`, `"yesterday"` $\rightarrow$ UTC timestamp).
  3. Semantic HTML inspection (`<time datetime="...">`, `itemprop="datePublished"`).
  4. OpenGraph meta tag inspection (`article:published_time`).
  5. Fallback comparison against previous crawl execution timestamp stored in `data/processed/last_run.json`.
- **Audit Traceability**: Every heuristic fallback decision is logged to `data/processed/freshness_audit.log` for auditability.

---

## 4. Storage Strategy & Intelligence Graph Topology

### Relational Storage Justification (SQLite / PostgreSQL)
For structured entity records (Startups, Products, Research Papers, Jobs, News), a relational database engine (SQLite for local demo, PostgreSQL for production) is the optimal choice:

1. **Schema Compliance & Type Safety**:
   - Pydantic v2 schemas map 1:1 to relational table definitions with strict column constraints, foreign key references, and timestamp indexing.
2. **ACID Transaction Integrity**:
   - Atomic writes ensure idempotent pipeline executions: pipeline runs either commit a complete batch of validated entity records or roll back cleanly.
3. **JSONB Semi-Structured Flexibility**:
   - Fields such as `topics`, `authors`, and nested `SourceMetadata` are persisted using PostgreSQL `JSONB` columns, enabling GIN-indexed JSON query performance without sacrificing table normalization.

### Graph Database Topology (Neo4j / Amazon Neptune - Production Vision)
While relational storage excels at schema validation and tabular aggregation, modeling an **AI Ecosystem Intelligence Graph** in production requires modeling multi-hop relationship topologies.

```
       (Startup: OpenAI)
           │      │
   [:PRODUCES]  [:HIRES]
           │      │
           ▼      ▼
    (Product:  (Job: Research
     ChatGPT)   Scientist)
           │
     [:UTILIZES]
           │
           ▼
    (Paper: Attention Is All You Need)
```

#### Why a Graph Database for Production Scale?
1. **Multi-Hop Traversal Performance**:
   - Querying *"Find all startups that published a research paper cited by a competitor's product team"* requires 4+ relational JOINs, resulting in exponential $O(N^k)$ execution latency.
   - A Graph DB (Neo4j using Cypher) utilizes **index-free adjacency**, executing multi-hop traversals in $O(1)$ time per node hop regardless of total database size.
2. **Dynamic Relationship Properties**:
   - Relationships carry metadata (e.g., `(Startup)-[:RAISED_ROUND {amount: "$6.6B", date: "2024-10"}]->(FundingRound)`).

#### Storage Layer Architecture Trade-offs

| System Component | Relational DB (PostgreSQL) | Graph DB (Neo4j) | Key Trade-off Decision |
| :--- | :--- | :--- | :--- |
| **Primary Role** | Structured Entity Storage & Deduplication | Multi-hop Intelligence Graph Querying | Postgres ensures schema validation; Neo4j enables relationship discovery. |
| **Query Strengths** | Column filtering, aggregation, CRUD | Traversals (`Startup` ➔ `Product` ➔ `Paper` ➔ `Job`) | Use Postgres for ingestion pipeline targets; sync graph edges to Neo4j downstream. |
| **Write Performance** | High-throughput batch inserts | Moderate-throughput graph updates | Batch write relational entities first, stream graph delta edge updates via CDC. |
