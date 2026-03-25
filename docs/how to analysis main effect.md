
# Experimental Design and Analysis Notes

## 1. Experimental Structure

### Factors

- **A: Village Relationship (分类变量)**
  - A1 = Same village
  - A2 = Different village

- **B: Distance (分类变量)**
  - B1 = Nearest
  - B2 = Near
  - B3 = Far
  - B4 = Unknown

### Observed Structure

- A1 → B1 only
- A2 → B2, B3, B4

Not observed:
- A1–B2/B3/B4
- A2–B1

### Key Property

- Distance levels are **conditionally defined within A**
- Therefore:
  
  > **B is nested within A**

---

## 2. Design Classification

### Not a Factorial Design

A factorial design requires full crossing:

|        | B1 | B2 | B3 | B4 |
|--------|----|----|----|----|
| A1     | ✔  | ✔  | ✔  | ✔  |
| A2     | ✔  | ✔  | ✔  | ✔  |

This condition is not met.

### Correct Classification

> **Unbalanced Nested Design**

More precisely:
- B nested within A: `B(A)`
- Unequal number of B levels across A → unbalanced

---

## 3. Identifiability Issue

### Structural Confounding

- A1 is perfectly tied to B1
- A2 is tied to B2/B3/B4

Therefore:

> **A and B effects are not separable (non-identifiable)**

Implications:
- Cannot estimate independent main effects of A and B
- No valid A × B interaction
- No shared reference level across A

---

## 4. Role of Mixed Models

### Model Form

```

Y ~ A + B(A) + (1 | Subject)

```

or

```

Y ~ Condition + (1 | Subject)

```

### What Mixed Models Can Do

- Handle:
  - Unbalanced data
  - Nested structure
  - Random effects (e.g., subjects)
- Provide:
  - Overall A comparison (with confounding)
  - Clean comparisons within A2 (B2 vs B3 vs B4)

### What They Cannot Do

> Mixed models **cannot recover independent A and B effects**

Reason:
- Missing combinations are structural, not random
- No statistical method can infer absent comparisons

---

## 5. Recommended Analysis Strategies

### Strategy 1: Decomposition Approach

#### (1) Overall A Effect

```

Y ~ A + (1 | Subject)

```

Interpretation:
- Same-village (nearest) vs different-village (mixed distances)
- Not a pure A effect

#### (2) Distance Effect Within A2

```

Y ~ Distance (B2/B3/B4) + (1 | Subject)

```

Interpretation:
- Valid test of distance effect
- Restricted to A2

---

### Strategy 2: Single Factor Encoding (Preferred)

Define:

```

Condition:

* C1 = A1-B1
* C2 = A2-B2
* C3 = A2-B3
* C4 = A2-B4

```

Model:

```

Y ~ Condition + (1 | Subject)

```

Advantages:
- Statistically clean
- No artificial factor separation
- Supports planned contrasts

---

## 6. Reporting Guidance

Key statement required:

> Distance and village relationship are partially confounded due to design constraints.

Recommended phrasing:

- Distance is nested within village condition
- The nearest distance occurs only in same-village trials
- Effects cannot be fully disentangled

Avoid:
- Claiming independent main effects of A and B
- Referring to the design as factorial

---



## 7. Design Limitation and Resolution

### Core Limitation

> Missing cells are structural → effects are not identifiable

### Only True Solution

Adopt a fully crossed design:

|        | Nearest | Near | Far | Unknown |
|--------|--------|------|-----|---------|
| Same   | ✔      | ✔    | ✔   | ✔       |
| Different | ✔   | ✔    | ✔   | ✔       |

---

## 8. Final Summary

- The design is:
  > **Unbalanced nested design (B nested within A)**

- Key issue:
  > **A and B are structurally confounded**

- Mixed models:
  > Improve estimation but do not resolve confounding

- Best practice:
  > Treat conditions as a single factor or analyze within valid subsets

- Critical principle:
  > **Statistical methods cannot compensate for missing experimental structure**

