# Langfuse — LLM trace + prompt versioning (self-hosted)

Catalogued in MASTER_PLAN_v6.md § 17.2 H. Provides:
- Trace every LLM call (orchestrator → workers) with inputs/outputs/tokens
- Prompt version registry (swap prompts without code change once wired)
- Datasets + offline eval scoring (Phase 5 DSPy input)

**Status as of 2026-05-13:** scaffolded, not yet wired into tpm_core.
Auditor + Reflexion run without it. Activate when ≥ 1 week of real
internship traces would yield signal.

---

## Activate

```bash
cd services/langfuse
docker compose up -d
# UI: http://localhost:3000  (first launch → sign up local owner account)
```

Resource cost: postgres ~50 MB RAM + langfuse server ~200 MB RAM. CPU only.

---

## Wire into tpm_core (when ready)

1. After signup → Settings → API Keys → create project keys
2. `.env`:
   ```
   LANGFUSE_HOST=http://localhost:3000
   LANGFUSE_PUBLIC_KEY=pk-lf-...
   LANGFUSE_SECRET_KEY=sk-lf-...
   ```
3. Wrap the LLM client in `tpm_core/llm.py`:
   ```python
   from langfuse.openai import openai  # drop-in replacement
   # ...or use langfuse.decorators.observe on the call
   ```
4. Confirm traces appear in UI → check token costs by session_id.

---

## Decision gate

Activate when ANY hits:
- ≥ 50 real Toshiba sessions/week (sample-rich enough for prompt-tuning)
- Phase 5 DSPy prep (needs trace dataset)
- User report of "AI gave wrong answer, no way to debug"
