# Introduction

### What Are Agents?

The term **‘agent’** in its contemporary formal capacity originates from Russell & Norvig’s textbook *Artificial Intelligence: A Modern Approach*. In which they describe an agent as “anything that can be viewed as perceiving its environment through sensors and acting upon that environment through actuators”. 

While contemporary notions of the term ‘Large Language Model (LLM) agents’ can vary widely in definition (particularly given that the ‘LLM’ portion of term can be replaced with the vaguer ‘AI’ (Claude 2025\) or dropped entirely (OpenAI 2025a)); they all subscribe to the model of perceive and act. From a sampling of just three modern respected definitions, one of the only commonalities is that of **independent action** (via tool calling, or otherwise). That is to say, we expect the model to respond to a prompt (environment and goal) with actions to achieve that goal (actuators):

\> “Agentic LLMs are LLMs that (1) reason, (2) **act**, and (3) interact.” (Plaat *et al.* 2025\)

\> “An LLM agent runs **tools** in a loop to achieve a goal.” (Willison 2025a)

\> “Agents are systems that independently **accomplish tasks** on your behalf” (OpenAI 2025b)

The belabouring of this definition is essential for two key reasons: 

- subsequent chapters will rely heavily on the definition we lay out here and,  
- The loaded nature of the term ‘agent’ necessitates from us a clear definition of what we expect agents to be and what we expect them to do. 

To that end, we will synthesize these definitions into one that suits the discussions present in this project: **An agent is a system whose actions are chosen and/or defined by an LLM.**

### “All you need is code”

Recent studies have shown that providing agents with the ability to write and execute code can improve their performance on complex tasks (Wang, Chen, Yuan, Zhang, Li, Peng and Heng 2024). Research such as CodeAct demonstrates that executable Python actions outperform schema based methods (i.e. Model Context Protocol) on benchmarks like API Bank (Li *et al.* 2023a) and M3ToolEval (Wang, Chen, Yuan, Zhang, Li, Peng and Ji 2024\)

Beyond academic results, industry experiments highlight the same trend. Cloudflare recently introduced “Code Mode” in its AI Gateway (Kenton Varda *et al.* 2025), with Anthropic confirming these findings (Anthropic 2025). In parallel, platforms like manus.ai have explored ‘agents as developers’, where models interact with curated libraries to build applications directly (Lu 2025). These efforts suggest that a dedicated, AI oriented development environment could further improve reliability and efficiency.

Recent work and commentary converge on the view that coding agents function as general-purpose agents. Soni et al. show that a minimal toolkit built around code editing and execution, web search, multimodal browsing, and file access achieves generalist performance across diverse benchmarks, supporting the broader claim that developer-style agents extend beyond software-only tasks (Soni *et al.* 2025). Willison’s analysis of Claude Skills underlines the same point, highlighting Claude Code’s use as a general agent, and arguing that the simple, code-centered Skills mechanism enables broad computer automation (Willison 2025b). 

# Aims and Objectives

The primary aim of this project is to leverage these findings to engineer a generalist agent of superior **accuracy** and **usability** when benchmarked against CodeAct, and potentially other benchmarks for agents being operated as ‘generalists’ (AgentBench (Liu *et al.* 2025), Gaia (Mialon *et al.* 2023), Gaia2 (Fourrier *et al.* 2025), ApiBank (Li *et al.* 2023b), BFCL (Patil *et al.* 2025)).  
   
We decompose this aim into several objectives:

## Accuracy

#### “Write code to do stuff.”

The development of an agent to code is not a novel deployment of agentic technology (e.g., (Yang *et al.* 2024)) This is to say, the innovation of this project lies not in the code generation itself, but in the agent's ability to leverage deeply integrated, programmatic interfaces with external environments and services. Essentially, the agent will develop using a singular SDK (henceforth the ‘Wren SDK’) for all supported platforms which has been designed specifically for the agent’s use case. This will provide the integration layer where one might have found the Model Context Protocol in other agents.

#### “Write good code.“

Because we expect agents to develop exclusively for the Wren SDK, we can facilitate a development environment purpose-built for this constraint. For example, we may dynamically limit the LLM's allowed token outputs or adapt the context window to guide generation based on the current syntactic context or development step.

While further development, research, and experimentation are required to solidify the exact systems we employ, our approach is planned to center on three complementary mechanisms:

We’ll use lightweight, progressive typing (hints, inferred shapes, and schema constraints) to communicate intent to the agent and steer generation toward valid, well-formed code. A tight, schema-aware feedback loop will flag mismatches early and nudge the agent toward the correct types, without over-constraining creativity or flow.Targeted linting rules to enforce safe handling and usage patterns akin to SWE-agent which demonstrated that structured linting significantly improves agent-generated code quality (Yang *et al.* 2024). And finally actionable diagnostic feedback that provides specific, contextualized guidance for correction rather than generic error messages.

## Usability

#### “Make it simple to write good code that does stuff.”

Agents are defined not only by the code they execute but by how they interpret and refine a user’s prompt into an actionable plan. The quality of this interpretation (disambiguating goals, surfacing assumptions, and negotiating constraints) often determines downstream reliability more than any single tool call. A responsive interface is therefore part of the agent itself: it mediates the clarification process, captures stable intent, and provides the structured inputs that make execution dependable. To this end, part of our objectives include providing a web-based layer that operates as an interface for the agent, with hosting and monitoring handled by the platform.

Building on that interface, the agent will use the browser UI to ask targeted clarifying questions, pin down what should happen, when, and with which systems, then translate answers into a concrete, executable plan. As it completes tasks, it will snapshot successful workflows as named, typed skills with minimal tests in a searchable registry, enabling reuse and faster, more consistent delivery; this follows evidence from Voyager and Alita that agents benefit from developing their own library of executable skills (Wang et al., 2023; Qiu et al., 2025). The platform underpins this with scheduling, credential management, isolated execution environments, observability across logs, metrics, and traces, and built-in rollback and versioning for safe iteration. Finally, to make plans legible and debuggable, workflows can be rendered as structure-aware views using Python’s AST, where nodes represent actions, conditions, or tools and edges capture data and control flow. 

## 

## Research

### Methodologies

The research methodology for Wren is necessarily forward-looking. Because the area is nascent, recent surveys present provisional taxonomies and acknowledge ongoing flux, our approach can not consist of solely retrospection (Wang, Ma, *et al.* 2024; Luo *et al.* 2025; Sapkota *et al.* 2025).Our approach centers on iterative rapid synthesis, with the aim of tracking how agents are framed, implemented, and evaluated as those practices emerge in real time rather than reconstructing a mature, retrospective narrative.

Primary sources are gathered through systematic keyword searches on Google Scholar and Web of Science, complemented by continuous ingest from RSS feeds, newsroom updates, abstract parsing, and technical blogs. We also monitor developer forums and newsboard discussions (e.g., Hacker News) to capture practice-driven insights as they surface. This mix lets us keep pace with what is happening now, not just what has been formally archived.

A persistent challenge is terminological drift and name collisions, exemplified by “CodeAct,” which has appeared under two titles in prior publications. To mitigate this, we document aliases and provenance for works we cite and verify whether a referenced name maps to the same artifact or a different one. Alongside papers, we follow ongoing commentary from key thinkers (such as Wilson and Wang) and industry directions from OpenAI, Anthropic, Gemini, and Manis, using their updates as additional anchors for what merits closer reading and follow-up analysis.

### Findings and work done to date 

![][image1]  
Fig 1 \- Preliminary architectural design diagram

##### Agent SDK

Our base layer is the agent SDK, because it fixes the execution contract: how tools are invoked, how runs are traced, where guardrails plug in, and how control moves between sub-agents. OpenAI’s Agents SDK is the clearest current exemplar of that contract in one place: it treats tracing as a first-class record of every generation, tool call, handoff, and guardrail verdict, which gives us a single narrative to replay, debug, and audit. This ‘few primitives, production-ready’ posture is attractive for our needs, but we still have yet to validate how well those traces will operate in practice (‘openai/openai-agents-python’ 2025).

Google’s ADK markets a software-engineering style of agent building, modular and nominally model-agnostic, which should compose neatly with our other layers if that modularity holds beyond the happy path (‘google/adk-python’ 2025). Anthropic’s Claude Agent SDK builds directly atop Claude Code’s harness and best practices, promising a pragmatic loop for code-heavy agents; but requires a strong commitment to Claude Code's design patterns and tooling (‘anthropics/claude-agent-sdk-python’ 2025). 

Other options are to be considered, but have yet to be investigated in depth. These include the Langchain (Chase 2022\) and Autogen (‘microsoft/autogen’ 2025\) libraries; and the development specific ‘smolagent’ which aims to solve general requests with code (‘huggingface/smolagents’ 2025\)

#### Designing an agent

We are still converging on a concrete design for the agent itself, but several findings are shaping our direction. From Parlant’s compliance architecture, we take the need to embed guideline enforcement and auditable controls into the core loop, not bolt them on later, so policies are checked as actions are planned and executed (‘How Parlant Guarantees AI Agent Compliance | Parlant’ 2025). We are of course primed to deploy these findings as our agents' primary mode of action will be in an auditable and enforceable medium. Harada et al’s “curse of instructions” warns that models degrade as simultaneous instructions multiply, which argues for keeping the active context small, pruning prompts and tool outputs, and favoring short, focused exchanges (Harada *et al.* 2024). Attentive Reasoning Queries offer a lightweight way to maintain that focus, by steering the model through targeted, task-specific checkpoints when instructions are easy to lose in longer contexts. (Karov *et al.* 2025). As previously discussed, Alita suggests we should minimize predefined tooling and let the agent evolve capabilities over time, keeping the base system simple while supporting skill growth and reuse (Qiu *et al.* 2025). And finally, analyses of Claude Code recommend a pragmatic control loop that relies on a single main thread and a smaller, cheaper model for most orchestration work, reserving larger models for hard hops, an approach we can emulate to control cost and latency without sacrificing reliability (vivek 2025\)

#### Sandboxing (Hard Security Blocks)

Once the SDK defines “act,” we have to make acting safe. 

Sandboxing is our safety boundary. nsjail and bubblewrap are both low level tools that assemble Linux namespaces, rlimits, and seccomp. Bubblewrap is intentionally minimal and leaves policy choices to the caller. (‘containers/bubblewrap’ 2025). Nsjail in contrast, bundles more features in one place, including convenient network setup and seccomp policy files, yet it still relies on external firewall or DNS tooling for per destination rules (‘google/nsjail’ 2025).

We might also consider the **Claude Code** **Sandbox (CCS)** directly which will handle the per destination rules for us. Anthropic’s open-source sandbox runtime exposes allowlists for files and domains and is explicitly designed for code-capable agents (and is built upon bubblewrap) (‘anthropic-experimental/sandbox-runtime’ 2025). While CCS appears to be close to the firewalling we will require, it is relatively new and remains in beta.  Our stance is to evaluate it alongside nsjail and bubblewrap, checking distro support, egress controls, and general suitability. 

## Timeline

**November: Foundations, traceability, and tech stack.** Our intent is to fix scope, evaluation criteria, and architecture while establishing end to end traceability (logging, metrics, run IDs). We will also select core libraries and the tech stack (runtime, sandboxing, storage/queues, observability) and outline how development will proceed from the scaffold.

**Early December: Basic, tangible SDK.** By early December, we aim to begin a minimal but real SDK: action registration, IO contracts, retries/timeouts, credential handling, and seed integrations (mail, calendar, HTTP/RAG). Testing can start immediately by pointing generic agents at this SDK.

**Mid December: Creating an agent.** Our intent is to stand up a baseline agent that uses the SDK to execute simple end to end tasks, exercising clarification, planning, and action loops and producing traceable runs. This provides a living target for subsequent typing, linting, and hardening.

**Late December: Typing and linting.** We plan to layer progressive typing and schema validation over SDK calls, introduce targeted lint rules, and attach actionable diagnostics that guide corrections without over constraining design.

**Early January: Stabilization and hardening.** We intend to tighten isolation and resource policies, address flaky paths surfaced by traces, and standardize error taxonomies and recovery behaviors, expanding observability for regression tracking.

**Late January: Initial web layer.** We aim to commence a minimal web shell that mirrors the operational flow: clarify, plan, execute, observe, with an initial AST view and structured panes for configuration and credentials.

**February: Iterate and evaluate.** Our intent is to iterate the web layer to a usable alpha, refine SDK ergonomics from trace evidence, and run a first benchmark pass to drive targeted fixes and finalize examples.

**March: Writing and editorial consolidation.** We prioritize the dissertation, and begin revision cycles for accuracy, citations, and reproducibility.

**April: Submission and delivery.** We freeze artifacts (repo tag, datasets, harness, configs), produce the polished dissertation, and deliver the final demo; any post freeze changes are limited to non disruptive patches.

## References 

Anthropic (2025) Code Execution with MCP: Building More Efficient AI Agents \[online\], available: https://www.anthropic.com/engineering/code-execution-with-mcp \[accessed 5 Nov 2025\].   
‘anthropic-experimental/sandbox-runtime’ (2025) available: https://github.com/anthropic-experimental/sandbox-runtime \[accessed 5 Nov 2025\].   
‘anthropics/claude-agent-sdk-python’ (2025) available: https://github.com/anthropics/claude-agent-sdk-python \[accessed 3 Nov 2025\].   
Chase, H. (2022) ‘LangChain’, available: https://github.com/langchain-ai/langchain \[accessed 4 Nov 2025\].   
Claude (2024) Introducing the Model Context Protocol \[online\], available: https://www.anthropic.com/news/model-context-protocol \[accessed 28 Oct 2025\].   
Claude (2025) AI Agents \[online\], available: https://www.claude.com/solutions/agents \[accessed 28 Oct 2025\].   
‘containers/bubblewrap’ (2025) available: https://github.com/containers/bubblewrap \[accessed 5 Nov 2025\].   
Fourrier, C., Lecanu, M., Andrews, P., Carreira, A., Frere, T., Ghosh, A., Mekala, D., Pascal, C., Froger, R., and Piterbarg, U. (2025) Gaia2 and ARE: Empowering the Community to Evaluate Agents \[online\], available: https://huggingface.co/blog/gaia2 \[accessed 31 Oct 2025\].   
‘google/adk-python’ (2025) available: https://github.com/google/adk-python \[accessed 3 Nov 2025\].   
‘google/nsjail’ (2025) available: https://github.com/google/nsjail \[accessed 5 Nov 2025\].   
Harada, K., Yamazaki, Y., Taniguchi, M., Kojima, T., Iwasawa, Y., and Matsuo, Y. (2024) ‘Curse of Instructions: Large Language Models Cannot Follow Multiple Instructions at Once’, available: https://openreview.net/forum?id=R6q67CDBCH\&utm\_source=chatgpt.com \[accessed 5 Nov 2025\].   
How Parlant Guarantees AI Agent Compliance | Parlant \[online\] (2025) available: https://parlant.io/blog/how-parlant-guarantees-compliance/ \[accessed 5 Nov 2025\].   
‘huggingface/smolagents’ (2025) available: https://github.com/huggingface/smolagents \[accessed 5 Nov 2025\].   
Karov, B., Zohar, D., and Marcovitz, Y. (2025) ‘Attentive Reasoning Queries: A Systematic Method for Optimizing Instruction-Following in Large Language Models’, available: https://doi.org/10.48550/arXiv.2503.03669.   
Kenton Varda, Sunil Pai, and Cloudflare (2025) Code Mode: The Better Way to Use MCP \[online\], *The Cloudflare Blog*, available: https://blog.cloudflare.com/code-mode/ \[accessed 29 Oct 2025\].   
Li, M., Zhao, Y., Yu, B., Song, F., Li, H., Yu, H., Li, Z., Huang, F., and Li, Y. (2023a) ‘API-Bank: A Comprehensive Benchmark for Tool-Augmented LLMs’, available: https://doi.org/10.48550/arXiv.2304.08244.   
Li, M., Zhao, Y., Yu, B., Song, F., Li, H., Yu, H., Li, Z., Huang, F., and Li, Y. (2023b) ‘API-Bank: A Comprehensive Benchmark for Tool-Augmented LLMs’, available: https://doi.org/10.48550/arXiv.2304.08244.   
Liu, X., Yu, H., Zhang, H., Xu, Y., Lei, X., Lai, H., Gu, Y., Ding, H., Men, K., Yang, K., Zhang, S., Deng, X., Zeng, A., Du, Z., Zhang, C., Shen, S., Zhang, T., Su, Y., Sun, H., Huang, M., Dong, Y., and Tang, J. (2025) ‘AgentBench: Evaluating LLMs as Agents’, available: https://doi.org/10.48550/arXiv.2308.03688.   
Lu, K. (2025) MCP or Not, Manus Made a Choice \[online\], *Medium*, available: https://pub.towardsai.net/mcp-or-not-manus-made-a-choice-40b0a66d2d7c \[accessed 4 Nov 2025\].   
Luo, J., Zhang, W., Yuan, Y., Zhao, Y., Yang, J., Gu, Y., Wu, B., Chen, B., Qiao, Z., Long, Q., Tu, R., Luo, X., Ju, W., Xiao, Z., Wang, Y., Xiao, M., Liu, C., Yuan, J., Zhang, S., Jin, Y., Zhang, F., Wu, X., Zhao, H., Tao, D., Yu, P.S., and Zhang, M. (2025) ‘Large Language Model Agent: A Survey on Methodology, Applications and Challenges’, available: https://doi.org/10.48550/arXiv.2503.21460.   
Mialon, G., Fourrier, C., Swift, C., Wolf, T., LeCun, Y., and Scialom, T. (2023) ‘GAIA: a benchmark for General AI Assistants’, available: https://doi.org/10.48550/arXiv.2311.12983.   
‘microsoft/autogen’ (2025) available: https://github.com/microsoft/autogen \[accessed 4 Nov 2025\].   
OpenAI (2025a) Agents \[online\], available: https://platform.openai.com \[accessed 28 Oct 2025\].   
OpenAI (2025b) A-Practical-Guide-to-Building-Agents \[online\], available: https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf \[accessed 28 Oct 2025\].   
‘openai/openai-agents-python’ (2025) available: https://github.com/openai/openai-agents-python \[accessed 3 Nov 2025\].   
Patil, S.G., Mao, H., Yan, F., Ji, C.C.-J., Suresh, V., Stoica, I., and Gonzalez, J.E. (2025) ‘The Berkeley Function Calling Leaderboard (BFCL): From Tool Use to Agentic Evaluation of Large Language Models’, Presented at the Forty-second International Conference on Machine Learning, available: https://openreview.net/forum?id=2GmDdhBdDk \[accessed 31 Oct 2025\].   
Plaat, A., Duijn, M. van, Stein, N. van, Preuss, M., Putten, P. van der, and Batenburg, K.J. (2025) ‘Agentic Large Language Models, a survey’, available: https://doi.org/10.48550/arXiv.2503.23037.   
Qiu, J., Qi, X., Zhang, T., Juan, X., Guo, J., Lu, Y., Wang, Y., Yao, Z., Ren, Q., Jiang, X., Zhou, X., Liu, D., Yang, L., Wu, Y., Huang, K., Liu, S., Wang, H., and Wang, M. (2025) ‘Alita: Generalist Agent Enabling Scalable Agentic Reasoning with Minimal Predefinition and Maximal Self-Evolution’, available: https://doi.org/10.48550/arXiv.2505.20286.   
Sapkota, R., Roumeliotis, K.I., and Karkee, M. (2025) ‘AI Agents vs. Agentic AI: A Conceptual Taxonomy, Applications and Challenges’, *Information Fusion*, 126, 103599, available: https://doi.org/10.1016/j.inffus.2025.103599.   
Soni, A.B., Li, B., Wang, X., Chen, V., and Neubig, G. (2025) ‘Coding Agents with Multimodal Browsing are Generalist Problem Solvers’, available: https://doi.org/10.48550/arXiv.2506.03011.   
vivek (2025) What Makes Claude Code so Damn Good (and How to Recreate That Magic in Your Agent)\!? \[online\], *minusx.ai*, available: https://minusx.ai/blog/decoding-claude-code/ \[accessed 5 Nov 2025\].   
Wang, L., Ma, C., Feng, X., Zhang, Z., Yang, H., Zhang, J., Chen, Z., Tang, J., Chen, X., Lin, Y., Zhao, W.X., Wei, Z., and Wen, J. (2024) ‘A survey on large language model based autonomous agents’, *Frontiers of Computer Science*, 18(6), 186345, available: https://doi.org/10.1007/s11704-024-40231-1.   
Wang, X., Chen, Y., Yuan, L., Zhang, Y., Li, Y., Peng, H., and Heng, J. (2024) ‘CodeAct: Your LLM Agent Acts Better when Generating Code’, in *ICML*, available: https://arxiv.org/abs/2402.01030.   
Wang, X., Chen, Y., Yuan, L., Zhang, Y., Li, Y., Peng, H., and Ji, H. (2024) ‘Executable Code Actions Elicit Better LLM Agents’, available: https://doi.org/10.48550/arXiv.2402.01030.   
Willison, S. (2025a) I Think “Agent” May Finally Have a Widely Enough Agreed upon Definition to Be Useful Jargon Now \[online\], *Simon Willison’s Weblog*, available: https://simonwillison.net/2025/Sep/18/agents/ \[accessed 28 Oct 2025\].   
Willison, S. (2025b) Claude Skills Are Awesome, Maybe a Bigger Deal than MCP \[online\], *Simon Willison’s Weblog*, available: https://simonwillison.net/2025/Oct/16/claude-skills/ \[accessed 3 Nov 2025\].   
Yang, J., Jimenez, C.E., Wettig, A., Lieret, K., Yao, S., Narasimhan, K., and Press, O. (2024) ‘SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering’, available: https://doi.org/10.48550/arXiv.2405.15793.   


