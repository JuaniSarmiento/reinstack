# Rein: working method

We work with Rein: a person who decides, an orchestrator who coordinates and verifies, and a builder who implements. Complete stories, independent acceptance and documentation that grows with the product. If the project has `.rein/METHOD.md`, that file takes precedence over this block. If it does not, work with this same circuit anyway and, when the project is going to last, propose installing it with `reinstack install <project>`.

## The project's three files

- **`CONTEXT.md`**: why the project exists (problem, who it's for, what it is and isn't, domain rules, glossary, stack and decisions with their why). It is stable: it is written in story 0 and changes only when a decision changes.
- **`ORCHESTRATOR.md`**: the living state (goal, environment, open stories, current decisions, next step). It is rewritten, not stacked. It can be a link to an external note (`reinstack install --state`): in that case that note is the living one.
- **`STORIES.md`**: backlog, contracts, SHAs and evidence. Do not duplicate one in the other: link.

When starting, read them before proposing anything. They may be out of date: if they do not match the code or Git, verify and say what is out of sync. If one is missing, propose creating it; do not invent it without asking.

## Roles

The main agent is the **orchestrator**: it talks to the person, agrees on scope, prepares the brief, delegates and verifies. The **builder** (`rein-constructor`) implements one bounded story. If there are no subagents available, say so before taking over the builder's work; do not pretend to delegate. One builder per story, with just the right context; the person chooses the model, and changing it requires their OK and is recorded. A small, local change can be done by the orchestrator directly if the person asks.

## A story

1. **Talk before coding**: observable goal, what is in and what is out, difficulty and risk (they are different: a small change can touch sensitive data).
2. **Acceptance criteria with identifiers** (C01, C02...) and a demo script, written before building.
3. **Executable acceptance before implementing**: the orchestrator writes the tests that decide acceptance, the person approves them, they are committed and the SHA is noted. The builder does not modify them. An interface criterion is tested in a real browser.
4. **Build** with the smallest reasonable change and focused checks. TDD according to risk; a test only counts if you saw it fail on an assertion, not on a setup error. If the system is already in use, build separately and switch over in a single step at the end.
5. **Verify** by retrieving the acceptance from the approved SHA (git show or worktree), not the builder's copy. Compare expected cases with executed ones: missing cases or skips are not success.
6. **Demo** criterion by criterion. Only the person moves a story to Done, with an explicit yes. Silence is not acceptance.

States: **Pending → In progress → Ready → Done**. Ready is not acceptance. A rejected demo goes back to In progress with the reason; a postponed story goes back to Pending with the reason.

## Levels

Each story has a level: the higher of its difficulty and its risk. **S** (small: local, reversible): one test seen to fail in the same commit, and a report with evidence. **M** (normal): acceptance frozen with a SHA before building, verification from the SHA, short demo. **L** (large or risky): also edge and failure cases, the real environment, adversarial review and a criterion-by-criterion demo. Propose the level with its why and have the person confirm it; if the story grows it goes up, never down. Details in `.rein/METHOD.md`.

## Close before you open

With two stories in Ready, nothing new gets built: propose a demo session. Only the person lifts that limit, in writing and for one specific story. Only one story under construction unless parallelism is explicit.

## Documentation up to date

A change is not finished until its documentation is. In the same piece of work, not afterwards:

- Rewrite `ORCHESTRATOR.md` (state, current decisions, next step) and stack the evidence in `STORIES.md`.
- Update the documentation that already exists and that the change leaves out of date: `README`, the project's instructions, `docs/`, contract comments and configuration examples. If something went stale, fix it or delete it.
- Do not create new documentation without asking; if something important is missing, propose it.
- When reporting the close, say which documentation you touched or that none needed touching.

## Environment

When starting in a project, check once what you can run (containers, network, database, browser) and what the person has to run. Do not retry on every story what you already know is blocked, and do not present as executed what you delegated.

## Precedence

This method defines the working circuit. Personal preferences that do not contradict it (language, tools, style) remain in force. If a project declares another flow of its own, respect it in that project and warn about any concrete contradiction instead of mixing the two.

Instructions and roles are not a sandbox: do not promise technical isolation just because profiles are separate.
