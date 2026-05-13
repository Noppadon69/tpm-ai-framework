# Arize Phoenix — RAG eval + hallucination detection (self-hosted)

Catalogued in MASTER_PLAN_v6.md § 17.2 H. Becomes the **Layer 6 semantic eval**
in the Auditor pipeline (currently deferred per `tpm_workers/auditor.py`
docstring: "7 of 8 layers implemented; Phoenix semantic eval deferred until
Arize infrastructure exists").

**Status as of 2026-05-13:** scaffolded, not yet wired. Auditor runs the
other 7 layers without it.

---

## Activate

```bash
cd services/arize_phoenix
docker compose up -d
# UI:        http://localhost:6006
# OTLP gRPC: localhost:4317  (for ingesting traces)
```

Resource cost: ~300 MB RAM, CPU only. No GPU needed.

---

## Wire into Auditor (when ready)

1. `.env`:
   ```
   PHOENIX_HOST=http://localhost:6006
   PHOENIX_COLLECTOR_ENDPOINT=http://localhost:4317
   ```
2. In `tpm_workers/auditor.py` — implement the deferred `layer_6_semantic()`:
   ```python
   from phoenix.evals import HallucinationEvaluator, llm_classify
   # score retrieved_context vs answer; threshold 0.7
   ```
3. Add Phoenix span instrumentation in `tpm_core/orchestrator.py` via
   `openinference-instrumentation-langchain` (already implied by Langfuse
   integration — both can coexist on the same trace).

---

## Decision gate

Activate when ANY hits:
- First real Toshiba RAG result triggers user complaint ("answer not in source")
- § 15.8 Vision-RAG cross-check enters implementation phase
- Reflexion (§ 15.7) needs a richer judge than the current rule-based Auditor
