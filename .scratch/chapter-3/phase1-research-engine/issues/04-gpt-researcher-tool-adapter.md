# 04: GPT-Researcher Tool Adapter

**What to build:** Bridge the gap between ODR's execution flow and GPT Researcher's deep crawling capabilities. By wrapping GPT Researcher as a standard LangChain tool, ODR maintains total control over the research loop (single control plane) while leveraging advanced retrieval.

**Blocked by:** 02: Upstream Vendoring & Dependencies.

**Status:** ready-for-agent

- [ ] Create `app/integrations/research_engine/tools/gpt_researcher_tool.py`.
- [ ] Implement a LangChain `BaseTool` subclass (or `@tool` decorated function) that initializes and runs the `GPTResearcher` API programmatically.
- [ ] Ensure the tool accepts a specific sub-topic or query and returns the structured summary output from GPT Researcher.
- [ ] Write a unit test ensuring the tool initializes correctly and conforms to the expected LangChain tool schema.
