# Public research behind this AI fleet

Researched on 2026-10-02 for Mathis's Arch laptop and future machines. The
result is an adaptation of publicly demonstrated practices. Theo's private
letter, complete skills library, machine inventory, and deployment scripts
were not available for inspection. I found a related public Fleet project,
but could not verify an exact recreation of his private repo.

## What Theo has shown

| Evidence | Publicly described practice | Adaptation here |
| --- | --- | --- |
| [AGENTS and skills walkthrough](https://www.youtube.com/watch?v=e1snsuY4lTI), with [unofficial transcript](https://ainotes.us/summary/1039) | A personal letter explains taste, communication, and vocabulary. Project notes address observed failures. Fleet separates universal skills from harness-specific and command-center skills. Skill descriptions control when workflows activate. He describes PR and artifact-sharing workflows. | Preserve your personal rules and letter, keep project notes focused, share only a small set of relevant skills. No new leader role or upload service. |
| [Changed coding workflow](https://rosetta.to/u/t3dotgg/how-i-code-with-ai-changed-a-lot), 2026-05-27, unofficial transcript of Theo's video | T3 Code manages harnesses; the workflow uses conversational requests, short prompts, fresh threads, relevant local context, and verification. | Keep your existing interfaces; use one thread per outcome and ask for evidence. |
| [Voice workflow video](https://www.youtube.com/watch?v=NvVbCqDgfCs), 2026-09-16, with [unofficial transcript](https://moderncreator.app/2026-09-16-theo-t3-gg-how-i-code-without-typing) | Fleet documents computers and connection methods so agents can perform ordinary machine tasks. He demonstrates requesting a separate T3 Code build with its own application identity and data directory. | Maintain machine records and host selection. Isolate experiments when a task requires it; do not replace the working install by default. |
| [Skills evaluation](https://www.youtube.com/watch?v=0oXOOlqVu5M), 2026-08-19, with [unofficial transcript](https://moderncreator.app/2026-08-19-theo-t3-gg-so-i-tried-matt-pocock-s-ai-agent-skills) | He evaluates external skills in practice and manages setup from Fleet, including adding another machine. | Evaluate skills on actual work; no wholesale import. |

The transcripts are third-party renderings, not access to the private files.
Video titles can differ between transcript sites and YouTube. The recurring
pattern is useful context and communication, supported by tools the agent can
actually operate. The folder structure and installer in this kit are our design.

## Public projects checked

| Project | What is verifiable | Decision for this setup |
| --- | --- | --- |
| [extoci/fleet](https://github.com/extoci/fleet), [author's submission](https://devpost.com/software/fleet-t8uwi3) | The author explicitly credits Theo as inspiration. The tool sets up a captain, member discovery, SSH, persistent tmux, and an agent-readable machine skill. Its README lists macOS or Debian/Ubuntu Linux requirements and optional Tailscale routing. | Related implementation, not a copy of Theo's private repo. Your Arch machines already have the underlying transport tools; installing it would introduce a second machine-management convention. Not installed. |
| [mattpocock/skills](https://github.com/mattpocock/skills) | Public reusable engineering skills, referenced in Theo's evaluation. | Source of ideas to evaluate individually, not a reason to import the entire collection. |
| [Cursor PStack skills](https://github.com/cursor/plugins/tree/main/pstack/skills) | Public skill collection linked by the evaluation transcript. The workflow discussed includes interviewing, specifications, tickets, implementation, and review. | Optional for a project that needs that process. The repository path was linked by the source but could not be independently fetched during research; contents and current availability remain unverified. |
| [pingdotgg/t3code](https://github.com/pingdotgg/t3code) | Public application repository. Your laptop already has T3 Code installed. | Keep the existing app; no fork or custom build is needed for this kit. |

No reviewed project supplied Theo's actual private machine records or letter.
An absence in these searches is not proof that no other recreation exists.

## Verified technical foundations

- [OpenAI's skill documentation](https://learn.chatgpt.com/docs/build-skills)
  documents user skills under `~/.agents/skills`, symlink support, concise
  descriptions, and explicit or automatic invocation. [Instruction discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
  documents global Codex guidance under its home and project-level overrides.
- [OpenCode's skills](https://opencode.ai/docs/skills/) include the same shared
  user location; [its rules](https://opencode.ai/docs/rules/) document global
  guidance under `~/.config/opencode/AGENTS.md`.
- [Cursor's skills](https://cursor.com/docs/skills) include `~/.agents/skills`.
  Its documented remote/cloud behavior means local installation alone should
  not be treated as remote availability.
- [tmux's guide](https://github.com/tmux/tmux/wiki/Getting-Started) describes
  detachable persistent terminal sessions. [Tailscale's guide](https://tailscale.com/docs/how-to/quickstart)
  covers private device connectivity. Neither replaces machine context or
  makes a sleeping host execute work.

## Local findings and intentional choices

The laptop's tools, executable shadowing, current desktop session, and active
transport services were inspected directly; see [its record](machines/laptop.md).
The desktop was offline, so its installed state remains unverified. Existing
personal policies were preserved in `../GLOBAL.md` rather than silently
pruned into someone else's defaults.

Keep context and skills in the existing synced config repo, install with
recoverable links, and authenticate separately per device. Leave local models,
automatic merges, fleet daemons, speech tools, external artifact uploads, and
new paid integrations out until a real task calls for them. These are design
choices for Mathis, not claims about Theo's complete setup.
