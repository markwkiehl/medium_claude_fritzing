# Ways to share a Claude Code skill

This page lists the ways to hand the `fritzing` skill to other Claude Code users. For each way it says what a user types, what the author puts in the repository, and what was tested. All tests ran on Windows 11 with Claude Code 2.1.274, on 2026-11-07.

## Pages that were read

The author read these pages from Anthropic's Claude Code documentation on 2026-11-07. Each was saved as Markdown and read in full or searched for the terms named here.

- [Create a marketplace](https://code.claude.com/docs/en/plugin-marketplaces.md): the `marketplace.json` file, `claude plugin validate`, `claude plugin marketplace add`, `claude plugin install`.
- [Create plugins](https://code.claude.com/docs/en/plugins/create.md): the `plugin.json` file, the `skills/` folder, `--plugin-dir`, `--plugin-url`, and the skills folder in the user's home directory.
- [Publish a plugin](https://code.claude.com/docs/en/plugins/publish.md): sharing without a marketplace, a marketplace file beside `plugin.json` with `"source": "./"`, and Anthropic's directory.
- [Extend Claude with skills](https://code.claude.com/docs/en/skills.md): where skills live (personal, project, plugin) and how skills from a claude.ai account sync.
- [Documentation index](https://code.claude.com/docs/llms.txt): used to find the address of the quickstart page.

## Layout that serves several ways

The repository has one layout, so the ways below all work from the same files.

```text
medium_claude_fritzing/
├── README.md
├── LICENSE
├── .claude-plugin/
│   ├── plugin.json
│   └── marketplace.json
├── docs/
│   └── ways_to_share.md
└── skills/
    └── fritzing/
        ├── SKILL.md
        ├── references/
        ├── scripts/
        └── examples/
```

- The documentation confirms this layout. The manifest `plugin.json` goes in `.claude-plugin/`. The skill goes in `skills/<name>/SKILL.md` at the plugin root, not inside `.claude-plugin/`.
- The documentation also says that a plugin repository can hold its own marketplace file beside `plugin.json`, with one entry whose `source` is `"./"`. The entry name must equal the `name` in `plugin.json`. Here both are `fritzing`.
- The marketplace name is `medium-claude-fritzing`. The documentation says a user cannot add two marketplaces with the same name, so the name is one that other authors are unlikely to use.
- The names `claude-plugins-official` and similar are reserved for Anthropic.

## Way 1: plugin and marketplace from GitHub

- The user types:
  - `claude plugin marketplace add OWNER/medium_claude_fritzing`
  - `claude plugin install fritzing@medium-claude-fritzing`
  - Inside a session, `/plugin marketplace add OWNER/medium_claude_fritzing` does the first step.
- The author puts in the repository: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, and `skills/fritzing/SKILL.md`.
- Tested:
  - `claude plugin validate --strict .` in the repository folder. It printed `Validation passed`. Without `--strict` an earlier run warned that `plugin.json` had no author. The author field was then added.
  - `claude plugin marketplace add <local folder>` and `claude plugin install fritzing@medium-claude-fritzing`, with the environment variable `CLAUDE_CONFIG_DIR` set to an empty folder, so the user's real settings stayed unchanged. Both commands printed `Successfully`. `claude plugin list` showed `fritzing@medium-claude-fritzing` as `enabled`. `claude plugin details fritzing` showed `Skills (1)  fritzing`.
- Not tested: the `OWNER/medium_claude_fritzing` form, because the repository was not on GitHub yet. Updates through `claude plugin update`. The slash command in a session. Running the skill as `/fritzing:fritzing` (the documentation says a plugin's skills get the plugin name as a prefix).
- The documentation says the plugin must have a `version` in `plugin.json` that the author raises on each release, or have no `version`, in which case Claude Code uses the commit id.

## Way 2: plain repository, copy the skill folder

- The user types: download or clone the repository, then copy the folder `skills\fritzing` into `%USERPROFILE%\.claude\skills\` (Windows) or `~/.claude/skills/` (macOS, Linux).
- The author puts in the repository: the folder `skills/fritzing/` with `SKILL.md`. No other file is needed.
- Tested: on Windows, the same files were copied into the personal skills folder, and a new session listed the skill `fritzing`.
- Not tested: macOS and Linux.
- The documentation says a skill in the personal skills folder works in all of the user's projects on that computer, and that Claude Code does not name a folder `synced` there.

## Way 3: load the folder for one session

- The user types: `claude --plugin-dir <path to the repository folder>`. The documentation says `--plugin-dir` also accepts a `.zip` of the plugin.
- Tested: `claude --plugin-dir . plugin list` showed `fritzing@inline` with `Status: loaded`.
- Not tested: a `.zip` passed to `--plugin-dir`.

## Way 4: release zip

- The author attaches a `.zip` of the repository to a release on GitHub. The user downloads it and either unpacks it (Way 2 or Way 3) or passes it to `claude --plugin-url <address of the zip>` for one session.
- Not tested: no release was made, and `--plugin-url` was not run.

## Other ways named in the documentation

- Project skills: a team commits the skill to `.claude/skills/fritzing/` in its own repository. Everyone who works in that repository then has it. Not tested.
- A plugin in a skills folder: a folder with `.claude-plugin/plugin.json` placed in `~/.claude/skills/` loads at every session start. Not tested.
- Anthropic's directory: the author submits the plugin at claude.ai/directory/manage. The plugin then reaches claude.ai, Cowork, and Claude Code. It needs a paid claude.ai plan and a GitHub repository. Not done.
- Skills from a claude.ai account sync into Claude Code when the user signs in with that account. How to add a skill to an account was not read, so it is not covered here.
