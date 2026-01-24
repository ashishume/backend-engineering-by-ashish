# PostgreSQL as a Practical Alternative to Elasticsearch

Elasticsearch is often the default choice for implementing search. However, in many real-world systems, introducing Elasticsearch adds **operational overhead, infrastructure cost, and data consistency challenges** that are not always justified.

Modern PostgreSQL provides several capabilities that make it a **viable search engine** for a large class of applications.

This post explains **when and how PostgreSQL can replace Elasticsearch**, using fuzzy search as a concrete example.

---

## Why Elasticsearch Is Not Always the Right First Choice

Elasticsearch excels at:

- Distributed, large-scale search
- Advanced analyzers (synonyms, phonetics)
- High-throughput read-heavy workloads

But it also introduces:

- Another distributed system to operate
- Eventual consistency
- Data synchronization complexity
- Additional infrastructure cost

For many applications, these trade-offs are unnecessary.

---

## What PostgreSQL Brings to the Table

PostgreSQL is not just a relational database anymore.

It provides:

- Native **full-text search** (`tsvector`, `tsquery`)
- **Fuzzy search** using `pg_trgm`
- JSONB indexing for semi-structured data
- Advanced indexing (GIN, GiST)
- Strong consistency (ACID)
- Rich querying with joins and transactions

In many cases, PostgreSQL can handle **both storage and search** effectively.

---

## Architecture Overview

```
Client
  |
  v
FastAPI Service
(Create + Search APIs)
  |
  v
PostgreSQL
- products table
- pg_trgm extension
- GIN indexes
- similarity() ranking
```

In this setup:

- PostgreSQL is the **single source of truth**
- Search queries run directly against indexed text columns
- No Elasticsearch cluster is required

---

## Enabling Fuzzy Search in PostgreSQL

### Enable required extensions

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
```

### Create search-optimized indexes

```sql
CREATE INDEX idx_products_name_trgm
ON products USING GIN (name gin_trgm_ops);

CREATE INDEX idx_products_desc_trgm
ON products USING GIN (description gin_trgm_ops);
```

These indexes allow efficient **typo-tolerant searches** using trigram similarity.

---

## Fuzzy Search Query Example

```sql
SELECT
  id,
  name,
  description,
  similarity(unaccent(name), unaccent('iphne')) AS score
FROM products
WHERE
  unaccent(name) % unaccent('iphne')
  OR unaccent(description) % unaccent('iphne')
ORDER BY score DESC
LIMIT 20;
```

This query supports:

- Typo tolerance (`iphne` → `iphone`)
- Relevance ranking
- Accent-insensitive search

Functionally, this resembles a basic Elasticsearch fuzzy query.

---

## Where PostgreSQL Search Works Well

PostgreSQL is a strong fit when:

- Search is tightly coupled with transactional data
- Dataset size is in the **low-to-mid tens of millions**
- Strong consistency is required
- Joins and filters are important
- Operational simplicity matters

Common examples:

- SaaS dashboards
- Admin panels
- Internal tools
- Product catalogs
- Content platforms

---

## Where Elasticsearch Still Wins

Elasticsearch is still the right choice when you need:

- Massive scale (hundreds of millions or billions of documents)
- Advanced analyzers and synonym handling
- Distributed search across shards
- Heavy read concurrency with near-real-time indexing

---

## A Common Industry Pattern

Many mature systems follow this approach:

```
PostgreSQL → Source of truth
Elasticsearch → Search index (only when needed)
```

PostgreSQL handles correctness and transactions.
Elasticsearch is introduced only when search requirements outgrow Postgres.

---

## Key Takeaway

**Do not start with Elasticsearch by default.**

Start with PostgreSQL:

- Simpler architecture
- Fewer moving parts
- Strong consistency
- Lower cost

Introduce Elasticsearch only when your **scale or search complexity justifies it**.

---
