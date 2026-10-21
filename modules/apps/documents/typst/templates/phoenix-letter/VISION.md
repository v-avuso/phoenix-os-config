# Phoenix Letter: exploratory directions

These are ideas for investigation, not an approved roadmap or implementation
specification. Keep the accepted template usable independently of any application.

## Possible standalone application

A minimalist, free/open-source desktop tool could let ordinary users paste
Markdown and save a professional letter with fully local processing. This could
provide public benefit and a freelance portfolio project.

- One main multiline Markdown field, with a hint such as “Paste your letter here,
  for example from ChatGPT.” A small gear opens settings; clearly separate
  “Generate PDF” from “Save PDF”. Keep cognitive load low and avoid an installation
  wizard where reasonably possible.
- Sender/frontmatter defaults live in settings rather than permanent main-window
  fields, normally configured once and persisted across launches. Font/formatting
  choices could follow after user research.
- Explore portable `phoenix-letter.exe` beside human-readable
  `phoenix-letter-configuration.toml`; their shared prefix groups them alphabetically.
  Use the executable directory only when writable, with an application-data fallback.
  Never modify the executable to store preferences.
- Investigate a native Rust GUI embedding Typst libraries, the template, suitable
  fonts and license notices. Avoid requiring an installed Typst CLI or Omd2Typst.
  Explore Windows/Linux/macOS builds and self-contained distribution.
- Evaluate LTO, stripping and dead-code elimination for distribution size without
  sacrificing reliable output, semantic tagging, font embedding or hyperlinks.

Separate template/integration repositories, possibly nested via a future submodule,
and companion authoring-agent guidance are other possible consumers. No submodules,
GUI framework, compiler migration or public-license choice is committed by this
structure. Each direction needs its own usability, packaging, licensing and
maintenance assessment before implementation.
