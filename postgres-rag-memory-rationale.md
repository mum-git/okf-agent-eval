# RAG Memory System Decision: Postgres + pgvector

**Decision:** Adopt PostgreSQL with the pgvector extension as the **default** vector/memory layer for agent RAG workloads — the option you choose unless a named, specific constraint (documented in "When NOT to Choose pgvector") forces a dedicated engine. This is a default-with-off-ramps, not a claim that pgvector is the fastest or best vector database in every dimension.

**Date:** June 2026
**Scope:** Enterprise-grade, production-ready memory system for AI agents requiring semantic retrieval alongside relational data.

---

## The Short Answer

Postgres + pgvector is the default choice for any new RAG project unless you can name a specific bottleneck that forces a move to a dedicated vector database. You already have Postgres (or should). Adding pgvector costs zero new infrastructure, zero new credentials, zero new on-call rotation, and gives you ACID consistency, relational joins, and full data sovereignty out of the box.

It is a *default*, not a silver bullet. pgvector has real weaknesses — filtered-search recall, slow index builds at scale, single-node writes (see "Known Limitations") — and there are concrete workloads where a dedicated engine is the correct call (see "When NOT to Choose pgvector"). The argument is that pgvector should be what you have to argue your way *out* of, not the thing you have to justify adopting.

---

## Landscape: Other Options Evaluated

### 1. Dedicated Vector Databases

#### Pinecone
- **What it is:** Fully managed, serverless vector database. Zero operational overhead.
- **Strengths:** Easiest to use, auto-scaling to billions, SOC 2/HIPAA/ISO 27001, reliable SLAs, multi-tenant SaaS ready.
- **Weaknesses:** Vendor lock-in (no self-hosting), usage-based pricing that climbs steeply under write-heavy agent load (real production bills commonly land 3–5× above the calculator estimate), no relational data model — you still need a separate database for structured state.
- **Verdict:** Only choose if you genuinely have no infrastructure team and budget is not a concern.

#### Weaviate
- **What it is:** Open-source + managed vector database with best-in-class hybrid search (vector + BM25 + metadata).
- **Strengths:** Native multi-tenancy with data isolation, modular architecture for plugging in different embedding models/rerankers, excellent documentation.
- **Weaknesses:** Operational complexity (more knobs to tune), resource-heavy above 100M vectors, still a separate system from your relational data.
- **Verdict:** Strong choice if hybrid search is your primary concern and you need multi-tenant isolation out of the box.

#### Qdrant
- **What it is:** Rust-based open-source vector database with excellent metadata filtering.
- **Strengths:** Filtering is part of the indexing pipeline (not post-retrieval), so latency stays flat as filters get specific. Best free tier (1GB forever). Compact footprint for edge deployments.
- **Weaknesses:** Single-node throughput drops at large scale — in Timescale's (vendor) 50M-vector benchmark Qdrant sustained ~41 QPS at 99% recall vs pgvectorscale's ~471 QPS. Note the *same* benchmark showed Qdrant winning on tail latency (p99 ~39ms vs ~75ms). Still a separate system from your relational data.
- **Verdict:** Strong on metadata filtering and low tail latency; reasonable when filtered vector search is the core workload, but it doesn't consolidate relational data — not the default for general RAG.

#### Milvus / Zilliz Cloud
- **What it is:** Distributed vector database designed for billion-scale workloads.
- **Strengths:** Nothing else competes at billion-vector scale with cost efficiency (~70% cheaper than Pinecone). Separate query, index, and data nodes. SOC 2/HIPAA compliant cloud option.
- **Weaknesses:** High operational complexity — requires Kubernetes expertise. Massive overkill under 10M vectors.
- **Verdict:** The right answer at billion scale. Wrong answer everywhere else.

### 2. Unified Platforms (Vector + Existing Infrastructure)

#### Elasticsearch
- **What it is:** Search engine with kNN vector search added via DiskBBQ algorithm.
- **Strengths:** If you already run Elastic for logs/analytics, this is incremental. Granular document-level RBAC. Hybrid search (BM25 + vector) in a single query. DiskBBQ reduces memory usage 95%.
- **Weaknesses:** High operational overhead if not already running Elastic. Licensing is nuanced — since Sept 2024 the source is available under AGPLv3 (OSI-approved open source), SSPL, or Elastic License v2. It's the SSPL/ELv2 options — not AGPL — that restrict offering Elasticsearch as a competing managed service.
- **Verdict:** Use only if Elasticsearch is already part of your stack.

#### MongoDB Atlas Vector Search
- **What it is:** Vector search built into MongoDB's managed service.
- **Strengths:** One fewer system to operate if you're already on Mongo. Hybrid queries blend keyword + semantic natively.
- **Weaknesses:** Managed-only (not available on self-hosted MongoDB). Vector performance lags purpose-built options at very large scale.
- **Verdict:** Use only if MongoDB is already your primary database.

#### Redis (RediSearch + Context Engine)
- **What it is:** In-memory data store with vector search and new agent memory layer.
- **Strengths:** Ultra-low latency (sub-50ms). Already in 43% of enterprise AI agent stacks. New Context Engine provides dual-layer memory (short-term session + long-term semantic). Real-time data sync from warehouses/CRMs.
- **Weaknesses:** Not a long-term system of record. Limited transactional semantics. Memory costs at massive scale.
- **Verdict:** Excellent for short-term session memory and real-time state. Not a replacement for persistent RAG storage.

#### DataStax Astra
- **What it is:** Cassandra with built-in vector search. Horizontal scale, multi-region active-active.
- **Strengths:** Forrester Leader. Strong consistency at global scale. Multi-region, multi-cloud. SOC 2/HIPAA/FedRAMP.
- **Weaknesses:** Cassandra learning curve. Vector search is newer compared to purpose-built options.
- **Verdict:** Use only if you're already running Cassandra and need global distribution.

### 3. Full RAG Platforms (Turnkey)

#### Glean
- **What it is:** Premium enterprise AI search and assistant platform. 100+ connectors, proprietary GraphRAG.
- **Strengths:** Category leader for Fortune 500. $7.2B valuation (Series F, June 2025). Booking.com, Grammarly, Duolingo customers.
- **Weaknesses:** ~$50/user/month with $60K+ annual minimum. First-year TCO often $300K–$1M+. No open-source option. Long implementation cycles.
- **Verdict:** Premium turnkey solution when budget allows and you want someone else to solve the problem entirely.

#### Onyx
- **What it is:** Full-stack open-source enterprise AI platform with RAG, chat, and agents. MIT license.
- **Strengths:** 40+ connectors, permission-aware retrieval, air-gapped capable. Used by Ramp (115K queries/mo), NASA, UC San Diego. Free Community Edition.
- **Weaknesses:** Fewer connectors than Glean. Self-hosting requires ops knowledge.
- **Verdict:** Best open-source turnkey platform for air-gapped or data-sovereignty requirements.

---

## Why Postgres + pgvector Is a Strong Default

> These are the advantages that make pgvector the right starting point. They are real, but read them alongside "Known Limitations" below — several are strongest at small-to-mid scale and weaken as you grow.

### 1. The "Join Advantage" — One Query, Not Two

This is the single biggest architectural advantage:

```sql
-- pgvector: ONE query, ONE round trip, ACID consistent
SELECT id, title, content, 1 - (embedding <=> $1) AS similarity
FROM documents
WHERE category = 'finance'
  AND published_at > now() - interval '6 months'
  AND tenant_id = $2              -- multi-tenant isolation
ORDER BY embedding <=> $1
LIMIT 10;
```

With a dedicated vector database, the equivalent requires:
1. Search vector store → get top 50 candidate IDs
2. Query relational DB for filters (`WHERE category = 'finance' AND tenant_id = ...`)
3. Reconcile results in application code
4. Handle eventual consistency between the two stores

**Two services, two round trips, application-level reconciliation logic, and a consistency problem you didn't know you had until production.**

> **Caveat:** This same filtered query is pgvector's trickiest case for *recall*, not just convenience. With an HNSW index, selective `WHERE` clauses can exhaust the search budget before enough matching rows are found. pgvector 0.8.0 (Nov 2024) added **iterative index scans** (`hnsw.iterative_scan`) to mitigate this, but you must enable and tune them and validate recall on your real filter distribution. See "Known Limitations." Engines like Qdrant solve this structurally with in-index pre-filtering.

### 2. Zero New Infrastructure

- No new service to deploy, monitor, or scale
- No new credentials to rotate
- No new on-call rotation
- No new backup strategy
- No new disaster recovery plan
- Uses existing Postgres backups, replication, and monitoring

The operational cost of adding a second database system is often underestimated. pgvector eliminates that entirely.

### 3. Performance Is Competitive — With the Right Extension

Plain pgvector with an HNSW index is competitive through the low millions of vectors. At tens of millions, *throughput* requires the `pgvectorscale` extension (StreamingDiskANN). The most-cited public head-to-head is Timescale's benchmark (50M Cohere 768-dim vectors, 99% recall, AWS r6id.4xlarge) — note it is a **vendor benchmark and favors Postgres**:

**Throughput (50M vectors, 99% recall):**

| Engine | QPS |
|---|---|
| pgvector + pgvectorscale | **~471 QPS** |
| Qdrant | ~41 QPS |

**Latency, same benchmark (per-query):**

| Engine | p50 | p99 |
|---|---|---|
| Qdrant | ~31ms | **~39ms** |
| pgvector + pgvectorscale | ~31ms | ~75ms |

So at 50M vectors pgvectorscale wins on throughput while Qdrant holds lower tail latency — choose by whichever your workload is bound on, not on a single headline number.

For small datasets (under ~100K rows), exact nearest-neighbor search with no index runs in roughly 30–80ms. Add an HNSW index as you grow into the millions, and `pgvectorscale`'s diskANN for datasets approaching 100M vectors. (Pinecone was not part of this benchmark; its managed service advertises single-digit-millisecond p99 on optimized configs, but those figures aren't measured under the same conditions and aren't directly comparable.)

### 4. ACID Consistency

Vector inserts, updates, and deletes are part of the same transaction as your relational data. If a document is updated in your application, the embedding update either succeeds or fails atomically with the rest of the transaction. With separate vector databases, you're managing eventual consistency between two stores — a source of subtle bugs in production.

### 5. Full Data Sovereignty

Runs on your infrastructure. Air-gapped capable. No data leaves your environment. SOC 2/HIPAA/FedRAMP compliance is determined by your Postgres deployment, not a third-party vendor's certifications. Critical for regulated industries (healthcare, finance, government).

### 6. Covers All Four Memory Layers

Production agents need four types of memory:

| Layer | Function | pgvector handles it? |
|---|---|---|
| **Short-term** | Session context, transient state | ✅ (regular columns + TTL) |
| **Episodic** | Conversation history, event logs | ✅ (structured tables) |
| **Semantic** | Embeddings, knowledge retrieval | ✅ (pgvector) |
| **Procedural** | Agent workflows, instructions, state transitions | ✅ (ACID transactions) |

Most architectures split these across Redis + Pinecone + PostgreSQL. pgvector consolidates all four into one system.

### 7. Cost

- **pgvector:** Free open-source extension. You pay for your existing Postgres hosting.
- **Pinecone:** Free tier for testing; Standard plan ~$50/mo minimum, then usage-based (storage ~$0.33/GB/mo plus read/write units). A ~10M-vector multi-agent system runs ~$99–199/mo on paper, but write-heavy agent load routinely pushes real bills 3–5× higher.
- **Weaviate Cloud:** $25/mo+ with resource costs scaling up.
- **Milvus/Zilliz:** $99/mo+ managed, or infrastructure costs for self-hosted Kubernetes cluster.

For a workload of 1M vectors, pgvector on a modest Postgres instance costs less than the free tier of most alternatives. At 50M vectors, it's still competitive — and you're not paying per-operation.

### 8. Ecosystem Maturity

- **~21K GitHub stars** on the pgvector project
- Supported by all major cloud providers (AWS RDS, Azure Database for PostgreSQL, Google Cloud SQL)
- First-class integrations with LangChain, LlamaIndex, Haystack, and every major AI framework
- Active development: `pgvectorscale` extension for diskANN, quantization support, halfvec type

---

## Known Limitations (Plan For These)

pgvector is the right default, but it is not free of sharp edges. Going in with eyes open:

- **Filtered vector search can quietly lose recall.** The flagship "join advantage" query — `WHERE tenant/category/date … ORDER BY embedding <=> $1` — is also pgvector's weakest shape. With an HNSW index, a selective filter can exhaust `ef_search` before enough matching rows are found, silently returning incomplete or low-quality results. Mitigations: raise `ef_search`, use partial or partitioned indexes per high-cardinality filter, or pgvector 0.8's iterative index scans. Test recall on your *real* filter distribution, not just unfiltered queries. (This is exactly the case Qdrant's in-index pre-filtering is built to solve.)
- **HNSW index builds are slow and memory-hungry at scale.** Building the index on tens of millions of vectors can take hours and needs enough `maintenance_work_mem` to hold the graph, or the build spills and crawls. Rebuilds (after large reindexes or dimension changes) are painful — the reason >100M vectors pushes you toward distributed engines.
- **Vectors compete with your OLTP workload.** Embeddings are large and queries are CPU/memory-intensive; running them on the same instance as transactional traffic can cause noisy-neighbor contention. At scale, isolate vector queries on a read replica.
- **Write/scale ceiling is single-node.** pgvector inherits Postgres's single primary for writes. Horizontal write scaling means sharding (Citus) or a distributed engine — there's no built-in answer.
- **Recall/latency tuning is on you.** `m`, `ef_construction`, `ef_search`, and quantization (`halfvec`) all trade recall against speed and memory. Purpose-built databases ship more opinionated defaults and autotuning.

None of these are disqualifying for most enterprise workloads — but they're real operational work, not "enable the extension and forget it."

---

## When NOT to Choose pgvector

Be honest about these edge cases:

| Scenario | Better Alternative | Why |
|---|---|---|
| >100M vectors | Milvus/Zilliz | Distributed architecture handles billion-scale. pgvector HNSW rebuilds become painful. |
| No Postgres, no infra team, budget unlimited | Pinecone | Zero-ops managed. Worth the premium if you truly can't manage infrastructure. |
| Already running Elasticsearch at scale | Elasticsearch kNN | Incremental addition to existing cluster. Don't add a second system. |
| Need native multi-tenant vector isolation in SaaS product | Weaviate | Built-in multi-tenancy with data isolation is more mature than manual pgvector partitioning. |
| Ultra-low latency session memory (<10ms) | Redis | In-memory store beats disk-based Postgres for sub-millisecond reads. |

**If none of these apply, use pgvector.**

---

## Retrieval Patterns: How an Agent Actually Uses the Chunks

pgvector finds relevant **chunks**; what the agent does with them depends on the pattern. These escalate from cheap-and-simple to thorough-and-agentic. Each chunk row carries a pointer back to its source (`document_id`, `source_uri`), which is what makes the higher levels possible — without those pointers you're stuck at Level 1.

### Level 1 — Plain RAG (chunks *are* the answer)

Retrieve top-k chunks by vector similarity, drop their text straight into the prompt, the model answers. The source document is never opened.

- **How it works:** `ORDER BY embedding <=> $query LIMIT k` → stuff `content` into context.
- **When to use:** Most factual lookups. Fastest and cheapest; the default. Good when the answer fits inside a few isolated snippets.

### Level 2 — Parent-Document / "Small-to-Big" Retrieval

Search on **small** chunks for precision, but return something **bigger** for the model to read. The chunk's job is to *locate* the relevant section; you then expand around it.

- **How it works:** match a chunk → follow `document_id` → fetch the neighboring chunks (`chunk_index BETWEEN idx-2 AND idx+2`) or the parent section, and feed that richer context to the model.
- **When to use:** When precise matches need surrounding context to make sense (a matched sentence whose meaning depends on the paragraph around it). Best precision-to-context ratio for most real workloads.

### Level 3 — Agentic RAG (the agent decides to read the whole document)

Retrieval becomes a **tool the agent calls**, and reading a full source is a **second tool**. The agent treats chunk search as a table of contents, not the final answer.

- **How it works:** agent calls `search_chunks(query)` → inspects results and their `document_id`/`source_uri` → decides a hit warrants a full read → calls `get_document(id)` / `read_source(uri)` → reads thoroughly, optionally searches again, then answers.
- **When to use:** When answers genuinely require reading a document end-to-end — contracts, long procedures, multi-step reasoning across a full report. Most expensive (more tokens, more round trips), so reserve it for cases where snippets aren't enough.

**Rule of thumb:** start at Level 1, move to Level 2 when answers lose context, and reach for Level 3 only when the task requires whole-document comprehension. Watch the context window and cost at each step — dumping entire documents per query is expensive and can bury the answer ("lost in the middle").

---

## Implementation Checklist

1. **Enable the extension:** `CREATE EXTENSION vector;`
2. **Add vector columns to existing tables** — no schema migration needed beyond `ALTER TABLE ... ADD COLUMN embedding vector(1536);`
3. **Start without an index** — exact nearest-neighbor search is fast enough under ~100K rows
4. **Add HNSW index when queries slow:**
   ```sql
   CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops)
     WITH (m = 16, ef_construction = 64);
   ```
5. **For large datasets (>10M vectors):** Evaluate `pgvectorscale` extension for diskANN indexing
6. **Embedding generation:** Use any provider — OpenAI, Cohere, local sentence-transformers model, or on-device. Store the resulting vector in the column.

---

## Sources

> **On the benchmarks:** Throughput/latency figures above come from vendor and community benchmarks run on differing hardware, dimensions, and recall targets — they are not directly comparable across rows. The 50M-vector pgvectorscale-vs-Qdrant numbers are from Timescale (a Postgres vendor) and should be read as directional, not neutral.

- Timescale/Tiger Data: "pgvector vs. Qdrant" benchmark (50M vectors, 99% recall)
- PostgreSQL.org: "pgvector 0.8.0 Released!" (Nov 11, 2024) — iterative index scans for filtered search
- Pinecone: official pricing page and 2026 cost analyses (Standard plan ~$50/mo minimum, usage-based)
- Firecrawl: "Best Vector Databases in 2026" (May 2026)
- Vectorize.io: "Best AI Agent Memory Systems in 2026" 
- PingCAP: "Best Database for AI Agents (2026)"
- Medium/Intuz: "Top 15 Vector Databases in 2026: A Production Guide" (100+ enterprise deployments)
- Onyx AI: "Best Enterprise RAG Platforms 2026"
- pgvector documentation and community benchmarks
- Zilliz: Milvus vs Pinecone comparison
- Redis: Context Engine announcement (May 2026)
