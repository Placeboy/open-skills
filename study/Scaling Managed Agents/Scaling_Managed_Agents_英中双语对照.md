# Scaling Managed Agents: Decoupling the brain from the hands
# 扩展 Managed Agents：将大脑与双手解耦

Published Apr 10, 2026
发布于 2026 年 4 月 10 日

---

*Written by Lance Martin, Gabe Cemaj and Michael Cohen. Special thanks to the Agents API team and Jake Eaton for their contributions.*

*作者：Lance Martin、Gabe Cemaj 和 Michael Cohen。特别感谢 Agents API 团队以及 Jake Eaton 的贡献。*

---

*Get started with Claude Managed Agents by following our [docs](https://platform.claude.com/docs/en/managed-agents/overview).*

*你可以通过我们的[文档](https://platform.claude.com/docs/en/managed-agents/overview)开始使用 Claude Managed Agents。*

---

A running topic on the Engineering Blog is how to [build effective agents](https://www.anthropic.com/engineering/building-effective-agents) and [design harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) for [long-running work](https://www.anthropic.com/engineering/harness-design-long-running-apps). A common thread across this work is that harnesses encode assumptions about what Claude can't do on its own. However, those assumptions need to be frequently questioned because they can [go stale](http://www.incompleteideas.net/IncIdeas/BitterLesson.html) as models improve.

我们工程博客上一个持续讨论的主题是：如何[构建有效的 Agent](https://www.anthropic.com/engineering/building-effective-agents)，以及如何为[长时间运行的任务](https://www.anthropic.com/engineering/harness-design-long-running-apps)[设计 harness](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)。贯穿这些工作的一条主线是：harness 编码了我们对"Claude 自己做不到什么"的一系列假设。然而，随着模型的进化，这些假设可能会[过时](http://www.incompleteideas.net/IncIdeas/BitterLesson.html)，因此需要被频繁地重新审视。

---

As just one example, in prior work [we found](https://www.anthropic.com/engineering/harness-design-long-running-apps) that Claude Sonnet 4.5 would wrap up tasks prematurely as it sensed its context limit approaching—a behavior sometimes called "context anxiety." We addressed this by adding context resets to the harness. But when we used the same harness on Claude Opus 4.5, we found that the behavior was gone. The resets had become dead weight.

举一个例子：在之前的工作中[我们发现](https://www.anthropic.com/engineering/harness-design-long-running-apps)，Claude Sonnet 4.5 在感觉到自己接近上下文限制时，会过早地收尾——这种行为有时被称为"上下文焦虑"。我们通过在 harness 中加入上下文重置来解决这个问题。但当我们把同一个 harness 用在 Claude Opus 4.5 上时，发现这种行为已经消失了。那些重置逻辑变成了毫无价值的负担。

---

We expect harnesses to continue evolving. So we built Managed Agents: a hosted service in the Claude Platform that runs long-horizon agents on your behalf through a small set of interfaces meant to outlast any particular implementation—including the ones we run today.

我们预期 harness 会持续进化。因此我们构建了 Managed Agents：Claude Platform 上的一项托管服务，它通过一小组精心设计的接口替你运行长时任务 Agent——这些接口的目标是超越任何一个特定实现的生命周期，包括我们今天自己正在运行的那些实现。

---

Building Managed Agents meant solving an old problem in computing: how to design a system for "[programs as yet unthought of](http://www.catb.org/esr/writings/taoup/html/ch03s01.html)." Decades ago, operating systems solved this problem by virtualizing hardware into abstractions—*process, file*—general enough for programs that didn't exist yet. The abstractions outlasted the hardware. The `read()` command is agnostic as to whether it's accessing a disk pack from the 1970s or a modern SSD. The abstractions on top stayed stable while the implementations underneath changed freely.

构建 Managed Agents 其实是在解决计算机领域一个由来已久的问题：如何为"[尚未被设想出的程序](http://www.catb.org/esr/writings/taoup/html/ch03s01.html)"设计一个系统？几十年前，操作系统通过将硬件虚拟化为抽象——*进程、文件*——解决了这个问题，这些抽象足够通用，可以服务当时还不存在的程序。抽象比硬件活得更久。`read()` 这个命令并不关心它访问的是上世纪 70 年代的磁盘组还是现代 SSD。上层的抽象保持稳定，下层的实现则可以自由更替。

---

Managed Agents follow the same pattern. We virtualized the components of an agent: a session (the append-only log of everything that happened), a harness (the loop that calls Claude and routes Claude's tool calls to the relevant infrastructure), and a sandbox (an execution environment where Claude can run code and edit files). This allows the implementation of each to be swapped without disturbing the others. We're opinionated about the shape of these interfaces, not about what runs behind them.

Managed Agents 遵循了同样的模式。我们把一个 Agent 的各个组成部分虚拟化：session（只追加的事件日志，记录所发生的一切）、harness（调用 Claude 并把它的工具调用路由到相关基础设施的循环）、以及 sandbox（Claude 可以运行代码和编辑文件的执行环境）。这使得每个部分的实现都可以被替换，而不会波及其它部分。我们对这些接口的形态有明确的主张，但对它们背后运行什么并不设限。

---

![Brain and hands illustration](./images/brain-hands-hero.webp)

---

## Don't adopt a pet
## 别养"宠物"

---

We started by placing all agent components into a single container, which meant the session, agent harness, and sandbox all shared an environment. There were benefits to this approach, including that file edits are direct syscalls, and there were no service boundaries to design.

我们最初把 Agent 的所有组件都塞进了一个容器里，这意味着 session、agent harness 和 sandbox 共享同一个环境。这种做法有它的好处：比如文件编辑是直接的系统调用，也没有需要设计的服务边界。

---

But by coupling everything into one container, we ran into an old infrastructure problem: we'd adopted a [*pet*](https://cloudscaling.com/blog/cloud-computing/the-history-of-pets-vs-cattle/). In the pets-vs-cattle analogy, a pet is a named, hand-tended individual you can't afford to lose, while cattle are interchangeable. In our case, the server became that pet; if a container failed, the session was lost. If a container was unresponsive, we had to nurse it back to health.

但把所有东西都耦合进一个容器后，我们撞上了一个经典的基础设施问题：我们养了一只[*宠物*](https://cloudscaling.com/blog/cloud-computing/the-history-of-pets-vs-cattle/)。在"宠物 vs 牛群"的类比中，宠物是有名字的、被精心照料的个体，你承受不起失去它；而牛群是可以互相替换的。在我们的例子里，服务器就变成了那只宠物：如果一个容器挂了，session 就丢了；如果一个容器无响应，我们就得把它"抢救"回来。

---

Nursing containers meant debugging unresponsive stuck sessions. Our only window in was the WebSocket event stream, but that couldn't tell us *where* failures arose, which meant that a bug in the harness, a packet drop in the event stream, or a container going offline all presented the same. To figure out what went wrong, an engineer had to open a shell inside the container, but because that container often also held user data, that approach essentially meant we lacked the ability to debug.

"抢救"容器意味着去调试那些无响应、卡住的 session。我们唯一的观测窗口是 WebSocket 事件流，但它无法告诉我们故障*出在哪里*——这意味着 harness 里的 bug、事件流中的丢包、或者容器下线，在外部看起来都是同一副样子。要搞清楚到底哪里出了问题，工程师必须到容器里开一个 shell，但由于这个容器往往同时保存着用户数据，这种做法实际上等同于我们缺乏调试能力。

---

A second issue was that the harness assumed that whatever Claude worked on lived in the container with it. When customers asked us to connect Claude to their virtual private cloud, they had to either peer their network with ours, or run our harness in their own environment. An assumption baked into the harness became a problem when we wanted to connect it to different infrastructure.

第二个问题是：harness 假设 Claude 操作的对象一定和它本身在同一个容器里。当客户希望把 Claude 连接到他们自己的 VPC（虚拟私有云）时，他们要么必须把自己的网络和我们对等互联，要么就得在他们自己的环境里跑我们的 harness。这个被烙进 harness 的假设，在我们想把它接到不同基础设施时，就变成了障碍。

---

## Decouple the brain from the hands
## 把大脑与双手解耦

---

The solution we arrived at was to decouple what we thought of as the "brain" (Claude and its harness) from both the "hands" (sandboxes and tools that perform actions) and the "session" (the log of session events). Each became an interface that made few assumptions about the others, and each could fail or be replaced independently.

我们最终的解决方案是：把我们所说的"大脑"（Claude 及其 harness）与"双手"（执行动作的沙箱和工具）以及"session"（会话事件的日志）解耦。每一个都变成一个接口，彼此之间尽量不做假设，各自可以独立失败、独立被替换。

---

**The harness leaves the container.** Decoupling the brain from the hands meant the harness no longer lived inside the container. It called the container the way it called any other tool: `execute(name, input) → string`. The container became cattle. If the container died, the harness caught the failure as a tool-call error and passed it back to Claude. If Claude decided to retry, a new container could be reinitialized with a standard recipe: `provision({resources})`. We no longer had to nurse failed containers back to health.

**harness 离开容器。** 把大脑和双手解耦，意味着 harness 不再住在容器里。它调用容器的方式和调用其它任何工具一样：`execute(name, input) → string`。容器因此变成了"牛群"。如果容器挂了，harness 会把它当作一个工具调用错误捕获下来，再把错误交回给 Claude。如果 Claude 决定重试，就可以按一份标准配方重新初始化一个新容器：`provision({resources})`。我们再也不需要费力"抢救"故障容器了。

---

**Recovering from harness failure.** The harness also became cattle. Because the session log sits outside the harness, nothing in the harness needs to survive a crash. When one fails, a new one can be rebooted with `wake(sessionId)`, use `getSession(id)` to get back the event log, and resume from the last event. During the agent loop, the harness writes to the session with `emitEvent(id, event)` in order to keep a durable record of events.

**从 harness 故障中恢复。** harness 本身也变成了"牛群"。因为 session 日志在 harness 外部，harness 里没有任何东西需要在崩溃后存活下来。当一个 harness 挂掉时，可以通过 `wake(sessionId)` 重新启动一个新的，用 `getSession(id)` 取回事件日志，然后从最后一个事件处继续。在 agent 循环中，harness 通过 `emitEvent(id, event)` 把事件写入 session，以此维持一份持久化的事件记录。

---

![Harness architecture diagram](./images/harness-architecture.webp)

---

**The security boundary.** In the coupled design, any untrusted code that Claude generated was run in the same container as credentials—so a prompt injection only had to convince Claude to read its own environment. Once an attacker has those tokens, they can spawn fresh, unrestricted sessions and delegate work to them. Narrow scoping is an obvious mitigation, but this encodes an assumption about what Claude can't do with a limited token—and Claude is getting increasingly smart. The structural fix was to make sure the tokens are never reachable from the sandbox where Claude's generated code runs.

**安全边界。** 在耦合式设计中，Claude 生成的任何不可信代码，都和凭据运行在同一个容器里——所以一次 prompt injection 只需要说服 Claude 读取它自己的环境变量即可。一旦攻击者拿到这些 token，他们就可以创建全新的、不受限的 session，并把任务委派给它们。狭窄授权（narrow scoping）是一个显而易见的缓解手段，但这种做法本质上是在假设"Claude 拿着一个受限 token 也做不到什么"——而 Claude 正在变得越来越聪明。真正的结构性修复是：确保这些 token 在 Claude 生成代码运行的沙箱里永远不可达。

---

We used two patterns to ensure this. Auth can be bundled with a resource or held in a vault outside the sandbox. For Git, we use each repository's access token to clone the repo during sandbox initialization and wire it into the local git remote. Git `push` and `pull` work from inside the sandbox without the agent ever handling the token itself. For custom tools, we support MCP and store OAuth tokens in a secure vault. Claude calls MCP tools via a dedicated proxy; this proxy takes in a token associated with the session. The proxy can then fetch the corresponding credentials from the vault and make the call to the external service. The harness is never made aware of any credentials.

为此我们使用了两种模式。认证信息要么和资源捆绑，要么存放在沙箱之外的保险库（vault）里。以 Git 为例，我们会在沙箱初始化时使用每个仓库的 access token 克隆代码库，并把它连接到本地的 git remote。之后 `git push` 和 `git pull` 可以在沙箱里正常工作，而 agent 自己从头到尾都不接触这个 token。对于自定义工具，我们支持 MCP，并把 OAuth token 存放在一个安全的 vault 中。Claude 通过一个专用代理调用 MCP 工具；这个代理接收一个与该 session 绑定的 token，然后从 vault 中取出对应的凭据，再向外部服务发起调用。harness 自始至终不会知晓任何凭据。

---

## The session is not Claude's context window
## session 不等于 Claude 的上下文窗口

---

Long-horizon tasks often exceed the length of Claude's context window, and the standard ways to address this all involve irreversible decisions about what to keep. We've explored these techniques in [prior work](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) on context engineering. For example, compaction lets Claude save a summary of its context window and the memory tool lets Claude write context to files, enabling learning across sessions. This can be paired with context trimming, which selectively removes tokens such as old tool results or thinking blocks.

长时任务经常会超出 Claude 的上下文窗口长度，而解决这个问题的标准手段都涉及"不可逆地决定保留什么"。我们在之前的[上下文工程工作](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)中探讨过这些技术。比如 compaction（压缩）让 Claude 把自己的上下文窗口总结成一份摘要保存下来；memory 工具让 Claude 把上下文写入文件，从而实现跨 session 的学习。这些还可以和上下文裁剪（context trimming）配合使用——有选择地移除一些 token，比如旧的工具返回结果或思考块。

---

But irreversible decisions to selectively retain or discard context can lead to failures. It is difficult to know which tokens the future turns will need. If messages are transformed by a compaction step, the harness removes compacted messages from Claude's context window, and these are recoverable only if they are stored. Prior work [has explored](https://arxiv.org/pdf/2512.24601) ways to address this by storing context as an object that lives *outside* the context window. For example, context can be an object in a REPL that the LLM programmatically accesses by writing code to filter or slice it.

但"有选择地保留或丢弃上下文"这种不可逆决定可能会导致失败。我们很难预判未来的某一轮对话到底需要哪些 token。如果消息被一次 compaction 步骤转换过，harness 就会把这些被压缩过的消息从 Claude 的上下文窗口中移除，只有在它们被另行存储的情况下才能恢复。已有[相关工作](https://arxiv.org/pdf/2512.24601)探索了一种思路：把上下文存储为一个生活在上下文窗口*之外*的对象。例如，上下文可以是 REPL 中的一个对象，LLM 通过编写代码来过滤或切片来访问它。

---

![Context object illustration](./images/context-object.webp)

---

In Managed Agents, the session provides this same benefit, serving as a context object that lives outside Claude's context window. But rather than be stored within the sandbox or REPL, context is durably stored in the session log. The interface, `getEvents()`, allows the brain to interrogate context by selecting positional slices of the event stream. The interface can be used flexibly, allowing the brain to pick up from wherever it last stopped reading, rewinding a few events before a specific moment to see the lead up, or rereading context before a specific action.

在 Managed Agents 中，session 提供了同样的好处：它充当一个生活在 Claude 上下文窗口之外的"上下文对象"。不同的是，它并不存储在沙箱或 REPL 中，而是被持久化地记录在 session 日志里。通过接口 `getEvents()`，大脑可以按位置对事件流进行切片，从而去"询问"上下文。这个接口的用法非常灵活：大脑可以从它上次停止阅读的地方继续往下读，也可以回退到某个时刻之前的几条事件看看"前因"，或者在执行某个动作前重新阅读相关上下文。

---

Any fetched events can also be transformed in the harness before being passed to Claude's context window. These transformations can be whatever the harness encodes, including context organization to achieve a high prompt cache hit rate and context engineering. We separated the concerns of recoverable context storage in the session and arbitrary context management in the harness because we can't predict what specific context engineering will be required in future models. The interfaces push that context management into the harness, and only guarantee that the session is durable and available for interrogation.

任何被取回的事件，在进入 Claude 的上下文窗口之前，都可以先在 harness 中被转换。这些转换可以是 harness 自己编码的任何逻辑，包括为了获得高 prompt 缓存命中率而进行的上下文组织，以及各种上下文工程。我们把 session 中"可恢复的上下文存储"与 harness 中"任意的上下文管理"两个关注点分离开，是因为我们无法预测未来的模型会需要什么样的具体上下文工程。接口把上下文管理的职责推给了 harness，只保证 session 是持久化的，并且可供查询。

---

## Many brains, many hands
## 多个大脑，多双手

---

**Many brains.** Decoupling the brain from the hands solved one of our earliest customer complaints. When teams wanted Claude to work against resources in their own VPC, the only path was to peer their network with ours, because the container holding the harness assumed every resource sat next to it. Once the harness was no longer in the container, that assumption went away. The same change had a performance payoff. When we initially put the brain in a container, it meant that many brains required as many containers. For each brain, no inference could happen until that container was provisioned; every session paid the full container setup cost up front. Every session, even ones that would never touch the sandbox, had to clone the repo, boot the process, fetch pending events from our servers.

**多个大脑。** 把大脑和双手解耦，同时也解决了我们最早遇到的客户抱怨之一。当团队希望 Claude 访问他们自己 VPC 中的资源时，唯一的路径就是把他们的网络和我们的对等互联，因为装着 harness 的容器假设所有资源都紧挨着自己。一旦 harness 不再住在容器里，这个假设就不复存在了。同样的改动还带来了性能收益。当我们一开始把大脑放进容器时，这意味着多少个大脑就需要多少个容器。对每一个大脑来说，在容器被 provision 之前，任何推理都无法开始；每个 session 都要预先付清整个容器的启动成本。每个 session——哪怕是根本不需要沙箱的那些——都要克隆仓库、启动进程、从我们的服务器拉取待处理的事件。

---

That dead time is expressed in time-to-first-token (TTFT), which measures how long a session waits between accepting work and producing its first response token. TTFT is the latency the user most acutely *feels*.

这段"空转时间"体现在 TTFT（首 token 时延，time-to-first-token）上，它衡量一个 session 从接收任务到产出第一个响应 token 之间要等多久。TTFT 是用户*感受最直接*的延迟。

---

Decoupling the brain from the hands means that containers are provisioned by the brain via a tool call `(execute(name, input) → string)` only if they are needed. So a session that didn't need a container right away didn't wait for one. Inference could start as soon as the orchestration layer pulled pending events from the session log. Using this architecture, our p50 TTFT dropped roughly 60% and p95 dropped over 90%. Scaling to many brains just meant starting many stateless harnesses, and connecting them to hands only if needed.

把大脑和双手解耦后，意味着容器只有在被需要时，才会由大脑通过一次工具调用 `(execute(name, input) → string)` 去 provision。因此不需要立刻用到容器的 session，根本就不用等容器启动。只要编排层从 session 日志中拉到待处理的事件，推理就可以立刻开始。使用这套架构后，我们的 p50 TTFT 下降了大约 60%，p95 下降了超过 90%。扩展到多个大脑，就只是启动多个无状态的 harness，并且仅在必要时把它们连到双手上而已。

---

**Many hands.** We also wanted the ability to connect each brain to many hands. In practice, this means Claude must reason about many execution environments and decide where to send work—a harder cognitive task than operating in a single shell. We started with the brain in a single container because earlier models weren't capable of this. As intelligence scaled, the single container became the limitation instead: when that container failed, we lost state for every hand that the brain was reaching into.

**多双手。** 我们还希望每一个大脑都能连接多双手。在实践中，这意味着 Claude 必须在多个执行环境之间进行推理并决定把任务派发到哪里——这是一项比只在单个 shell 里操作更难的认知任务。我们最初把大脑放在单个容器里，是因为当时的模型还做不到这一点。但随着模型智能的提升，单个容器反而成了限制：一旦那个容器挂掉，大脑伸进的每一只"手"的状态都会一起丢失。

---

Decoupling the brain from the hands makes each hand a tool, `execute(name, input) → string`: a name and input go in, and a string is returned. That interface supports any custom tool, any MCP server, and our own tools. The harness doesn't know whether the sandbox is a container, a phone, or a Pokémon emulator. And because no hand is coupled to any brain, brains can pass hands to one another.

把大脑和双手解耦后，每一只手都变成了一个工具 `execute(name, input) → string`：传入一个名字和输入，返回一个字符串。这个接口可以承载任何自定义工具、任何 MCP server，以及我们自家的工具。harness 并不知道沙箱到底是一个容器、一台手机，还是一个宝可梦模拟器。而且因为没有任何一只手与某个特定大脑耦合，大脑之间也可以互相传递手。

---

## Conclusion
## 结论

---

The challenge we faced is an old one: how to design a system for "programs as yet unthought of." Operating systems have lasted decades by virtualizing the hardware into abstractions general enough for programs that didn't exist yet. With Managed Agents, we aimed to design a system that accommodates future harnesses, sandboxes, or other components around Claude.

我们所面对的挑战是一个古老的问题：如何为"尚未被设想出的程序"设计一个系统。操作系统之所以能够延续数十年，正是因为它把硬件虚拟化为足够通用的抽象，能够服务当时还不存在的程序。我们希望通过 Managed Agents 设计一个能够容纳未来的 harness、沙箱，以及围绕 Claude 的其它组件的系统。

---

Managed Agents is a meta-harness in the same spirit, unopinionated about the *specific* harness that Claude will need in the future. Rather, it is a system with general interfaces that allow many different harnesses. For example, Claude Code is an excellent harness that we use widely across tasks. We've also shown that task-specific agent harnesses excel in narrow domains. Managed Agents can accommodate any of these, matching Claude's intelligence over time.

Managed Agents 正是本着同样的精神而构建的"元 harness"：它对 Claude 未来所需的*具体* harness 不持立场。相反，它是一个提供通用接口、允许多种不同 harness 存在的系统。例如，Claude Code 就是一个出色的 harness，被我们广泛用于各种任务；我们也展示过，针对特定任务的 agent harness 在各自的狭窄领域里表现极佳。Managed Agents 能够容纳任何一种 harness，并随着时间推移与 Claude 的智能同步进化。

---

Meta-harness design means being opinionated about the interfaces around Claude: we expect that Claude will need the ability to manipulate state (the session) and perform computation (the sandbox). We also expect that Claude will require the ability to scale to many brains and many hands. We designed the interfaces so that these can be run reliably and securely over long time horizons. But we make no assumptions about the number or location of brains or hands that Claude will need.

元 harness 设计意味着对 Claude 周围的接口持有明确的立场：我们预期 Claude 需要操作状态的能力（即 session）以及执行计算的能力（即 sandbox）。我们也预期 Claude 需要能够扩展到多个大脑和多双手。我们设计这些接口的目标，是让它们能够在很长的时间跨度内可靠且安全地运行。但对于 Claude 到底需要多少个大脑或多双手、它们位于何处，我们不做任何假设。

---

## Acknowledgements
## 致谢

---

Written by Lance Martin, Gabe Cemaj and Michael Cohen. Special thanks to the Agents API team and Jake Eaton for their contributions.

作者：Lance Martin、Gabe Cemaj 和 Michael Cohen。特别感谢 Agents API 团队以及 Jake Eaton 的贡献。
