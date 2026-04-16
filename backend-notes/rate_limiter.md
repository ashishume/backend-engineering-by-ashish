# Rate limiters

Common algorithms for capping how often a client (user, IP, API key) may call a service. Pick one based on fairness, burst tolerance, storage cost, and how sharp you want the limit at window edges.

## Sliding window

You keep every request timestamp (or use a structure like a Redis sorted set) and only count events whose timestamps fall in **\[now − W, now\]**. The “window” literally slides forward in time as `now` advances.

- **Behavior:** The limit is enforced over the last **W** seconds continuously, so there is no artificial reset line in the middle of the wall clock.
- **Trade-offs:** Accurate and smooth, but storing each event (or many buckets) costs more memory and work than coarse counters.
- **Good for:** APIs where you care about “no more than N requests in any rolling W-second period,” not just per calendar minute.

## Fixed window

Time is split into non-overlapping buckets (e.g. minute 0–59, then 60–119). You count requests **per bucket** and reset when a new bucket starts.

- **Behavior:** Very simple: increment a counter keyed by `floor(now / W)`.
- **Trade-offs:** Cheap, but **boundary spikes**: a client can send N requests at the end of one window and N at the start of the next, so briefly you allow **2N** in a span shorter than **2W** if windows align badly.
- **Good for:** Rough limits, batch jobs, or when approximate fairness is enough.

## Fixed window counter

Same idea as fixed window, but you only persist a **single counter (and maybe the current window id)** per key—not every request time.

- **Behavior:** “How many in this bucket?” resets when the bucket id changes.
- **Trade-offs:** Same boundary issue as fixed window, with minimal storage and O(1) updates.
- **Good for:** High traffic, Redis/Memcached with tiny keys, when you accept edge doubling.

## Sliding window counter

A **hybrid** that approximates a sliding window without storing every timestamp. You keep the count for the **current** fixed window and the **previous** window, then estimate overlap: e.g. weight the previous window’s count by how much of **W** still overlaps `now`.

- **Behavior:** Smoother than pure fixed window, much cheaper than storing every event.
- **Trade-offs:** Not exact like a full sliding log; error is usually small and acceptable for HTTP rate limits.
- **Good for:** Large scale when you want fewer spikes than fixed window but cannot afford per-event storage.

## Token bucket (used by big tech)

A bucket holds up to **C** tokens; tokens are added continuously at rate **r** (tokens per second), capped at **C**. Each allowed request **consumes one token**; if `tokens < 1`, reject (or wait).

- **Behavior:** **Bursts** up to **C** are allowed, then the sustained rate is about **r**. Traffic is “lumpy” in a controlled way.
- **Trade-offs:** Very common in networking and APIs; easy to reason about burst + average. Needs atomic updates (or Lua/scripts) in Redis for correctness under concurrency.
- **Good for:** “Average R/s but allow short spikes,” shaping friendly to interactive clients.

## Leaky bucket

Requests arrive into a **queue** (or abstract bucket); the server **drains** (processes) them at a **fixed** rate, like water leaking from a hole at the bottom.

- **Behavior:** Output rate is **steady**; bursts are absorbed in the queue until it is full—then you **drop** or reject new arrivals (depending on variant).
- **Trade-offs:** Protects downstream from burst overload; can add **latency** for queued work and may drop if the queue overflows.
- **Good for:** Smoothing traffic into a worker or DB at a constant pace, not for “N per minute” fairness in the same way as window counters.

---

## Sliding window using Redis

The snippet below uses a **sorted set** keyed by time: scores are timestamps. Before counting, it removes members older than `now - WINDOW`, then checks cardinality against `LIMIT`. The pipeline batches commands for fewer round-trips.

```
import time
import redis

r = redis.Redis()

LIMIT = 5
WINDOW = 10  # seconds

def is_allowed(user_id):
    key = f"rate:{user_id}"
    now = time.time()

    pipe = r.pipeline()

    # Remove old requests
    pipe.zremrangebyscore(key, 0, now - WINDOW)

    # Count current requests
    pipe.zcard(key)

    # Add current request
    pipe.zadd(key, {now: now})

    # Set expiry
    pipe.expire(key, WINDOW)

    results = pipe.execute()

    current_count = results[1]

    return current_count < LIMIT

```

**Complexity:** Time **O(log n)** for ZSET operations (n ≈ members in window); space **O(n)** per user for events inside the window.

---

## Token bucket using Redis (BEST PRACTICE)

Stores **tokens** and **last_time** in a hash. On each check, elapsed time refills tokens at `RATE`, capped at `CAPACITY`; one token is spent if the request is allowed. In production, run this logic in a **single atomic step** (Redis `EVAL` / Lua or `INCR`-style patterns) so concurrent requests do not double-spend tokens.

```
import time
import redis

r = redis.Redis()

RATE = 5          # tokens per second
CAPACITY = 10     # max bucket size

def allow_request(user_id):
    key = f"bucket:{user_id}"

    now = time.time()

    bucket = r.hmget(key, "tokens", "last_time")

    tokens = float(bucket[0]) if bucket[0] else CAPACITY
    last_time = float(bucket[1]) if bucket[1] else now

    # Refill tokens
    delta = now - last_time
    tokens = min(CAPACITY, tokens + delta * RATE)

    if tokens < 1:
        return False

    tokens -= 1

    r.hmset(key, {
        "tokens": tokens,
        "last_time": now
    })

    return True
```
