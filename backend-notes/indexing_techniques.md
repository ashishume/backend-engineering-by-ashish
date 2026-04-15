When you’re designing a backend system (especially multi-tenant SaaS or high-scale apps), **indexing and partitioning** are your primary levers for performance optimization at the storage layer. Let’s break this down in a practical, system-design-oriented way.

---

# 🔹 1. Indexing Strategies (Query Optimization)

Indexes reduce **read latency** by avoiding full table scans.

## 📌 Types of Indexes

### 1. B-Tree Index (default in most DBs like PostgreSQL)

* Best for:

  * `=`, `<`, `>`, `BETWEEN`, `ORDER BY`
* Use case:

  ```sql
  SELECT * FROM users WHERE email = 'x';
  ```

---

### 2. Hash Index

* Best for:

  * Exact match (`=`)
* Not useful for range queries
* Rarely used in production compared to B-tree

---

### 3. Composite Index (Multi-column)

* Order matters ⚠️

```sql
CREATE INDEX idx_user_org_email ON users(org_id, email);
```

* Works for:

  * `(org_id)`
  * `(org_id, email)`
* NOT for:

  * `(email)` alone

👉 Critical for **multi-tenancy**

```sql
WHERE org_id = ? AND email = ?
```

---

### 4. Partial Index

* Index only subset of rows

```sql
CREATE INDEX idx_active_users 
ON users(email) 
WHERE is_active = true;
```

👉 Reduces index size + faster scans

---

### 5. Covering Index (INCLUDE)

* Avoids hitting table (index-only scan)

```sql
CREATE INDEX idx_user_email 
ON users(email) INCLUDE(name, age);
```

---

### 6. Full-text Index

* For search systems (or use Elasticsearch instead)

---

## 📌 Indexing Best Practices

### ✅ Always index:

* `WHERE` filters
* `JOIN` keys
* `ORDER BY / GROUP BY`

---

### ⚠️ Avoid over-indexing:

* Slows down `INSERT/UPDATE`
* Each index = extra write

---

### 🔥 Multi-tenant Optimization

For SaaS:

```sql
CREATE INDEX idx_org_data ON table(org_id, created_at);
```

* Ensures tenant isolation in queries
* Prevents cross-tenant scans

---

# 🔹 2. Partitioning Strategies (Data Scaling)

Partitioning splits large tables → improves **query performance + manageability**

---

## 📌 Types of Partitioning

### 1. Horizontal Partitioning (Sharding within DB)

Split rows across partitions:

```text
users_1 → id 1–1M
users_2 → id 1M–2M
```

---

### 2. Range Partitioning

Best for time-series / logs

```sql
PARTITION BY RANGE (created_at)
```

Examples:

* Jan data → partition A
* Feb data → partition B

👉 Used in:

* analytics
* logs
* events

---

### 3. List Partitioning

Partition based on values:

```sql
PARTITION BY LIST (region)
```

Example:

* India → partition A
* US → partition B

---

### 4. Hash Partitioning

Even distribution:

```sql
PARTITION BY HASH (user_id)
```

👉 Prevents skew

---

### 5. Vertical Partitioning

Split columns instead of rows

```text
users_basic → id, name
users_heavy → id, metadata_json
```

👉 Reduces row size → faster queries

---

# 🔹 3. Sharding (Across Databases)

Partitioning inside DB ≠ Sharding

Sharding = multiple DB instances

---

## 📌 Sharding Strategies

### 1. Tenant-based sharding (Best for SaaS)

```text
DB1 → org_id 1–1000
DB2 → org_id 1001–2000
```

✔ Strong isolation
✔ Easy scaling
❌ Hard rebalancing

---

### 2. Hash-based sharding

```text
shard = hash(user_id) % N
```

✔ Even distribution
❌ Hard debugging

---

### 3. Geo-based sharding

```text
India → ap-south DB
US → us-east DB
```

✔ Low latency
✔ Compliance-friendly

---

# 🔹 4. Indexing + Partitioning Together (Important)

This is where most systems fail.

## ❌ Bad:

* Partitioned table without proper indexes → still slow

## ✅ Good:

Each partition has its own index:

```sql
CREATE INDEX idx_partitioned 
ON orders_2026(created_at);
```

---

# 🔹 5. Real-world Architecture (Your Case)

Given your SaaS + multi-DB (regions):

### Recommended:

### ✅ DB Level:

* Partition by `created_at` (range)
* Index on `(org_id, created_at)`

---

### ✅ Multi-region:

* Each region → separate DB cluster
* App routes user → nearest region

---

### ✅ Query Flow:

1. Identify region DB
2. Use partition pruning (date filter)
3. Use index (org_id + filter)

---

# 🔹 6. Common Pitfalls

### ❌ Missing tenant filter

```sql
SELECT * FROM data WHERE email = 'x';
```

→ Full scan across tenants 😬

---

### ❌ Wrong index order

```sql
INDEX(email, org_id)
```

Query:

```sql
WHERE org_id = ? AND email = ?
```

→ inefficient

---

### ❌ Too many partitions

* PostgreSQL struggles with 1000s partitions

---

### ❌ Skewed partitions

* One partition huge, others empty

---

# 🔹 7. Quick Decision Cheat Sheet

| Problem                | Solution                     |
| ---------------------- | ---------------------------- |
| Slow reads             | Indexing                     |
| Huge tables            | Partitioning                 |
| Multi-region scaling   | Sharding                     |
| Multi-tenant isolation | Composite index (org_id + X) |
| Logs/events            | Range partitioning           |

---
