# Contributing to sdnd-proof

Thank you for your interest in this research.

---

## What This Repository Is

This is the implementation and results of a single controlled experiment:

> Does network structure matter more than model capability
> in multi-LLM systems?

It is not a framework, library, or production system.
It is a scientific record.

---

## How You Can Contribute

### 1. Reproduce the Experiment

The most valuable contribution is independent reproduction.

Run the experiment on your own hardware with your own models.
Report your results — whether they confirm or contradict ours.

Open an Issue with:
- Your hardware specifications
- The model you used
- Your results (accuracy table + statistical output)
- Any differences from our setup

Contradicting results are as welcome as confirming ones.

### 2. Report Issues

If you find bugs in the implementation, open an Issue.
Include the error message and your environment.

### 3. Propose Amendments to constitution.md

If you believe the safety design has gaps, open an Issue.
Describe the gap and your proposed solution.

Amendments require approval from the CODEOWNERS
as defined in constitution.md Article 10.

### 4. Extend the Experiment

If you run follow-up experiments (different models, tasks, scales),
open an Issue to share your findings.

We are particularly interested in:
- Results with models other than qwen2.5:3b
- Results on tasks other than world-consistency detection
- Results at larger scales (10+ nodes)
- Results in internet-connected environments
  (with safety design documentation as required by LICENSE.md)

---

## What We Ask

- Use your real name or a consistent handle
- State your results honestly, including negative results
- Read constitution.md before deploying any derived system
- Read the Internet Connectivity Warning in LICENSE.md

---

## What We Do Not Accept

- Pull Requests that remove or weaken safety constraints
- Pull Requests that modify constitution.md Articles 3, 8-2, or the Preamble
- Issues that advocate for removing the safety design

---

*pipe_render (村下 勝真 / KATSUMA MURASHITA)*
*robosheep.and@gmail.com*
