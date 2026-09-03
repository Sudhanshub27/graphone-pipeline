# Tripwire LLM Extraction Quality Evaluation Framework

The `evaluation/llm` package provides a standalone, scientific evaluation harness to measure structured extraction quality, schema validation rates, field accuracy, field completeness, missing fields, hallucinations, and latency across individual LLM providers (`Gemini`, `Groq`, `DeepSeek`, `RuleBased`) and the production `FallbackChain`.

---

## Ground-Truth Dataset Structure

The evaluator utilizes a manually curated, verifiable ground-truth dataset stored at [`evaluation/datasets/extraction/ground_truth.json`](../datasets/extraction/ground_truth.json).

Each dataset item contains:
* `id`: Unique identifier (e.g. `gt-startup-01`)
* `target_schema`: Target schema name string (`Startup`, `Product`, `ResearchPaper`, `Job`, `News`)
* `source_text`: Unstructured HTML snippet or raw article body
* `expected_fields`: Dictionary of expected ground-truth field key-value pairs

---

## Field-Level Comparison Rules

Field scoring uses domain-specific normalization instead of rigid exact string matching:

1. **Normalized Strings**:
   * Lowercases text, strips legal corporate suffixes (`Inc`, `LLC`, `Ltd`, `Corp`), removes punctuation, and computes token overlap (Jaccard similarity) and substring containment.
2. **Numeric Fields**:
   * Converts numbers and string-formatted currency/quantities (e.g. `1240` vs `$1240`) to float values. Matches within 1% relative tolerance score 1.0.
3. **Dates**:
   * Parses normalized `YYYY-MM-DD` or `YYYY` date representations. Year matching scores 0.8+; full date matching scores 1.0.
4. **Lists / Sets**:
   * Evaluates list elements (e.g. tags, categories, requirements, authors) as unordered sets using Jaccard set overlap: $J(A, B) = \frac{|A \cap B|}{|A \cup B|}$.

---

## Metrics Measured

For each evaluated provider or chain, the harness measures:

* `json_validity`: Ratio of responses producing valid JSON
* `schema_validity`: Ratio of extractions passing Pydantic `schema.model_validate()`
* `field_accuracy`: Average accuracy score across expected ground-truth fields
* `field_completeness`: Ratio of expected non-null fields successfully extracted
* `missing_fields`: List of ground-truth fields missing or null in extraction
* `unexpected_fields`: Extracted keys not present in the target schema or ground truth
* `average_latency_ms`: Mean extraction latency per document in milliseconds
* `fallback_occurrence_rate`: Ratio of extractions escalating past Tier-1 providers

---

## Output Report Specification

Running an evaluation produces a machine-readable JSON report:

```json
{
  "provider": "FallbackChain",
  "schema": "All Schemas",
  "examples": 7,
  "json_validity": 1.0,
  "schema_validity": 1.0,
  "field_accuracy": 0.985,
  "field_completeness": 1.0,
  "average_latency_ms": 12.4,
  "fallback_occurrence_rate": 1.0,
  "missing_fields": [],
  "unexpected_fields": [],
  "per_example_results": [...]
}
```

---

## Execution Guide

### 1. Evaluate Production FallbackChain

```bash
python -m evaluation.llm.evaluator --provider chain --output evaluation/reports/llm_chain_eval.json
```

### 2. Evaluate Offline Rule-Based Heuristic Provider

```bash
python -m evaluation.llm.evaluator --provider rule --output evaluation/reports/llm_rule_eval.json
```

### 3. Evaluate Individual Frontier Providers (Requires API Keys)

```bash
python -m evaluation.llm.evaluator --provider gemini
python -m evaluation.llm.evaluator --provider groq
python -m evaluation.llm.evaluator --provider deepseek
```

---

## Evaluation Framework Limitations

1. **Ground-Truth Corpus Size**: The initial dataset consists of 7 manually verified HTML/text snippets covering all 5 schemas. While high-precision, statistical confidence will expand as community ground-truth contributions grow.
2. **String Normalization Bounds**: Normalization strips corporate suffixes and punctuation; however, long paraphrased descriptions may receive partial token overlap scores despite conveying identical semantics.
3. **API Non-Determinism**: Commercial LLMs (Gemini, Groq, DeepSeek) may exhibit minor response variations across runs depending on model version updates or non-zero temperatures.
4. **Mock Mode / RuleBased Isolation**: In offline mock mode, extractions use `RuleBasedFallbackProvider` heuristics, which reflect baseline regex extraction capabilities rather than live frontier LLM reasoning.
