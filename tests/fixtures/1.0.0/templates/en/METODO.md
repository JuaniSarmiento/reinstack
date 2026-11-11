# Rein Method

We work in vertical user stories, with brief, progressive documentation. The person decides the expected outcome; the orchestrator coordinates and verifies; the builder implements. The instructions guide the agent: they are not a sandbox and do not technically block its tools.

## Project start

Talk before coding: purpose, users, scope of the first version, exclusions, data sources and stack. That conversation is story 0: the orchestrator writes CONTEXT.md (problem, who it's for, what it is and isn't, domain rules, glossary, stack and decisions with their why) by interviewing the person; in an existing project it reads the code and asks whatever it cannot deduce. Record only agreed decisions in README.md and CONTEXT.md, and the main stories in STORIES.md. Do not generate a long specification up front. The first story delivers a walking skeleton: a runnable application, a minimal slice of the layers needed and a way to check it.

## Environment

When the project starts, and whenever it changes, the orchestrator checks with a real attempt what it can run (containers, network, database, browser) and records it in the state file next to what the person has to run. With that table it prepares up front the commands the person will execute; it does not retry on every story what it already knows is blocked, and it does not present as executed what it delegated.

## Precedence

Inside a project with Rein, this method defines the working circuit. If the client's global instructions propose another flow (other roles, other stages, other artifacts), this method prevails; personal preferences that do not contradict it, such as language or tools, remain in force. When there is a concrete contradiction, tell the person instead of mixing the two circuits.

## Roles and context

The main agent acts as the orchestrator. It talks to the person, maintains the backlog, prepares the brief, delegates the implementation and checks the delivery. The builder is a separate subagent that develops the story. If the environment does not allow delegation, report the limitation before replacing that circuit; do not pretend there was a subagent.

The builder receives the brief and reads README.md, CONTEXT.md, the story, the state file (ORCHESTRATOR.md) and the applicable instructions. It does not receive a raw task and does not need to rebuild the whole conversation. It must report contradictions, pending decisions or blockers to the orchestrator.

One builder per story, with a brief limited to the context it needs. Which model or tool builds is decided by the person; if it has to be replaced (for example, for lack of quota), the person's OK is requested and the replacement is recorded in the story.

## Story brief

Inside STORIES.md, record: identifier, status, observable goal, scope and exclusions, acceptance criteria with identifiers, difficulty, risks, dependencies and demo script. Add technical decisions only when they help execution. Difficulty and risk are different: a small change can affect sensitive data.

- Low: bounded change, focused checks.
- Medium: integration or relevant logic, edge examples and focused regression tests; TDD where it helps.
- High or high risk: investigate uncertainties before building, edge and failure tests, TDD on critical logic and adversarial review with an independent approach.

An adversarial review can be a session independent of the orchestrator; it does not require a third installed profile. Switching models may help, but it guarantees neither independence nor correctness. Set a budget and a stopping condition for investigations; an investigation can be closed with a negative result, without presenting a feature that does not exist.

## Acceptance before implementation

The builder does not write or modify the tests that decide the acceptance of its own delivery. The orchestrator turns the agreed criteria into executable tests in acceptance/<story>/ before delegating. The person and the orchestrator approve the contract, the expected identifiers and the demo script. Freeze it in Git and note in the story the approved SHA and the run command. If Git, the approval or an executable way to verify a criterion is missing, point it out and resolve it before declaring the acceptance frozen.

The builder may write supporting unit and integration tests. It does not change the acceptance contract to get a green result. If it finds an incorrect criterion, it asks for a decision; an approved change requires another commit and another SHA, with the reason recorded.

An interface criterion is verified in a real browser with the rendered screen (clicks, accessible names, console errors): API tests alone are not enough. If only the live system exists, the test walks through it read-only and intercepts writes.

When verifying, the orchestrator retrieves acceptance/<story>/ from the approved commit in a separate environment, through git show or a worktree; it does not trust the builder's copy. It runs that contract against the delivered code and compares expected cases with cases actually executed: missing cases, skips or partial selection do not count as success. Checking that the local folder has the right SHA is not enough. This simple isolation does not stop malicious code from tampering with the process: it is not a security barrier.

## Build and validation

Work one story at a time unless parallelism is explicit, with defined limits on files and dependencies. Each story crosses database, backend and frontend when the behavior needs it; do not split automatically by layer.

The builder runs only checks focused on the change and reports commands, results and limits. No agent runs the full suite: the person runs it when appropriate and shares the evidence. The orchestrator identifies which regressions and additional checks are needed; it does not claim to have run them without evidence. The story's acceptance tests are run in a focused way by the orchestrator. Use isolated data and environments; do not touch personal databases or production to validate.

If the system is already in use (a running service, files served live), the builder builds and tests in a separate copy or branch and switches over in a single step at the end, with a backup of any data it migrates. It never leaves the person facing a half-done deployment.

## States and closing

STORIES.md has four states: Pending, In progress, Ready and Done.

- Pending: identified, not implemented yet.
- In progress: the contract is being agreed, or the story is being built and fixed.
- Ready: delivery prepared for review; record the available evidence and the pending verifications. It does not equal acceptance.
- Done: the orchestrator verified the frozen contract and the required regressions, and the person walked through the demo and explicitly accepted.

If the person rejects the demo, go back to In progress and note the reason. Silence is not acceptance. Do not mark Done just because the builder says it finished or the tests pass.

## Close before you open

A delivery without a demo is half-finished work. With two stories in Ready, no new construction is delegated: the orchestrator proposes a demo session. Only the person can lift that limit, in writing and for one specific story.

In the demo session, the orchestrator presents each story in Ready with its script criterion by criterion, the verified evidence and what is missing, and the person decides: Done, or back to In progress with the reason. If they prefer to postpone it, it goes back to Pending with the reason; there is no fifth state. At the end, STORIES.md and the state file reflect each decision.

## Living documentation

Each project has three layers of documentation, besides README.md (how to run it and current decisions):

- CONTEXT.md: why the project exists. It is stable: it is written in story 0 and changed only when a decision changes, noting the why. It is read at the start, together with the state.
- ORCHESTRATOR.md: the state, the minimum context to resume, blockers and next step. It can be a regular file or a link to an external note (for example, an Obsidian note), created with `reinstack install --state <path>`; then the external note is the state and it is updated when closing each working day. For compatibility, an existing `obsidian.md` plays that role and ORCHESTRATOR.md is then not created.
- STORIES.md: what gets built: backlog, contracts and evidence.

Update them when closing and when an important decision changes. Remove obsolete context and link evidence, without copying huge logs. Record concrete constraints with their reason; do not accumulate vague mandates.

The state does not exceed about forty lines and keeps five fixed sections: Goal, Environment, Open stories (one line per story that is not Done: status, what is missing, blocker if any, next step), Current decisions and Next step. It is rewritten, not stacked: when updating it, whatever stopped being true is deleted; only a dated history, if the external note has one, is stacked. What was accepted is not repeated here: Done stories, their evidence, SHAs and commands live in STORIES.md. If the existing state does not have this format, the orchestrator rewrites it this way the next time it updates it, keeping only what is current. If a constraint repeats across several paragraphs, write it once as a current decision.

Do not add three new documents for each change. Acceptance files, evidence data and specific technical documentation are created only when needed. Do not record secrets. The installer does not download skills or configure permissions, services or credentials. Decoy-based protections, pinned external dependencies and extended auditing are left for an explicit evolution of the circuit.
