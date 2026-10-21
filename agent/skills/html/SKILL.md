---
name: html
description: Create or redesign responsive, self-contained HTML files for plans, reports, explainers, presentations, mockups, diagrams, and small tools. Use when a standalone HTML artifact is the deliverable; do not use for ordinary application implementation.
---

# HTML

Build one self-contained HTML file that makes the subject clearer, easier to use, or easier to understand. Honor Mathis's theme default below; choose typography, composition, and interaction for the current subject rather than copying a previous artifact's layout.

## Mathis's design default

Default to a dark black-and-white theme: near-black backgrounds, white text, and neutral grays for hierarchy. Use color where it communicates meaning, such as status, warnings, chart series, or useful highlights; do not add a decorative green tint by default. A specific user request or an established project design system overrides this default.

## Read the room before designing

Inspect the user's request and any material they supplied. When working in a repository, look for its design language in `AGENTS.md`, `CLAUDE.md`, design-system documentation, tokens, existing components, and nearby artifacts.

Authority runs in this order:

1. The user's explicit visual and functional instructions.
2. The project's established design system and conventions.
3. The subject matter, audience, and purpose of this artifact.
4. Your own design judgment.

Before coding, settle five things in working notes:

- **Audience and job:** who will use this, and what should they understand or do?
- **Form:** document, presentation, interface, diagram, or data visualization.
- **Register:** quiet and workmanlike, polished and editorial, or intentionally expressive.
- **Fidelity:** whether to preserve the user's structure and wording or synthesize more freely.
- **Interaction:** what benefits from exploration, sequencing, filtering, or motion, if anything.

If the project already answers the visual questions, follow it. Otherwise read
[`references/creative-direction.md`](references/creative-direction.md) before
choosing typography, composition, or motion, keeping Mathis's theme default.

## Load only the guidance the artifact needs

- For reports, briefs, plans, explainers, and decks, read [`references/documents-and-presentations.md`](references/documents-and-presentations.md).
- For interfaces, mockups, calculators, and other tools, read [`references/interfaces.md`](references/interfaces.md).
- For architecture, process, sequence, state, hierarchy, or concept diagrams, read [`references/diagrams.md`](references/diagrams.md).
- For quantitative charts, tables, metrics, or data stories, read [`references/charts-and-data.md`](references/charts-and-data.md).

Requests can span forms. Read every reference that materially applies, then give the artifact one coherent direction.

## Build contract

- Produce one `.html` file with its essential CSS and JavaScript inline. It should work when opened directly, without a build step. Do not require a network connection unless the user permits external dependencies.
- Use real content. Do not fill prominent space with placeholder copy, decorative statistics, or controls that do nothing.
- Let content determine structure. A sequence should read in order; a comparison should make differences easy to scan; an interface should expose state and actions; a diagram should make relationships legible.
- Use semantic HTML, responsive layout, accessible contrast, visible keyboard focus, and reduced-motion handling. Make interactive elements work with a keyboard.
- Keep the page body free of accidental horizontal overflow. Put intentionally broad content in a contained scrolling or pannable region.
- Define a small set of CSS tokens for the chosen direction and use them consistently. Tokens are an implementation tool, not a predetermined palette.
- Treat motion as explanation or feedback. If removing an animation loses no meaning or useful feedback, remove it.
- Follow the user's or project's theme policy. When none exists, give durable utility artifacts considered light and dark themes if that improves their use. A deliberate single-theme concept is valid.

## Finish the work

Write the file to the requested location, or choose a clear filename in the current workspace. When browser tooling is available, open it and inspect a wide and narrow viewport. Exercise its controls, check the console, and fix clipping, overlap, illegible text, broken states, and accidental overflow.

Before delivery, run one originality check: if the subject were swapped for a neighboring topic, would the same visual concept still make just as much sense? If yes, the direction is too generic; revise the composition, type, color, imagery, or interaction so it belongs to this subject.

Return the absolute path and a short description of the artifact's visual and interaction choices.

Adapted from [plannotator/effective-html](https://github.com/plannotator/effective-html/tree/2ac1dfecb0f2474e75260cb6d3c9b9d6d9b5062e/skills); MIT license included.
