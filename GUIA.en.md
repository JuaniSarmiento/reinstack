# A story with Rein

## Initial conversation

The person tells what they need. The orchestrator questions ambiguities, checks real constraints and proposes a first useful scope. The stack and the main stories are agreed without designing every future detail. That conversation is story 0: the orchestrator leaves the why of the project in CONTEXT.md (problem, for whom, what it is and what it is not, domain rules, glossary, stack and decisions with their why). In an existing project it writes it by reading the code and asking what it cannot deduce. The README keeps how to run it and the current decisions.

## A sufficient brief

The story lives in STORIES.md, for example:

```md
### HU01 — Save my first place
Status: Pending
Difficulty: Medium
Risk: Low; local personal data

Goal: mark a place on the map and get it back when coming back in.
Includes: runnable map, selection, name and persistence.
Excludes: sharing, notifications or multiple users.

C01: when marking a point and saving it with a name, that place appears.
C02: on reload, the place and its name are still available.
C03: an empty name reports the problem and does not create a place.

Acceptance: pending, to be prepared and approved.
Approved SHA: pending; do not delegate yet.
Expected cases: C01, C02, C03.
Command: pending, depends on the stack.
Demo: mark, name, save, reload and try an empty name.
```

An initial story also includes how to start the project and how to run its verification. The layers are built together around the behavior; they are not three separate stories.

## Preparing the contract

The orchestrator writes tests from C01–C03 without looking at an implementation that does not exist yet. They are reviewed with the person. After they are approved, a commit of acceptance/hu01/ is made and the full SHA, command and expected cases are recorded.

Approving the scope does not replace approving a contract that does not exist yet. The orchestrator presents what concretely needs approval and carries on with all the independent work it can do.

## Delegate and build

The builder receives the ready story, paths to the current context, the contract and the limits. It reads the necessary code, implements, writes supporting tests and verifies the change in a focused way. If the problem requires changing the scope or the contract, it hands it back to the orchestrator to decide with the person.

The builder delivers evidence, not an unsupported "done". It does not run the full suite and does not decide that its own story was accepted.

## Verify and demonstrate

The orchestrator retrieves the acceptance from the approved SHA in another environment and runs it against the delivery. It checks that exactly the agreed cases and the necessary regressions were executed. If a full suite is needed, the person runs it and its evidence is recorded.

The Ready state means there is a delivery to review; it must say what was verified and what is missing. The demo walks through C01, C02 and C03. With a correct objective result and an explicit yes from the person, it becomes Done. If they say no, it goes back to In progress with the reason.

## Demo session

When two stories are Ready, the orchestrator stops new construction and proposes reviewing them together. For each one it shows the script, what was verified and what is missing, and the person decides on the spot: Done, back to In progress with a reason, or to Pending with a reason if they prefer to postpone it. That way deliveries do not pile up waiting for a closing that never comes.

## Global installation

`reinstack global` leaves Rein at user level, so it applies in any project, with or without `.rein/METHOD.md` (if it has one, that file rules). It is optional and distinct from `install`, which is per project.

```sh
python3 reinstack.py global --dry-run      # lists the files it would touch, writes nothing
python3 reinstack.py global                # Claude Code and Codex, with tone (language: --lang es|en)
python3 reinstack.py global --no-tone      # only the method
python3 reinstack.py global --agent claude # or codex: only that client
python3 reinstack.py global --remove       # undoes what it installed
```

It uses the environment's HOME. What it writes:

| Client | File | Content |
|---|---|---|
| Claude Code | `~/.claude/CLAUDE.md` | method block between `<!-- rein:global -->` and `<!-- /rein:global -->` |
| Claude Code | `~/.claude/agents/rein-orchestrator.md`, `rein-constructor.md` | the two profiles |
| Claude Code | `~/.claude/output-styles/rein.md` and `"outputStyle": "Rein"` in `~/.claude/settings.json` | the tone (only without `--no-tone`); the rest of `settings.json` is preserved |
| Codex | `~/.codex/AGENTS.md` | the same method block and, without `--no-tone`, the tone between `<!-- rein:tono -->` and `<!-- /rein:tono -->` |
| Codex | `~/.codex/agents/rein-orchestrator.toml`, `rein-constructor.toml` | the two profiles |
| Rein | `~/.rein/global.json` | what `--remove` needs (previous outputStyle, hashes of what was installed) |

- **Foreign content untouched**: it only writes inside the marks. If there is no block, it is added at the top of the file; if the file does not exist, it is created. A profile or style with the same name that ReinStack did not install is rejected.
- **Idempotent**: running it again does not change a single byte; an old block is replaced only inside its marks.
- **Backups**: the first time an existing file (`CLAUDE.md`, `AGENTS.md`, `settings.json`) is modified, `<file>.rein-bak` is left with its original content. An existing backup is never overwritten and none is made for what did not exist.
- **Everything is checked before writing**: a `settings.json` with invalid JSON or broken marks (opened and never closed, or duplicated) stops with an error without touching anything. Symbolic links in the destinations are not followed either.
- **`--remove`** takes out the blocks (and the blank lines it added), the profiles and the style, restores the `outputStyle` that was there (or deletes the key if there was none) and leaves foreign content as it was. It keeps the `.rein-bak` files.

Close and reopen the client so that it loads the new files.

## Language

`install` and `global` accept `--lang es|en`; without it the locale is used (`es...` gives Spanish, anything else gives English). `update` keeps the installed language and a 0.3.0 installation counts as Spanish. In an English installation the files are called `CONTEXT.md`, `ORCHESTRATOR.md`, `STORIES.md` and `.rein/METHOD.md`, and the options have English aliases (`tone`, `--state`, `--no-tone`, `--remove`); both names always work. See the README, Language section.

## Picking it up another day

Three files answer everything. CONTEXT.md says why the project exists and changes little. ORCHESTRATOR.md, the state, says what is being worked on, what is blocked and what the next step is, in its five sections; it can be a link to an external note (for example from Obsidian) created with `install --state <path>`, and it is not a copy of the chat. STORIES.md says what is accepted and with what evidence. Decisions that no longer apply are corrected or removed. An existing `obsidian.md` is still valid as the state file, for compatibility.

ReinStack installs this circuit as instructions. Retrieving the contract and checking cases takes real work from the orchestrator: the installer does not implement a universal acceptance runner or a permissions system.
