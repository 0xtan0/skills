# skills

Agent skills for Claude Code. One folder per skill.

## Skills

| Skill | What it does |
|---|---|
| [infra-flow-deck](skills/infra-flow-deck/) | Builds a slide deck from infrastructure code: an animated request flow, the network path, IAM roles, the release path, a data-protection matrix, and accounts and repos. Every block and arrow is backed by a file and line in the code. |

## Layout

```
skills/
  <skill-name>/
    SKILL.md        required: frontmatter (name, description) + instructions
    assets/         optional: templates and examples the skill copies or reads
    scripts/        optional: tools the skill runs (checks, generators)
scripts/
  install.sh        links every skill into ~/.claude/skills
```

Rules for a skill folder:

- The folder name equals the `name` in its `SKILL.md` frontmatter.
- A skill is self-contained. It refers to its own files by relative path and never to another skill's folder.
- No project-specific data: no account ids, internal names or paths from the repo a skill was first used on.

## Install

Link all skills into Claude Code, so a `git pull` updates them:

```bash
./scripts/install.sh
```

Link one skill:

```bash
./scripts/install.sh infra-flow-deck
```

The script does not replace an existing folder with the same name in `~/.claude/skills`. Move that folder away first.

## Add a skill

1. Create `skills/<skill-name>/SKILL.md` with `name` and `description` in the frontmatter.
2. Put templates in `assets/` and runnable tools in `scripts/`.
3. Add a row to the table above.
4. Run `./scripts/install.sh <skill-name>`.
