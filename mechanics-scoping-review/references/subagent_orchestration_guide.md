# Subagent Orchestration Guide for Large-Scale Mechanics Review

## 1. Principles of Parallel Delegation

When reviewing literature sets exceeding 30-50 papers, keeping all abstracts and full texts within the main LLM context causes severe token fatigue and loss of precision. The subagent delegation architecture solves this by dividing screening into independent parallel tasks.

**Core Rules:**
1. **Strict Context Isolation**: Each subagent receives only its designated batch (typically 10-15 papers) and the screening rubric.
2. **Structured Machine-Readable Output**: Subagents must write standardized JSON files (`batch_01_evaluated.json`, etc.) containing score, category, key findings, and extracted equations/parameters.
3. **Consolidation Checkpoints**: The root orchestrator never summarizes unverified raw text; it reads all batch JSONs, performs cross-checking, and generates the master PRISMA flow chart.

## 2. Dispatching Subagents Workflow

### Step 1: Batch Partitioning
Given N retrieved papers from `search_mechanics_papers.py`, divide into chunks of size M (M ~ 10-15):
- Batch 1: Papers 1 - 15
- Batch 2: Papers 16 - 30
- Batch 3: Papers 31 - 45

### Step 2: Subagent Prompt Specification
When calling `spawn_agent`, supply:
- Task Name: `subagent_review_batch_k`
- Clear Task Instruction: "Read papers in batch k from `batches/batch_k.json`. Apply the mechanics screening rubric from `references/mechanics_screening_rubrics.md`. For each paper, output: (1) Score (0-10), (2) Mechanical category, (3) Key analytical methods, (4) Specific benchmark data if present. Save results to `batches/batch_k_evaluated.json` and return a brief completion summary."

### Step 3: Consolidation & Quality Audit
After all subagents finish:
1. Merge all `batch_*_evaluated.json` into `master_evaluated_papers.json`.
2. Flag discrepancies (e.g. papers scored 7-8 that lack governing equations).
3. Select top Priority papers (Score >= 7) for citation snowballing and full-text retrieval.