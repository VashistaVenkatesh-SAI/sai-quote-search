# UL 891 Cross-Reference Matrix
## For Quote Bot Knowledge Base Chunking

This document maps all internal cross-references in UL 891 (July 2019).
Use this when chunking the document to embed relationship metadata in each chunk.

---

## How to Use This Matrix

When you create a chunk for **Section 8.8.1.6.2**, your metadata should include:
```yaml
references_sections: [8.8.1.6.3]
references_tables: [Table 23]
```

When you create a chunk for **Table 6**, your metadata should include:
```yaml
referenced_by_sections: [8.1.16.12, 8.1.16.14, 8.1.17.5, 8.8.1.4.4, 8.8.1.7.2, 9.2.3.1.1]
```

---

## Section → Section References

These sections reference other sections. When chunking, link them together.

| Source Section | References Sections |
|----------------|---------------------|
| 5.3.1.1.1 | 8.8.1.6.16.1 |
| 5.3.2.1 | 8.8.1.6.9 |
| 5.3.2.3 | 5.3.1.1 |
| 6.1.2.1 | 6.2.1.2 |
| 6.2.1.6 | 6.2.1.2 |
| 6.2.1.12.2 | 8.8.4.2 |
| 6.2.1.14 | 6.2.1.12 |
| 6.2.1.15.1 | 9.1.1.6 |
| 6.2.1.15.2 | 8.5.1.2 |
| 6.2.1.15.3 | 6.2.5.3 |
| 6.2.1.15.4 | 8.8.4.2, 6.2.1.12.2 |
| 6.2.2.6 | 8.1.13.2 |
| 6.2.2.7 | 8.1.13.5.1 |
| 6.2.2.9 | 8.1.12.13 |
| 6.2.6.2 | 3.28 |
| 6.2.7.1 | 6.2.7.2, 6.2.7.3 |
| 6.2.7.12 | 6.2.7.11, 6.2.7.13 |
| 6.2.7.22 | 8.8.2.3.15 |
| 6.2.8.3 | 8.6.15.3 |
| 8.1.13.5.1 | 6.2.2.7 |
| 8.1.14.1 | 8.1.11.3 |
| 8.1.16.3 | 8.1.16.12 |
| 8.1.16.13 | 8.8.2.3.6 |
| 8.1.18.5 | 8.1.18.5 |
| 8.1.18.7 | 8.1.18.3 |
| 8.2.1.3.2 | 8.2.1.3.1 |
| 8.2.1.4.5 | 8.2.1.4.3 |
| 8.2.1.5.1 | 6.2.9.1.1 |
| 8.4.1.4 | 8.6.7.8.1 |
| 8.4.6 | 8.4.6.1 |
| 8.4.6.1.3 | 8.1.11.4 |
| 8.4.6.1.4 | 8.4.8 |
| 8.4.6.4.3 | 8.1.13.1 |
| 8.4.7.2.2 | 8.4.8 |
| 8.4.8.11 | 9.2.2.17 |
| 8.6.5.5 | 6.2.3.3 |
| 8.6.6.8.1 | 8.6.8.1 |
| 8.6.6.8.1.1 | 6.2.1.10 |
| 8.6.6.8.2 | 8.6.15.1 |
| 8.6.7.4 | 6.2.1.10, 8.6.15.2 |
| 8.6.7.8.1 | 6.2.3.11 |
| 8.6.11.13 | 8.1.1.2, 8.7.1.1 |
| 8.6.15.4 | 8.6.15.3, 8.6.18.3 |
| 8.6.17.2 | 6.2.8.1 |
| 8.7.1.6 | 8.7.1.5 |
| 8.7.1.7 | 8.7.1.3 |
| 8.7.2.1 | 8.7.1.1 |
| 8.8.1.5.1 | 8.8.1.3.1 |
| 8.8.1.6.2 | 8.8.1.6.3 |
| 8.8.1.6.3.1 | 8.6.11.12 |
| 8.8.1.6.6 | 8.8.1.6.5 |
| 8.8.1.6.9 | 5.3 |
| 8.8.2.3.2.2 | 6.2.7.15 |
| 8.8.2.3.4 | 6.2.7.1 |
| 8.8.3.1.2.1 | 8.8.2.3.6, 6.2.7.10 |
| 8.8.4.1.4 | 8.8.1.8.6 |
| 9.1.1.2.6 | 6.2.15 |
| 9.1.1.7 | 8.8.1.6 |
| 9.1.1.8.2 | 8.6.12.1.1 |
| 9.2.2.11.1 | 9.2.2.13 |
| 9.2.2.14 | 9.2.2.1 |
| 9.2.2.16 | 9.2.2.1 |
| 9.2.3.2 | 9.2.3.1 |
| 9.2.4.2.4.4 | 9.2.4.2.4.2 |
| 9.2.4.2.7.1 | 6.3.3.1 |
| 9.2.4.3.1.2 | 9.2.4.4.2.1 |
| 9.2.4.3.2.1 | 9.2.4.3.2.2 |
| 9.2.4.4.1.1 | 9.2.4.4.3.1 |
| 9.2.4.4.6.1 | 9.2.4.1.5.1 |
| 9.2.8.1 | 9.2.8.2 |

---

## Section → Table References

These sections reference tables. Pull the table content when these sections are retrieved.

| Source Section | References Tables |
|----------------|-------------------|
| 6.2.1.15 | Table 3 |
| 6.2.1.15.2 | Table 16 |
| 6.2.9.1 | Table 12 |
| 6.2.14.1 | Table 14 |
| 8.1.10.2 | Table 5 |
| 8.1.16.5 | Table 13 |
| 8.1.16.12 | Table 6 |
| 8.1.16.14 | Table 6 |
| 8.1.17.5 | Table 6, Table 7 |
| 8.2.1.4.2 | Table 12 |
| 8.2.1.4.3 | Table 12 |
| 8.4.4.1 | Table 14, Table 15 |
| 8.4.4.4 | Table 14 |
| 8.4.7.2 | Table 15, Table 14 |
| 8.5.1.1 | Table 16 |
| 8.6.11.6 | Table 18 |
| 8.6.15.1.3 | Table 20 |
| 8.6.15.2 | Table 20 |
| 8.6.17.1 | Table 25 |
| 8.7.1.2.1 | Table 7 |
| 8.8.1.4.4 | Table 6 |
| 8.8.1.6.2 | Table 23 |
| 8.8.1.6.3 | Table 24 |
| 8.8.1.6.4 | Table 25 |
| 8.8.1.6.6 | Table 23, Table 24, Table 25 |
| 8.8.1.7.2 | Table 6 |
| 8.8.1.8.1 | Table 28, Table 29 |
| 8.8.3.1.2 | Table 28 |
| 8.8.3.2.2 | Table 30, Table 31 |
| 8.8.3.2.6.1 | Table 32 |
| 8.8.3.3.2 | Table 33 |
| 9.2.2.7 | Table 35 |
| 9.2.2.8 | Table 13 |
| 9.2.2.10 | Table 13 |
| 9.2.3.1.1 | Table 6 |
| 9.2.4.2.4.1 | Table 28 |
| 9.2.4.2.8.1 | Table 36 |

---

## Section → Figure References

These sections reference figures.

| Source Section | References Figures |
|----------------|-------------------|
| 8.1.6.2 | Figure 6 |
| 8.2.1.5.7 | Figure 10, Figure 11 |
| 8.2.1.5.8 | Figure 12 |
| 8.4.3.1 | Figure 14 |
| 8.6.5.1 | Figure 2, Figure 3 |
| 9.2.4.2.4.4 | Figure 17 |

---

## Section → Annex References

| Source Section | References Annexes |
|----------------|-------------------|
| 2.4.1 | Annex A |
| 6.2.1.1 | Annex C |
| 8.1.4.1 | Annex B |
| 8.1.17.2 | Annex B |
| 8.2.1.5.2 | Annex B |
| 8.4.4.7 | Annex B |
| 8.8.2.3.1.2 | Annex B |
| 8.8.2.3.2 | Annex B |
| 9.1.1.2.7 | Annex G |

---

## Tables: Reverse Lookup

Use this to add `referenced_by` metadata to each table chunk.

### Table 3
Referenced by sections: 6.2.1.15

### Table 5
Referenced by sections: 8.1.10.2

### Table 6
Referenced by sections: 8.1.16.12, 8.1.16.14, 8.1.17.5, 8.8.1.4.4, 8.8.1.7.2, 9.2.3.1.1

### Table 7
Referenced by sections: 8.1.17.5, 8.7.1.2.1

### Table 12
Referenced by sections: 6.2.9.1, 8.2.1.4.2, 8.2.1.4.3

### Table 13
Referenced by sections: 8.1.16.5, 9.2.2.8, 9.2.2.10

### Table 14
Referenced by sections: 6.2.14.1, 8.4.4.1, 8.4.4.4, 8.4.7.2

### Table 15
Referenced by sections: 8.4.4.1, 8.4.7.2

### Table 16
Referenced by sections: 6.2.1.15.2, 8.5.1.1

### Table 18
Referenced by sections: 8.6.11.6

### Table 20
Referenced by sections: 8.6.15.1.3, 8.6.15.2

### Table 23
Referenced by sections: 8.8.1.6.2, 8.8.1.6.6

### Table 24
Referenced by sections: 8.8.1.6.3, 8.8.1.6.6

### Table 25
Referenced by sections: 8.6.17.1, 8.8.1.6.4, 8.8.1.6.6

### Table 28
Referenced by sections: 8.8.1.8.1, 8.8.3.1.2, 9.2.4.2.4.1

### Table 29
Referenced by sections: 8.8.1.8.1

### Table 30
Referenced by sections: 8.8.3.2.2

### Table 31
Referenced by sections: 8.8.3.2.2

### Table 32
Referenced by sections: 8.8.3.2.6.1

### Table 33
Referenced by sections: 8.8.3.3.2

### Table 35
Referenced by sections: 9.2.2.7

### Table 36
Referenced by sections: 9.2.4.2.8.1


---

## Figures: Reverse Lookup

### Figure 2
Referenced by sections: 8.6.5.1

### Figure 3
Referenced by sections: 8.6.5.1

### Figure 6
Referenced by sections: 8.1.6.2

### Figure 10
Referenced by sections: 8.2.1.5.7

### Figure 11
Referenced by sections: 8.2.1.5.7

### Figure 12
Referenced by sections: 8.2.1.5.8

### Figure 14
Referenced by sections: 8.4.3.1

### Figure 17
Referenced by sections: 9.2.4.2.4.4


---

## Annexes: Reverse Lookup

### Annex A
Referenced by sections: 2.4.1

### Annex B
Referenced by sections: 8.1.4.1, 8.1.17.2, 8.2.1.5.2, 8.4.4.7, 8.8.2.3.1.2, 8.8.2.3.2

### Annex C
Referenced by sections: 6.2.1.1

### Annex G
Referenced by sections: 9.1.1.2.7


---

## High-Traffic Tables (Most Referenced)

These tables are critical reference material - ensure they're always available:

1. **Table 6** - Referenced by 6 sections (8.1.16.12, 8.1.16.14, 8.1.17.5, 8.8.1.4.4, 8.8.1.7.2, 9.2.3.1.1)
2. **Table 14** - Referenced by 4 sections (6.2.14.1, 8.4.4.1, 8.4.4.4, 8.4.7.2)
3. **Table 25** - Referenced by 3 sections (8.6.17.1, 8.8.1.6.4, 8.8.1.6.6)
4. **Table 28** - Referenced by 3 sections (8.8.1.8.1, 8.8.3.1.2, 9.2.4.2.4.1)
5. **Table 12** - Referenced by 3 sections (6.2.9.1, 8.2.1.4.2, 8.2.1.4.3)
6. **Table 13** - Referenced by 3 sections (8.1.16.5, 9.2.2.8, 9.2.2.10)

---

## Critical Annex

**Annex B** is the most referenced annex (6 sections reference it):
- 8.1.4.1, 8.1.17.2, 8.2.1.5.2, 8.4.4.7, 8.8.2.3.1.2, 8.8.2.3.2

**Annex G** (100kAIC without test) is referenced by:
- 9.1.1.2.7

---

## Recommended Chunking Groups

Based on cross-references, consider keeping these sections bundled or linked:

### Electrical Connections Cluster (Section 8.8)
- 8.8.1.6.x series (bus bars) → Tables 23, 24, 25
- 8.8.1.8.x → Tables 28, 29
- 8.8.2.3.x → Section 6.2.7.x (markings)
- 8.8.3.x → Tables 30, 31, 32, 33
- 8.8.4.x → Section 8.8.1.8.6

### Enclosure Cluster (Section 8.2)
- 8.2.1.4.x → Table 12
- 8.2.1.5.x → Figures 10, 11, 12 and Annex B

### Protection Cluster (Section 8.4)
- 8.4.4.x → Tables 14, 15 and Annex B
- 8.4.6.x → Sections 8.1.11.x, 8.4.8
- 8.4.7.x → Tables 14, 15

### Switching Devices Cluster (Section 8.6)
- 8.6.5.x → Figures 2, 3
- 8.6.6.8.x → Sections 8.6.8.1, 8.6.15.x
- 8.6.15.x → Table 20
- 8.6.17.x → Table 25

### Test Specifications Cluster (Section 9)
- 9.2.2.x → Tables 13, 35
- 9.2.4.x → Tables 28, 36 and Figure 17
