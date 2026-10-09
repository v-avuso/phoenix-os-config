# Media regression checks

Run from the repository root:

```sh
python3 -B -m unittest discover -s modules/apps/media/tests
```

Put the configured FFmpeg/FFprobe and pinned yt-dlp on PATH, and run with the
configured media Python (including Mutagen/pyacoustid). Missing runtime
dependencies cause the corresponding cases to be explicitly skipped. Fixtures check packet-identical
AV1/Opus copying, H.264/AAC conversion, mixed-stream selective encoding, geometry,
frame rate, metadata, original bypass, software fallback and failed-validation
cleanup. Upstream quality-search arguments and strict size/quality rejection are
covered separately; codec fixtures isolate conversion from the search. Media ingestion and
downloader/progress regressions run in the same suite.
Real GPU encoding, installed commands and representative download sizes/timings
require host acceptance in addition to these disposable fixtures.
`test_pipeline.py` runs real yt-dlp conversion, metadata, artwork, validation and
ingestion/review routing. Its video cases stub optimizer results while exercising
real FFmpeg and publication; representative host runs verify the upstream search.
