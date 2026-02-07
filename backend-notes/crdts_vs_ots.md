# CRDTs vs OTs: Real-Time Collaboration Algorithms

## What Are They?

**CRDT (Conflict-free Replicated Data Type)** and **OT (Operational Transformation)** are algorithms for building real-time collaborative applications where multiple users edit the same data simultaneously.

• **OT**: Transform operations based on concurrent changes (Google Docs approach)
• **CRDT**: Data structures that automatically merge without conflicts (Figma approach)

## The Problem They Solve

When multiple users edit the same document simultaneously:

1. User A types "Hello" at position 0
2. User B types "World" at position 0
3. Both send their changes at the same time

**Without coordination**: Data corruption, lost edits, inconsistent states

**With OT/CRDT**: All users see the same final result

## Operational Transformation (OT)

### How It Works

OT transforms operations against each other to preserve intent:

```
Initial: "ABC"

User A: Insert "X" at position 1 → "AXBC"
User B: Insert "Y" at position 2 → "ABXC"

Without OT: Conflicts and data loss
With OT: Transform B's operation → Insert "Y" at position 3
Result: "AXYBC" (both edits preserved)
```

### OT Challenges

- **Complexity**: N operations require O(N²) transformations
- **Central server**: Typically needs a server to order operations
- **Edge cases**: Many subtle bugs in transformation functions

## CRDTs (Conflict-free Replicated Data Types)

### How It Works

CRDTs use special data structures where all operations are commutative—order doesn't matter:

```
Key insight: Every character gets a unique, ordered ID

User A: Insert "X" with ID (A, 1) after position 0
User B: Insert "Y" with ID (B, 1) after position 0

Both merge: IDs determine final order
Result: Consistent on all replicas
```

### Types of CRDTs

| Type             | Description                 | Example            |
| ---------------- | --------------------------- | ------------------ |
| **G-Counter**    | Grow-only counter           | View counts, likes |
| **PN-Counter**   | Increment/decrement counter | Inventory          |
| **G-Set**        | Grow-only set               | Add tags           |
| **OR-Set**       | Observed-remove set         | Shopping cart      |
| **LWW-Register** | Last-writer-wins            | User profile       |
| **RGA/YATA**     | Sequence/text               | Collaborative text |

## Comparison: CRDTs vs OTs

| Aspect           | OT                          | CRDT                   |
| ---------------- | --------------------------- | ---------------------- |
| **Architecture** | Usually centralized         | Peer-to-peer friendly  |
| **Complexity**   | Transform functions complex | Data structure complex |
| **Ordering**     | Requires operation ordering | Order-independent      |
| **Memory**       | Lower (ops discarded)       | Higher (tombstones)    |
| **Latency**      | May need server round-trip  | Local-first possible   |
| **Offline**      | Harder to support           | Natural support        |
| **Used By**      | Google Docs, Etherpad       | Figma, Yjs, Automerge  |

## When to Use What

### Choose OT When:

- ✅ Centralized server architecture
- ✅ Memory is a concern (no tombstones)
- ✅ Simpler data structures (mostly text)
- ✅ Always-online assumption

### Choose CRDTs When:

- ✅ Peer-to-peer or offline-first apps
- ✅ Complex data types needed
- ✅ Decentralized architecture
- ✅ Eventually consistent is acceptable

## Real-World Implementations

| Product         | Algorithm | Notes                            |
| --------------- | --------- | -------------------------------- |
| **Google Docs** | OT        | Server-based, optimized for text |
| **Figma**       | CRDT      | Custom implementation for design |
| **Notion**      | OT        | Hybrid approach                  |
| **Apple Notes** | CRDT      | Uses CloudKit for sync           |
| **Yjs**         | CRDT      | Popular open-source library      |
| **Automerge**   | CRDT      | JSON-like CRDT library           |

## Interview Q&A

### Q: Explain the difference between CRDTs and OT in simple terms.

**A**:

- **OT**: When conflicts happen, transform operations to make them compatible. Like a traffic controller merging lanes.
- **CRDT**: Design data structures so conflicts can't happen. Like giving everyone their own lane.

### Q: What's the main advantage of CRDTs over OT?

**A**: CRDTs work offline and peer-to-peer without a central server. Operations can be applied in any order and still converge to the same state. OT typically requires a central server to order operations.

### Q: What's the main disadvantage of CRDTs?

**A**: Memory overhead. CRDTs often use tombstones (marking deleted items instead of removing them) to handle deletions, which can grow unbounded. Garbage collection is complex.

### Q: How would you implement a collaborative counter?

**A**: Use a G-Counter (grow-only) or PN-Counter CRDT:

- Each node maintains its own count
- Merge by taking max for each node
- Sum all nodes for total value

### Q: Why is OT considered harder to implement correctly?

**A**: OT transformation functions have many edge cases. For N operation types, you need N² transformation pairs. Subtle bugs cause divergence. CRDTs avoid this by making merge commutative by design.

## Key Takeaways

✅ OT transforms concurrent operations; CRDTs use conflict-free data structures  
✅ OT is typically centralized; CRDTs support peer-to-peer  
✅ CRDTs have higher memory usage (tombstones)  
✅ CRDTs naturally support offline-first  
✅ Both achieve eventual consistency  
✅ Choose based on architecture needs (centralized vs distributed)
