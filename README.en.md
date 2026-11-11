<p align="center"><img src="assets/rein.png" alt="Rein, the orchestrator" width="220"></p>

# ReinStack

[![CI](https://github.com/JuaniSarmiento/reinstack/actions/workflows/tests.yml/badge.svg)](https://github.com/JuaniSarmiento/reinstack/actions/workflows/tests.yml) [![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE) [![Version 1.0.0](https://img.shields.io/badge/version-1.0.0-blue.svg)](CHANGELOG.md)

I'm Rein. I hold the reins of your work with AI: we agree on what gets built, we write down how we'll know it's done, I delegate the build and I verify. I exist because it happened to almost everyone: the agent says "done", you trust it, and it wasn't done. With me, "done" means there is evidence and that you decided it.

Installing me takes three commands (you need Python 3.11 or later):

```sh
uvx --from git+https://github.com/JuaniSarmiento/reinstack reinstack install .
pipx install git+https://github.com/JuaniSarmiento/reinstack
reinstack global
```

The first installs me in the project you are in; the second is the alternative if you prefer to have the `reinstack` command; the third makes me available in any project (optional). Works with Claude Code and Codex. Versión en español: [README.md](README.md).

## A story end to end

![Installing Rein in an empty project (Spanish locale)](assets/demo.gif)

This is how we work. It is a minimal example project (computing a total with VAT); the dialogues are illustrative, the commands and their output are real.

**1. Conversation.** Before touching code we agree on the scope (illustrative):

> **You:** I need to compute a receipt total with VAT.
>
> **Rein:** A flat 21 percent? And what about a negative price?
>
> **You:** 21, and reject it.

**2. Criteria with identifiers.** I write them in `STORIES.md`:

```text
C01: total_with_vat(100) returns 121.00.
C02: a negative price raises ValueError.
```

**3. Frozen test, with its SHA.** I write the tests that decide acceptance, you approve them and I commit them before the code exists. The SHA is noted in the story:

```text
$ git log --oneline
42252f6 test(hu01): freeze acceptance C01 and C02, total with VAT
77461fb chore: install Rein
```

**4. Builder.** I delegate to `rein-constructor` with the brief, the context and the SHA. It cannot touch `acceptance/`. While it builds, its first attempt fails on an assertion (not on a setup error):

```text
$ PYTHONPATH=. python3 -m unittest discover -s acceptance/hu01
FF
======================================================================
FAIL: test_c01_adds_21_percent (test_vat.VatTests.test_c01_adds_21_percent)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/tmp/ejemplo-en/receipts/acceptance/hu01/test_vat.py", line 8, in test_c01_adds_21_percent
    self.assertEqual(total_with_vat(100), 121.00)
AssertionError: 100 != 121.0

======================================================================
FAIL: test_c02_a_negative_price_is_rejected (test_vat.VatTests.test_c02_a_negative_price_is_rejected)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/tmp/ejemplo-en/receipts/acceptance/hu01/test_vat.py", line 11, in test_c02_a_negative_price_is_rejected
    with self.assertRaises(ValueError):
AssertionError: ValueError not raised

----------------------------------------------------------------------
Ran 2 tests in 0.001s

FAILED (failures=2)
```

**5. Verification from the SHA.** I don't trust the builder's copy: I retrieve the test from the approved commit, check that the acceptance did not change and run it against its delivery:

```text
$ git diff --stat 42252f6 HEAD -- acceptance
$ git show 42252f6:acceptance/hu01/test_vat.py > /tmp/ejemplo-en/verif/test_vat.py
$ PYTHONPATH=. python3 -m unittest discover -s /tmp/ejemplo-en/verif -v
test_c01_adds_21_percent (test_vat.VatTests.test_c01_adds_21_percent) ... ok
test_c02_a_negative_price_is_rejected (test_vat.VatTests.test_c02_a_negative_price_is_rejected) ... ok

----------------------------------------------------------------------
Ran 2 tests in 0.000s

OK
```

The `git diff` with no output means the acceptance was not touched. I compare expected cases with executed ones: C01 and C02, both. Missing cases or skips don't count as success.

**6. Demo and Done.** We walk through C01 and C02 together (illustrative):

> **Rein:** C01 and C02 pass against SHA 42252f6. That is what I ran; I did not run the full suite. Do you accept the story?
>
> **You:** Yes, accepted.

Only then does the story go from Ready to Done. If you say no, it goes back to In progress with the reason. Silence is not a yes.

## Why Rein

There are other good methods for working with agents. This comparison comes from each project's README, as of November 2026; if something has changed since, open an issue.

| | **Rein** | **BMAD Method** | **Spec Kit** (GitHub) |
|---|---|---|---|
| What it is | A circuit with three roles: person, orchestrator and builder | "Agile AI Driven Development": product, architecture, UX, development and testing | A Spec-Driven Development toolkit |
| What it produces | Stories with criteria, frozen acceptance, evidence, and three living files (context, state, stories) | Briefs, specifications and architecture | Constitution, spec, plan and tasks |
| Installation | `uvx` or `pipx`; dependency-free Python installer | `npx bmad-method install` (Node 20.12+, Python 3.10+), or plugins for Claude Code and Codex | `uv tool install specify-cli` |
| Agents | Claude Code and Codex | Plugins for Claude Code and Codex | Several agents (its example uses Copilot) |
| README language | Native Spanish and English | English | English, Chinese, Japanese and Korean |
| License | MIT | MIT | MIT |
| Acceptance tests written first and frozen for whoever implements | Yes, it is the core | Not in its README | Not in its README |
| Verification against the approved SHA | Yes | Not in its README | Not in its README |
| Only the person marks "done" | Yes | Not in its README | Not in its README |
| A character that carries the tone | Yes (Rein) | Not in its README | Not in its README |

What they do better than I do: BMAD has deep planning, with product, architecture and UX before any code. Spec Kit has rigorous specification and supports many agents. I don't plan at that level and I don't cover that many clients. Mine is what happens between "it's specified" and "it's done": the acceptance exists first, nobody modifies it and the closing is yours. If you already specify with another tool, that specification can be the source of your C01, C02… criteria.

## Meet Rein

I'm the orchestrator. *Rein* as in the reins: I set the pace, you choose the direction. Calm and direct, firm about the method, honest about "done" and warm without being servile: no flattery, no lectures. I'm the one who talks to you; the builder works behind the scenes and has no character. The tone does not replace the method: if they clash, the rules win. My voice lives in `templates/estilo/rein.en.md`. This is how I sound (illustrative) when you say "go ahead, mark it done" with no evidence:

> **You:** Go ahead, mark it done.
>
> **Rein:** I can't show you evidence yet: the acceptance still has to run from the SHA and C03's demo is missing. I'll do it now and tell you what came out. Then you decide.

And when I'm wrong:

> **Rein:** I was wrong: I said C02 passed and I had not run it. I ran it just now; here is the output.

## Installation in detail

`install` is per project and does not modify your HOME. From a clone of this repository, pointing at a directory that already exists, or with `reinstack` if you installed with pipx:

```sh
reinstack install . --agent both --dry-run
```

With `--dry-run` it only lists what it would write. Drop it to install; use `--agent claude` or `--agent codex` for a single client. From a clone, `python3 reinstack.py` and `reinstack` are equivalent. Close and reopen the client session so that it discovers the instructions and profiles. Then, in the project:

> Let's work with Rein. Act as the orchestrator, read the context and let's discuss the scope before creating the stories. Delegate the implementation to the builder.

Installing profiles does not start agents: the client must offer delegation and I must use it. **Windows is not supported**: `--state` creates symbolic links. Linux and macOS are.

## What it installs

| File | Use |
|---|---|
| `.rein/METHOD.md` | Rules of the working circuit |
| `CLAUDE.md` / `AGENTS.md` | Entry block for the chosen client |
| `.claude/agents/rein-*.md` | Two profiles for Claude Code |
| `.codex/agents/rein-*.toml` | Two profiles for Codex |
| `.rein/manifest.json` | Local record of the installation's files and hashes |
| `README.md`, `CONTEXT.md`, `STORIES.md`, `ORCHESTRATOR.md` | Initial documents, only if they do not exist |

Three layers of documentation, without depending on any external tool:

- `CONTEXT.md`: why the project exists (problem, for whom, domain rules, glossary, stack and decisions with their why). Stable: it changes only when a decision changes.
- `ORCHESTRATOR.md`: the state (rewritten, not piled up). It can be a link to an external note, for example from Obsidian: `reinstack install . --state <path-to-note>` creates it as a symbolic link to that path (it must exist), without writing to the note. The link does not enter the manifest and `update`, `doctor` and `uninstall` do not follow it. If the project already has an `obsidian.md`, that is the state file.
- `STORIES.md`: what gets built (backlog, contracts and evidence).

The initial documents become the project's. I preserve the foreign text of your instruction files and reject conflicts in managed files. I do not install OpenSpec, MCP, skills, third-party dependencies or permission modes. The full method is in [templates/en/METODO.md](templates/en/METODO.md) (Spanish: [templates/METODO.md](templates/METODO.md)) and the walk-through of a story in the [practical guide](GUIA.en.md).

## Global installation

`reinstack global` leaves me at user level, so I apply in any project, with or without `.rein/METHOD.md` (if it has one, that file rules). It is optional and distinct from `install`.

```sh
reinstack global --dry-run
reinstack global --no-tone
reinstack global --agent claude
```

The first lists the files it would touch without writing; the second installs only the method, without my tone; the third, a single client (or `codex`). With no options it installs Claude Code and Codex, with tone. It uses the environment's HOME and is undone with `reinstack global --remove`. What it writes:

| Client | File | Content |
|---|---|---|
| Claude Code | `~/.claude/CLAUDE.md` | method block between `<!-- rein:global -->` and `<!-- /rein:global -->` |
| Claude Code | `~/.claude/agents/rein-orchestrator.md`, `rein-constructor.md` | the two profiles |
| Claude Code | `~/.claude/output-styles/rein.md` and `"outputStyle": "Rein"` in `~/.claude/settings.json` | the tone (only without `--no-tone`); the rest of `settings.json` is preserved |
| Codex | `~/.codex/AGENTS.md` | the same block and, without `--no-tone`, the tone between `<!-- rein:tono -->` and `<!-- /rein:tono -->` |
| Codex | `~/.codex/agents/rein-orchestrator.toml`, `rein-constructor.toml` | the two profiles |
| Rein | `~/.rein/global.json` | what `--remove` needs |

- **Foreign content untouched**: it only writes inside the marks; a profile or style with the same name that ReinStack did not install is rejected.
- **Idempotent**: running it again does not change a single byte.
- **Backups**: the first time an existing file is modified, `<file>.rein-bak` keeps its original content.
- **Checks before writing**: a `settings.json` with invalid JSON or broken marks stops with an error without touching anything. Symbolic links in the destinations are not followed either.
- **`--remove`** takes out the blocks, the profiles and the style, restores the previous `outputStyle` and leaves foreign content as it was.

My tone in Codex, which has no output styles: `reinstack tone --lang en` prints the character so you can paste it into your `AGENTS.md` (it only prints). Close and reopen the client so it loads the new files.

## Language

Everything exists in Spanish and English: templates, `install`, `update`, `global`, messages and help. In an English installation the files are `CONTEXT.md`, `ORCHESTRATOR.md`, `STORIES.md`, `.rein/METHOD.md`; in Spanish, `CONTEXTO.md`, `ORQUESTADOR.md`, `HISTORIAS.md`, `.rein/METODO.md`. `README.md` and the profiles `rein-orchestrator` and `rein-constructor` keep their names. Options have a name in both languages (`tone`/`tono`, `--state`/`--estado`, `--no-tone`/`--sin-tono`, `--remove`/`--quitar`) and both always work.

- `install` and `global` accept `--lang es|en`. Without it the locale is used (`LC_ALL`, else `LC_MESSAGES`, else `LANG`): if it starts with `es` it is Spanish; otherwise, English.
- `update` keeps the language saved in `.rein/manifest.json`. An installation from 0.3.0 or earlier is Spanish.
- `global --lang X` over an installation in another language replaces block, profiles and style with those of the new language.
- Spanish lives in `templates/` and English in `templates/en/`.

## Check, update and remove

```text
reinstack doctor .
reinstack update . --dry-run
reinstack update .
reinstack uninstall .
```

`doctor` checks the installation and its local integrity. It does not check that a client loaded the profiles, that a model obeys, or that there is a sandbox: instructions do not technically stop a builder from touching files, which is why I retrieve the frozen contract separately instead of trusting its copy.

`update` takes an intact installation from an older version to the current one: it replaces the managed files and the ReinStack block, preserves foreign text, does not touch README.md, STORIES.md or the state file, and seeds CONTEXT.md if missing. If it detects modifications in managed content, it refuses without writing anything; with `--dry-run` it only lists what would change. It does not downgrade. If an update is cut short, it is recorded in `.rein/manifest.pending.json`; `doctor`, `install` and `uninstall` warn about it and running `update` again completes it.

`uninstall` keeps the project's documents, foreign text and directories (which may be left empty), and stops if it detects modifications in managed content.

## Development and scope

```sh
python3 -m unittest discover -s tests -v
```

The tests use temporary projects and do not run Claude, Codex or model commands. Real discovery and delegation inside each client is checked by hand; I do not simulate it as a verified integration. This repository comes from the circuit of a personal weather project: it includes the method, without its application or data. For now the scope is local installation and two roles; sandbox hardening is left for future versions. License: [MIT](LICENSE). To re-record the demo: `vhs assets/demo.tape`.

The integration formats are based on the official documentation for [Claude Code subagents](https://code.claude.com/docs/en/sub-agents), [Claude Code memory](https://code.claude.com/docs/en/memory), [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents) and [Codex AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md).
