# Module boundaries

Modules own their implementation, tests, fixtures, documentation and local
guidance. Prefer an import plus minimal configuration so a module can be shared
or extracted without collecting scattered support files. Explicit dependencies
on other modules and host wiring remain visible.

One or two related files may remain flat. Normally group three or more files,
including tests, under a named feature directory; use concise filenames such as
`default.nix`, `helper.py` and `tests/`. A cohesive module may keep tests at module
level rather than create a directory for every implementation file. Encapsulate
when effort is low; avoid speculative abstractions or promising standalone reuse
where application or host dependencies remain.

`home/` owns user integration; `modules/` owns system policy and services;
`commands/` owns packaged command implementations. Their tests live with those
owners. Shared integration fixtures live at the nearest common owner, such as
`modules/tests/`; the root [test index](../tests/README.md) contains commands and
verification limits. Root documentation covers cross-module operation.

Examples: [Kando](../home/kando/README.md) keeps its patch and selection fixtures
with its Home Manager module; the [mouse adapter](../modules/input/mouse-side-button-debounce/README.md)
keeps device handling and its synthetic tests together. They remain separate
because user menu integration and system input access have different owners.
