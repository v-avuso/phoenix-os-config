# Symbol input

- When changing symbol mappings, validate the full Compose path: keyd accepts
  literal Unicode but emits a private Cancel sequence that applications may not
  load. Prefer standard Compose macros on the configured US layout, keep the
  user's normal locale Compose table available, and check every mapping with
  `tests/symbols.py`; parser success alone does not prove character output.
