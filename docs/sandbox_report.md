Skip to content
Chat history
You said:
I'm working on an ai agents and i need a sandbox for code they run/actions they make. Compare these (and other) options. I want simple to use (one command to spin up a vm/container/whatever I want (if possible) conditional blocking (e.g. block web access except to a certain url, block bash commands starting with ls until user approval etc) I want foss (is possible) Options: https://github.com/liquidmetal-dev/flintlock https://github.com/e2b-dev https://www.daytona.io https://modal.com/ https://render.com/ https://github.com/PwnFunction/sandbox https://judge0.com/ https://gist.github.com/mavdol/2c68acb408686f1e038bf89e5705b28c https://firecracker-microvm.github.io/
ChatGPT said:

Thanks for sharing your requirements and initial list. To better compare and recommend the most suitable sandboxing environments for your AI agents, could you clarify the following:

    Primary Language/Tech Stack: Are you working mainly in Python, Node.js, or another language?

    Runtime Environment: Do you need support for running full operating systems (like microVMs), just user code (like function sandboxes), or containerized environments?

    Preferred Hosting: Do you plan to run this locally, on your own servers, or use a cloud-hosted solution?

    Security Level: How strict should the sandboxing be? Are you expecting untrusted code or just want isolation?

    Budget Constraints: Do you want only free/open-source options, or are managed/commercial services also acceptable if they offer convenience?

With these details, I’ll compare your listed tools and others for sandboxing suitability.
You said:
1. python
2. All of the above; draw comparisions in your final report. 
3. All of the above
4. Isolation is really what we are after, but the AI could delete all files or do something dumb
5. FOSS is important, but if something is perfect and cheap bring it up
ChatGPT said:

Got it. I’ll compare sandboxing solutions for running AI agents with a focus on Python support, isolation, ease of use, conditional execution blocking, and FOSS preference. I’ll include all the tools you listed and any other relevant ones.

I’ll let you know when the detailed comparison is ready — feel free to keep chatting with me in the meantime.
ChatGPT said:
Comparing Sandbox Options for AI Agent Code Execution

AI agents that can generate and execute code pose significant security risks. To safely run AI-generated code (which could otherwise delete files, leak data, or perform malicious actions), we need strong sandboxing and isolation
gist.github.com
. Below we compare several sandboxing options – focusing on ease of use (ideally one-command setup), isolation strength, ability to restrict specific actions, and open-source availability. We group the solutions into microVM-based and container-based sandboxes, then discuss emerging WebAssembly sandboxes and methods for fine-grained control (conditional blocking of actions).
MicroVM-Based Sandboxes (Strong Isolation)

MicroVMs use lightweight virtual machines (like Amazon’s Firecracker) to provide VM-level isolation with minimal overhead. Each sandbox gets its own virtualized kernel, isolating it from the host at a very high level of security
gist.github.com
. This greatly limits the damage if an AI agent’s code tries something nefarious (it can only affect the VM, not the host). The trade-offs are higher startup overhead and complexity compared to containers
gist.github.com
. Notable microVM-based options include:

    Firecracker MicroVM: An open-source virtualization technology from AWS that runs on KVM. Firecracker was built for AWS Lambda to securely run untrusted workloads at scale. It’s “secure by default” (thanks to minimal device emulation and a very limited interface)
    gist.github.com
    . However, using Firecracker directly isn’t one-command simple – you must supply a kernel and root filesystem image and configure networking, etc. It’s Linux-only and introduces more resource overhead for each sandbox (since each has its own kernel)
    gist.github.com
    . Firecracker is a great foundation if maximum isolation is required, but on its own it’s low-level.

    Flintlock: An open-source service by the CNCF Liquid Metal project, designed to make microVMs easy to use. Flintlock acts as a management layer to create and lifecycle microVMs via API/CLI calls
    github.com
    . It integrates with containerd, meaning you can spin up a microVM from an OCI container image in a relatively straightforward way. Flintlock supports Firecracker and Cloud Hypervisor VMMs
    github.com
    . This can give you “one command” style creation of a microVM (once Flintlock is set up as a daemon). It’s useful for isolated workloads and pipelines
    github.com
    . Pros: Fully open source (MPL 2.0) and flexible. Cons: You need to run the flintlock service on a host machine (or cluster), and it’s more devops-heavy than a hosted sandbox service.

    E2B (Execute to Build): E2B is an open-source infrastructure and cloud service focused on running AI-generated code in secure sandboxes
    github.com
    . Under the hood it uses Firecracker microVMs for true VM isolation
    northflank.com
    . The big advantage of E2B is its ease of use: you install their SDK (Python or TypeScript) and with a few lines can spin up a sandbox and run code inside it
    github.com
    github.com
    . It supports multiple languages (Python, JavaScript/TypeScript, R, Java, Bash, etc.) and even allows persistent sandboxes (up to 24 hours active, or up to 30 days in a paused state)
    northflank.com
    . This persistence is useful if the agent needs to maintain state across interactions. E2B’s hosted service requires an API key (they haven’t published transparent pricing yet)
    northflank.com
    . They also provide a way to self-host the infrastructure via Terraform on cloud providers
    github.com
    , though self-hosting is noted to be “still experimental (not production-ready)”
    northflank.com
    . Pros: True microVM isolation without heavy lifting, multi-language, very simple developer experience. Cons: Hosted model means trusting a third-party (unless you self-host), and it’s focused purely on code sandboxes (cannot run full apps or services)
    northflank.com
    .

    Concave Sandbox (PwnFunction/sandbox): Concave is a self-hostable platform (MIT-licensed) for running untrusted AI code, built on Firecracker microVMs
    github.com
    . It aims for both security and speed. Concave uses snapshot-based VM pooling to achieve startup times around 200ms despite using VMs
    github.com
    . In practice, you deploy their stack (with Terraform/Ansible as per their guides) on your cloud – it sets up Firecracker on bare metal or VMs, plus orchestration via gRPC and an HTTP API
    github.com
    github.com
    . A Python SDK is provided for integration. Essentially, Concave offers similar benefits to E2B (secure microVM per execution, with an API/SDK to manage them). It’s fully open source and “runs untrusted AI code safely, fast”
    github.com
    . Pros: Strong isolation with Firecracker, open source and self-hostable, optimized with snapshots for performance. Cons: Requires significant setup (not a single binary but a whole distributed setup with Nomad, etc.), and is a very new project (the community is small so far).

    Vercel Sandboxes (Hive): Vercel (a deployment platform) introduced an “AI Sandbox” feature for development previews, which also uses Firecracker microVMs under the hood
    northflank.com
    . It’s mainly intended for ephemeral dev environments (Node.js or Python) rather than production agent runtime. The isolation is strong (each sandbox in a microVM), and provisioning is pretty fast. But there are strict limits – e.g. sandboxes last max ~45 minutes, have no persistence, and are tied to Vercel’s workflow
    northflank.com
    . This could be useful for testing, but it’s not geared for long-running AI agents in production.

In summary, microVM-based solutions offer the highest isolation. If the AI agent goes rogue, it’s trapped in a lightweight VM – it could destroy the VM’s filesystem or try kernel exploits, but the blast radius is the VM itself. The downside is more overhead: Firecracker VMs are lightweight compared to full VMs, but still heavier than just a container or a function call (they incur a memory and startup time cost). Projects like Flintlock, E2B, and Concave mitigate this with management layers and snapshotting to approach the convenience of containers. For one-command simplicity with microVMs, E2B’s SDK or Concave’s API might be the closest fit, whereas Flintlock is more of a building block if you don’t mind some infra work.
Container-Based Sandboxes (Speed & Convenience)

Container-based sandboxes rely on OS-level virtualization (namespaces, cgroups, etc.) to isolate the code. A container is essentially a process (or set of processes) running on the host kernel, but isolated in terms of filesystem, network, etc. Containers are much faster to start than VMs (often sub-second), and easier to manage (Docker has one-line run). However, vanilla containers share the kernel, so a malicious code with a kernel exploit could escape, and any allowed system call runs on the host. To harden container sandboxes, projects employ additional isolation layers like gVisor or Kata Containers.

Figure: Illustration of container isolation approaches. Left: Standard containers (insecure) run processes on a shared host kernel (a container escape can compromise the host). Center: Kata Containers (secure) launch each container inside a lightweight VM (using an optimized hypervisor like Firecracker or Cloud Hypervisor), giving each container an isolated guest kernel
northflank.com
. Right: gVisor (secure) intercepts system calls in user space (runsc), acting as a lightweight kernel emulator between the app and host kernel
gist.github.com
. Both Kata and gVisor add isolation at the cost of some performance.

Key container-based sandbox options:

    Daytona: Daytona is a platform specifically for running AI-generated code safely. It’s open source (AGPL-3.0) and provides an SDK (Python/TypeScript) to spin up sandboxes on their infrastructure or yours
    github.com
    github.com
    . By default, Daytona prioritizes speed by using standard Docker containers for sandboxes
    northflank.com
    . In this default mode, startup is extremely fast (they claim “sub-90ms sandbox creation”)
    github.com
    , but isolation is the same as a normal container. However, Daytona can be configured to use Kata Containers or Sysbox for enhanced isolation
    northflank.com
    . Using Kata means each “container” actually runs in a microVM (improving security at the cost of some latency). This tiered security approach lets you trade off isolation vs. speed based on your needs
    northflank.com
    . Daytona also supports stateful sandboxes – you can keep a sandbox running indefinitely (with files and state preserved) rather than only ephemeral runs
    github.com
    . And it’s compatible with any Docker/OCI image as the sandbox base, so you can customize the runtime environment (e.g. include specific libraries)
    github.com
    . Pros: Very fast startup in default mode, flexible isolation options, open source with self-host or hosted service, good integration for AI agent use cases (files, git operations, etc., via their SDK). Cons: If you require the stronger isolation, you must explicitly use Kata/Sysbox and accept slower startup
    northflank.com
    ; as a young project, you’ll want to stay on top of updates. Also, it’s focused on the sandbox task – not a full cloud platform, so things like multi-tenant orchestration or databases require other tools
    northflank.com
    .

    Modal: Modal is a managed cloud service (proprietary) often mentioned in the context of ML and AI workloads. It provides a serverless-like experience to run Python code in isolated containers. Under the hood, Modal uses gVisor (the runsc runtime) to add a layer of isolation to its containers
    northflank.com
    . From a developer perspective, you write Python functions or apps and deploy them on Modal – it handles packaging into a container, and it will start/stop those container instances on demand. Startup times are very low (Modal built a custom Rust runtime to achieve sub-second cold starts)
    northflank.com
    . It also has strong support for GPUs, which is useful if your AI code needs acceleration
    northflank.com
    . Modal’s downsides are its opinionated nature: it’s Python-only (you can only define functions in Python, though you can call external binaries within that)
    northflank.com
    , and you can’t self-host or BYO cloud – you must use Modal’s service (no open-source offering)
    northflank.com
    . There’s also no concept of persistent long-lived sandbox; it’s more like serverless functions (though you can keep a function “container” alive for some time or reuse it). Pros: Very easy to use for Python developers, fast and scalable, with an added security layer (gVisor) behind the scenes. Likely sufficient for many AI code tasks if they fit into a Python function model. Cons: Not FOSS, limited to Python, and if you need to allow other languages or long-running stateful services, Modal isn’t the right fit
    northflank.com
    .

    Render: Render.com is a general-purpose PaaS (Platform as a Service) similar to Heroku. While not a dedicated sandbox service, you can use Render to deploy your AI agent in an isolated environment relatively easily. For example, you might run the agent in a Docker container on Render, or use a one-command deploy of a small VM instance. Render will isolate your service from other tenants, but note this is standard isolation (containers/VMs on their cloud, with normal Linux security). It doesn’t provide special guardrails for untrusted code beyond what any Linux container VM does. In practice, you could set up a “job” or background worker on Render that spins up on demand to execute AI-generated code, then shuts down. It’s simple (they handle the infra), and cheap for low volumes (they have free tiers and usage-based pricing). Pros: Very user-friendly deployment, supports any language/runtime, can scale up to production. Cons: Not specialized for sandboxing – no fine-grained controls out of the box. You’d have to implement restrictions yourself (e.g. ensure your container runs with a read-only filesystem or no network access if needed). Essentially, Render is a convenient way to run isolated processes, but it’s not secure-by-default against a determined malicious code (beyond Docker’s default isolation, which is weaker than Firecracker or gVisor
    gist.github.com
    ).

    Judge0: Judge0 is an open-source online code execution system commonly used for coding challenge platforms and IDEs. It’s relevant here because it provides a ready-made sandbox API that supports over 60 programming languages
    judge0.com
    judge0.com
    . With Judge0, you (or your AI agent) can send code to a REST API, and it will run that code in an isolated environment and return the output. It uses Docker containers under the hood for isolation, typically with resource limits and no network access for the running code by default (to prevent abuse) – indeed, it advertises “sandboxed compilation and execution”
    judge0.com
    . Judge0 is self-hostable (you can run their Docker images or Kubernetes charts) and also offered as a hosted service (with a free tier and paid tiers)
    judge0.com
    . It has been used in production by many services, so it’s fairly robust. However, since it’s container-based, one has to keep it updated for security. (Notably, there have been past vulnerabilities that allowed sandbox escape or SSRF, which were patched
    securityweek.com
    – a reminder that you must configure things like seccomp profiles properly.) Pros: Very easy “black box” to use – essentially one API call to run code – supporting many languages out of the box. Open source and widely tested. Cons: Limited control over the execution environment beyond what their API allows (though you can configure base images). It’s geared toward short-running code evaluation, not running a long-lived agent. And it doesn’t provide interactive control over system calls; it simply sandboxes with Linux container isolation. This means conditional blocking of specific actions isn’t a feature – you either trust the container’s restrictions or not.

    Do-It-Yourself with Docker + gVisor/Kata: If none of the above fully meet your needs, you can always build your own sandbox script. For example, using Docker directly can be as simple as:

    docker run --rm -it --network=none --security-opt seccomp=someProfile.json sandbox_image:latest python run_agent.py

    This would start a container with no network, and you could supply a seccomp profile that, say, forbids certain syscalls or enforces read-only filesystem, etc. To tighten security, you could swap Docker’s default runtime for gVisor (docker run --runtime=runsc ...) to intercept syscalls in user space
    gist.github.com
    . Or use Kata Containers as the runtime to actually give each container its own mini-VM (utilizing technologies like KVM or Cloud Hypervisor)
    northflank.com
    . These approaches are open-source and give a lot of control. The downside is complexity – you’ll be stitching together pieces (Docker, custom seccomp/AppArmor profiles, perhaps firewall rules for network whitelisting) and it may not be “one command” for the end-user unless you wrap it in a script. Kubernetes-based platforms (like Northflank or others) essentially automate this by scheduling sandbox containers with Kata or gVisor, but those tend to be commercial services
    northflank.com
    . If you prefer FOSS, both gVisor and Kata Containers are open projects you can use in your own infrastructure.

WebAssembly Sandboxes (Emerging Option)

Another intriguing option is using WebAssembly (WASM) as a sandbox for running code. WebAssembly was designed with sandboxing in mind – WASM modules run in a virtual machine that by default has no access to the host’s filesystem, network, or other resources unless explicitly provided. In other words, a WASM runtime won’t let the guest code do anything except pure computation and memory, unless the host app gives it specific APIs. This makes it secure by default and great for fine-grained sandboxing
gist.github.com
.

For AI agents, there are projects exploring WASM to run Python code or other tasks safely. For example, one could compile a Python interpreter to WASM (there are initiatives to get CPython or subsets of it running under WASI, the WebAssembly System Interface) and execute AI-generated Python code inside that. The advantage is extremely fast startup and low overhead (no separate OS or heavy context switch – it can be as fast as running a function in-process), plus the ability to whitelist specific capabilities (e.g. allow the WASM module to call a “fetch URL” function but not direct socket access, or allow writing to a virtual /tmp but nowhere else). This aligns with the principle of least privilege perfectly – you can grant exactly the permissions the agent needs and nothing more.

Current state: WebAssembly sandboxing for general code is still maturing. Pure Python logic can run in WASM (projects like Pyodide or wasmMicroPython exist), but C extensions and native libraries don’t work out-of-the-box. Many AI libraries (NumPy, Pandas, Torch, etc.) rely on C/C++ extensions, which either need special handling or aren’t supported in the WASM environment yet
gist.github.com
. So, today, a WASM sandbox might handle simple Python code well (and safely), but heavy ML code might fail or be too slow under interpretation. That said, this field is progressing rapidly. Companies like NVIDIA have explored “sandboxing agentic AI workloads with WebAssembly”
developer.nvidia.com
, and open-source efforts (e.g. the capsule project mentioned in the sandboxing gist) are underway to make it easy – for instance, by adding a decorator to functions to run them in a WASM sandbox
gist.github.com
.

Bottom line: If your AI agents mostly do logic, or you can compile the specific tools they need to WASM, this route gives you an extremely robust sandbox with fine control. It’s fully open source (multiple WASM runtimes to choose from, like Wasmtime, Wasmer, etc.) and can even run inside a browser for additional safety. In the near future, we may see combined approaches – e.g. an AI agent’s Python environment running in a Firecracker microVM and inside it each task running in a WASM sandbox for defense in depth!
Fine-Grained Control & Conditional Blocking

Your question highlights conditional blocking – for example, allowing web access only to certain URLs, or blocking certain shell commands (like ls) until user approval. Most sandbox solutions by themselves do not offer interactive approval mechanisms for syscalls or commands. They typically operate by policy: e.g. all network access is either allowed or blocked, all file system writes are allowed or confined to certain directories, etc., without a human in the loop for each action. Achieving interactive control requires an additional monitoring layer. Here are some approaches and considerations:

    Seccomp/System Call Interception: Linux’s seccomp can be used not just to outright block syscalls, but in a notify mode (SECCOMP_RET_USER_NOTIF) where a monitoring process gets alerted on a syscall and can decide to allow or deny it. This is advanced to implement but is one way to catch, say, an open() call to an unauthorized file or an attempt to execute ls (which involves syscalls to read directory entries) and then pause the sandbox until approval. A real-world example of this concept is the PyPy Sandbox. The PyPy Python interpreter has a special sandbox mode where every system call is forwarded to a controller process. That controller can implement any policy – allow, deny, or prompt the user. An initiative called Shannot extends this idea: instead of just isolating the agent, it “captures what they want to do and shows it to the user before executing”, turning syscall interception into a visibility/approval layer
    gist.github.com
    . For instance, if the sandboxed code tries to list a directory or send an HTTP request, the controller could ask the user for confirmation, effectively implementing a runtime firewall with user input. This approach can fulfill the conditional blocking requirement, but it’s custom – none of the mainstream sandbox tools have this built-in as a one-liner feature.

    Tool Broker / Proxy pattern: Another strategy is to architect the agent such that it cannot directly perform sensitive actions, but must request them from a broker service that enforces policy. One Reddit discussion described this as keeping the sandbox “fully isolated (no network, no secrets) and route all side-effects through a tool broker outside the sandbox”
    reddit.com
    . In this pattern, the sandbox might not even have network access or the ability to delete real files at all. Instead, when the AI agent wants to, say, fetch a URL or send an email, it communicates a structured request (like a high-level command) to an external supervisor process. That supervisor can then decide: allow it (and perform the action on behalf of the agent) or deny it. For example, the agent might call a function tool.request("GET", "http://example.com") which inside the sandbox just sends that request description to the broker; the broker (running with actual internet access) checks the URL against an allowlist and either fetches it and returns data, or refuses. This way, the sandbox itself never touches the network or critical systems – only the broker does, under strict rules. This method requires designing your agent to use such tools, but it’s a robust way to enforce policies. In practice, it complements sandboxing: the sandbox contains the execution, and the broker ensures least-privilege for side effects. Some frameworks for AI agents incorporate this idea (for example, an Agent-VM (AVM) concept was mentioned that uses a lightweight VM plus broker commands)
    reddit.com
    .

    Limiting the attack surface: Regardless of interactive approval, you can preemptively block dangerous capabilities. Many container or VM sandbox solutions let you define a whitelist of allowed syscalls or a blacklist of disallowed ones. For instance, you might forbid any execve syscall (preventing the agent from spawning new processes like ls at all), or drop network-related syscalls entirely so it can’t open sockets except through provided safe APIs. If you only want to allow access to one domain, you could hardcode a small HTTP client that ignores other domains (though a crafty agent might still try IP addresses – so truly enforcing that requires a network firewall rule). The point is, by locking down what the sandboxed code can do at the OS level, you reduce the need for asking permission each time. In practice, a combination of techniques might be best: e.g. run the agent in a Firecracker VM and within that VM use iptables or routing rules to only allow traffic to a certain URL, etc.

Reality check: No out-of-the-box sandbox solution in our list will, say, pop up a GUI prompt “Agent wants to run ls, do you allow?”. Implementing that requires custom wiring of syscalls to userland as discussed. If this feature is critical, you might explore projects like the PyPy sandbox or Shannot (for Python code) as a starting point, or build a monitoring layer using seccomp user notifications. Otherwise, your best bet is to use the sandbox’s configuration to predefine allowed/disallowed actions (which is static, not conditional on user input, but covers many cases).
Conclusion

In conclusion, isolation is indeed what we’re after to prevent an AI agent from doing damage
gist.github.com
. There is a spectrum of solutions:

    MicroVM-based sandboxes (Flintlock, E2B, Concave, Firecracker directly) offer the strongest isolation by giving the agent its own kernel and VM. They’re highly secure and open source in many cases, but come with more overhead and sometimes setup complexity. These shine when you absolutely cannot risk the agent affecting the host or need multi-tenant security boundaries. If one-command ease and managed service is desired, E2B’s hosted SDK is very attractive
    northflank.com
    northflank.com
    ; if full FOSS and control is needed, Flintlock or Concave on your own infrastructure is the way to go (with more elbow grease).

    Container-based solutions (Daytona, Modal, etc.) emphasize ease and speed. They can often be used with a single API call or CLI command and integrate nicely into development workflows. With additions like gVisor or Kata, they can approach VM-like security
    northflank.com
    , though not quite as ironclad as Firecracker. These are often sufficient if you trust Linux container isolation plus some hardening – for example, Modal’s use of gVisor means each Python function runs with an extra syscall filter layer
    northflank.com
    , which is a good middle ground. Daytona gives you the choice of more speed or more security, which is great for tuning the sandbox to your needs.

    Open-source versus proprietary: You expressed preference for FOSS. The good news is many options here are open source: Firecracker, Flintlock, Kata Containers, gVisor, E2B (the runtime/SDK), Daytona, Concave, Judge0 – all have open-source components or are fully open. Using them will require some effort to deploy and maintain. If you find a nearly perfect hosted solution that isn’t FOSS (like Modal or Northflank, etc.), you could consider it if it’s inexpensive and saves time. For example, Modal might be “cheap” to start with small workloads and has a generous free tier, but you lock into their platform. Similarly, Northflank (not in your initial list) is a commercial platform that combines Kubernetes with Kata and gVisor under the hood – it’s not FOSS, but it’s an example of a paid service that can run millions of secure microVMs for you if you need scale
    northflank.com
    northflank.com
    . It’s about weighing control vs convenience.

Finally, whichever route you choose, layer your security. Use the sandbox to contain the code, but also follow best practices like not mounting sensitive host files, limiting outbound network access, and running the minimal necessary services in the sandbox. Assume the AI will eventually find a way to do something dumb or dangerous if not fenced in – so give it the smallest playground possible. By combining a strong sandbox (be it VM or locked-down container) with strict policies and maybe an external approval mechanism, you can confidently experiment with AI agent code execution while keeping your system (and data) safe
reddit.com
gist.github.com
.

Sources:

    Liquid Metal’s Flintlock microVM manager overview
    github.com

    E2B.dev documentation on running AI code in secure sandboxes (Firecracker microVMs)
    northflank.com
    northflank.com

    Daytona README (fast sandbox creation, isolated runtime, OCI compatibility)
    github.com
    and architecture notes
    northflank.com

    Modal and others in Northflank’s sandbox comparison (gVisor isolation, Python-only)
    northflank.com
    northflank.com
    northflank.com

    Judge0 official site (open-source code execution engine, sandboxed for 60+ languages)
    judge0.com
    judge0.com

    Sandboxing discussion in mavdol’s gist (Firecracker vs gVisor vs WASM, importance of isolation)
    gist.github.com
    gist.github.com

    Comment on syscall interception as a user-approval layer (Shannot approach)
    gist.github.com

    Security best-practice discussion (tool broker pattern for sandboxed AI agents)
    reddit.com

You said:
This is a strong report. Let's talk about the fine-grain control. Are there libraries/agent frameworks/products/etc that enable this functionalitiy at the agent level? 
ChatGPT said:

Yes. There are a few practical ways to get fine grained control at the agent level today, and they tend to fall into two buckets.

    Agent frameworks that can pause before tool execution and request approval

    Policy and authorization layers that decide whether a proposed action is allowed, denied, or requires approval

If you combine those two, you get what you want: the model proposes an action, your system evaluates it against policy, and only then the tool actually runs.
Agent frameworks that support approvals and pausing

    OpenAI Agents SDK
    • Has built in human in the loop support intended specifically for approving sensitive tool executions.
    OpenAI GitHub

    • Also it supports long running agents and mentions human in the loop workflows with a Temporal integration, which is useful when approvals might take time.
    OpenAI GitHub

    LangChain and LangGraph
    • LangChain has a Human in the loop middleware that can pause execution when a tool call matches a configurable policy.
    LangChain Docs

    • LangGraph supports interrupts that pause a graph at a chosen point and wait until you resume, while persisting state so you can do approval out of band.
    LangChain Docs

    Microsoft AutoGen
    • AutoGen documents human in the loop interaction patterns and also shows interception patterns for tool execution with an intervention handler that can prompt the user for permission.
    Microsoft GitHub+1

    LlamaIndex
    • LlamaIndex explicitly supports tools that put a human in the loop for confirming a tool call or requesting input.
    developers.llamaindex.ai

    • It also supports human in the loop workflows that can pause, wait, and resume.
    developers.llamaindex.ai

What these frameworks usually give you is the mechanism: pause, resume, store state, show a prompt to a reviewer, and continue after a decision.
Policy and authorization layers for real fine grained decisions

Framework pauses are great, but you still need a consistent way to decide “is this allowed” across tools, users, and contexts. Two very common open source choices:

    Open Policy Agent
    • OPA is an open source policy engine. You send it JSON input and it returns an allow or deny style decision, decoupling policy from code.
    openpolicyagent.org+1

    Cedar
    • Cedar is an open source policy language and evaluation engine designed for fine grained authorization.
    cedarpolicy.com+1

A third option that is library style and often easier to embed directly into an app is Oso, which provides policy enforcement libraries and a declarative language.
osohq.com
Products that package agent permissions and approvals

If you want something closer to a product that is specifically framed as permissions for AI agents:

    Permit.io
    • They position this as fine grained permissions for AI powered apps, including human approval for critical actions and tool level controls.
    permit.io

    • They also talk about letting agents check whether an action is allowed before calling a tool, and escalation flows.
    permit.io

    • They also discuss authorizing Model Context Protocol style tool servers at the server boundary, which maps nicely to “agent requests, server authorizes, tool executes”.
    permit.io+1

This can be especially useful if you want approvals, audit logs, and admin UI without building everything yourself, while still using open engines like OPA or Cedar in some setups.
permit.io
The pattern that works best in practice

If you want controls like “allow web only to these domains” and “block certain commands unless approved”, the cleanest agent level design is:

    Put the agent in a sandbox with no network and no direct access to host secrets

    Provide tools that represent side effects as structured requests
    Example: fetch_url, write_file, run_command

    Before executing any tool, run a policy check
    • Inputs: tool name, arguments, user identity, agent identity, conversation, risk score, target host, and so on
    • Output: allow, deny, or needs approval

    If needs approval, pause the agent run and wait for a human decision using your framework mechanism

This makes approvals reliable because the agent cannot bypass them. It also gives you one consistent place to enforce policy.

If you tell me which agent framework you are leaning toward and whether you want policies expressed as code in your repo or managed with a UI, I can suggest a concrete integration shape that fits your stack.


ChatGPT can make mistakes. Check important info.

