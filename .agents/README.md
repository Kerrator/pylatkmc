# `.agents/` — instructions for AI coding assistants

The single file in this directory, [`AGENT.md`](AGENT.md), is an
operational guide for AI coding assistants (Claude Code, Copilot, Codex,
etc.) working on the pylatkmc codebase. It documents:

- What pylatkmc is, what's in scope vs out of scope
- The "rate-cube preprocessing" caveat that any agent rebuilding the
  rate cube needs to know
- Environment setup, top-level layout, conventions, task recipes
- Known quirks (CMake cache invalidation, mover-vs-vacancy axis offset,
  temperature baking, FCC-only assumption, MPI determinism, etc.)

Human contributors don't need to read this — start with
[`../README.md`](../README.md) and [`../CONTRIBUTING.md`](../CONTRIBUTING.md).

## Why a separate file?

AI assistants benefit from a single comprehensive reference that lays
out the implicit conventions and gotchas of the codebase upfront.
Without it, they tend to re-discover the same constraints on every
session (e.g. "the binary suffix is `pylatkmc_<MODEL>`, not just
`pylatkmc`"; "the build replaces stub .c files via include-path
ordering, don't mix"; "rate cubes are temperature-specific and baked
in"). AGENT.md captures these once, in a place agents can pull into
context as needed.

The format is loosely modeled on the
[Anthropic Skills](https://github.com/anthropics/skills) convention.
If your assistant supports skill / agent files, point it at
`.agents/AGENT.md`. If not, just have it read the file directly.
