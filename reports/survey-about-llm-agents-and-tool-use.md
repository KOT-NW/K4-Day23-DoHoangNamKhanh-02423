# LLM Agents and Tool Use: A Research Survey

## TL;DR
- When retrieved evidence contradicts an agent's prior beliefs, does it revise its answer, acknowledge uncertainty, or persist with an incorrect conclusion? [1]
- Runtime monitors are increasingly used to improve the reliability of LLM-based coding agents by inspecting execution trajectories and delivering corrective guidance upon detecting misbehavior. [2]
- PlanBench-XL evaluates large language model agents' ability to plan and adapt in complex tool-rich environments with limited visibility and dynamic disruptions. [3]

## Background
This survey examines llm agents and tool use through published paper abstracts and Hugging Face paper summaries. The selected sources describe distinct research questions within the topic. [1][2]

## Approaches and representations
In *Accurate but Not Humble: Evaluating Epistemic Humility in LLM Agents under Knowledge Conflict*, when retrieved evidence contradicts an agent's prior beliefs, does it revise its answer, acknowledge uncertainty, or persist with an incorrect conclusion? [1] *Cadence: Strategic Guidance for Coding Agents* places emphasis elsewhere: runtime monitors are increasingly used to improve the reliability of LLM-based coding agents by inspecting execution trajectories and delivering corrective guidance upon detecting misbehavior. [2] The two abstracts describe different targets, so their claims should be compared by setting and evidence rather than treated as one shared score. [1][2]

## Training and evidence
In *PlanBench-XL: Evaluating Long-Horizon Planning of LLM Tool-Use Agents in Large-Scale Tool Ecosystems*, planBench-XL evaluates large language model agents' ability to plan and adapt in complex tool-rich environments with limited visibility and dynamic disruptions. [3] *FinToolBench: Evaluating LLM Agents for Real-World Financial Tool Use* places emphasis elsewhere: finToolBench presents the first real-world benchmark for evaluating financial tool learning agents, featuring 760 executable tools and comprehensive evaluation criteria beyond simple execution success. [4] The two abstracts describe different targets, so their claims should be compared by setting and evidence rather than treated as one shared score. [3][4]

## Applications and trade-offs
In *SSCBench: Evaluating the Evidential Validity of Fault-Injection Tests for Tool-Using LLM Agents*, fault injection is increasingly used to evaluate the reliability of tool-using LLM agents. [5] *NOMOS: Compiling Written Policies into Statically Verified Tool-Call Gates for LLM Agents* places emphasis elsewhere: tool-using LLM agents violate the policies they are deployed to enforce, often silently. [6] The two abstracts describe different targets, so their claims should be compared by setting and evidence rather than treated as one shared score. [5][6]

## Trends and open problems
The newest papers in this sample broaden the range of methods and tasks under study:
- *Accurate but Not Humble: Evaluating Epistemic Humility in LLM Agents under Knowledge Conflict* (2026-10-08): When retrieved evidence contradicts an agent's prior beliefs, does it revise its answer, acknowledge uncertainty, or persist with an incorrect conclusion? [1]
- *Cadence: Strategic Guidance for Coding Agents* (2026-10-08): Runtime monitors are increasingly used to improve the reliability of LLM-based coding agents by inspecting execution trajectories and delivering corrective guidance upon detecting misbehavior. [2]
- *SSCBench: Evaluating the Evidential Validity of Fault-Injection Tests for Tool-Using LLM Agents* (2026-10-08): Fault injection is increasingly used to evaluate the reliability of tool-using LLM agents. [5]
- Another relevant record is *From Evidence to Action: How Tool-Using Agents Fail*: Tool-using agents make consequential changes to external state, yet correct outcomes do not guarantee that their actions were supported by evidence established beforehand. [7]

A useful next step is to test these approaches on comparable tasks and to examine where conclusions from one setting transfer to another. The cited abstracts provide distinct cases for that comparison. [1][2][5]

## References
[1] Accurate but Not Humble: Evaluating Epistemic Humility in LLM Agents under Knowledge Conflict. arxiv. https://arxiv.org/abs/2610.12360 (2026-10-08)
[2] Cadence: Strategic Guidance for Coding Agents. arxiv. https://arxiv.org/abs/2610.12269 (2026-10-08)
[3] PlanBench-XL: Evaluating Long-Horizon Planning of LLM Tool-Use Agents in Large-Scale Tool Ecosystems. hf-search. https://huggingface.co/papers/2606.22388 (2026-06-21)
[4] FinToolBench: Evaluating LLM Agents for Real-World Financial Tool Use. hf-search. https://huggingface.co/papers/2603.08262 (2026-03-09)
[5] SSCBench: Evaluating the Evidential Validity of Fault-Injection Tests for Tool-Using LLM Agents. arxiv. https://arxiv.org/abs/2610.11514 (2026-10-08)
[6] NOMOS: Compiling Written Policies into Statically Verified Tool-Call Gates for LLM Agents. arxiv. https://arxiv.org/abs/2610.11030 (2026-10-08)
[7] From Evidence to Action: How Tool-Using Agents Fail. hf-daily. https://huggingface.co/papers/2610.07753 (2026-10-06)
