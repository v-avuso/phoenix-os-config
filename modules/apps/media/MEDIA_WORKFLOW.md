# Media workflow

Phoenix packages yt-dlp from the existing `nixpkgs-unstable` input for exact-source
downloads, and stable FFmpeg for lossless remuxing. A small Python worker uses
pyacoustid + Chromaprint/fpcalc for fingerprints, MusicBrainz's web service for
canonical metadata, and Mutagen for tag writes and file organization. It has no
library database. Picard remains installed for manual
MusicBrainz release review and corrections in `_review`; it can compare release
track lists and edit tags in ways ordinary file properties and Thunar's basic
metadata display cannot.

`/home/v/sync/music/_unsorted/` is the ingestion queue. `_review/` holds files
that lack a confident match or hit an operational error. The worker excludes
that subtree and starts on yt-dlp's `after_move` hook, after the final file has
been remuxed and tagged. There is no directory watcher or stability delay.
Successful matches go under `/home/v/sync/music/<artist>/<album>/`, or directly
under the artist directory when no release is safely selected.

## Music downloads

These packaged commands work from any shell and pass options as individual
arguments without shell aliases or `eval`:

```sh
download music <URL> [yt-dlp options...]
download m <URL> [yt-dlp options...]
dl music <URL> [yt-dlp options...]
dl m <URL> [yt-dlp options...]
dlm <URL> [yt-dlp options...]
dlm --verbose <URL> [yt-dlp options...]
```

The URL goes directly to yt-dlp; there is no search or recording substitution.
`codec-policy.json` centrally defines the source selection and output preferences.
Audio prefers the best existing Opus stream, then best audio, then a combined
source if necessary. The shared Phoenix yt-dlp postprocessor extracts audio,
copies existing Opus packets, and converts other codecs with libopus VBR.
`phoenix.media.audioBitrateKbps` caps the bitrate (default `160` kbit/s): a
reliable positive FFprobe **audio stream** bitrate is used when lower, otherwise
the configured default applies. If merging removed the stream bitrate, FFprobe
measures the average from audio packet bytes and their timestamp span; missing/invalid
packet durations fall back to the configured default. Aggregate file/video bitrate
and extractor estimates are never used. This policy applies to both music and video.
There are no codec-specific equivalence tables.
Encoding other lossy codecs is an explicit user preference, not a promise of
smaller files or improved source quality. Attached thumbnail artwork is not a
moving video stream.

Fallback metadata uses a reliable extractor artist when present, otherwise
channel/account, uploader, or creator. A title prefix is removed only when it
literally duplicates that creator (case-insensitive, spaced `Creator - Title`).
Unknown/ambiguous titles are not split into guessed music artists. Upload year
is included only when supplied by the extractor; no current date is synthesized.
Title, artist, source URL, and thumbnail are embedded before ingestion, with no
info JSON sidecar or embedded info JSON. Untrusted album, disc, track, and genre
fields are cleared. Authoritative MusicBrainz enrichment overrides fallback
music tags. Filenames are human-readable and omit source IDs. Thunar's unexplained
Year 2006 display is not evidence of a corrupt embedded date tag. Inspection of
existing X WebM/Matroska downloads found `DATE=2026` and correct artists; older
videos without year tags also exist. Phoenix maps extractor `upload_date` to
`meta_date` as a year and uses yt-dlp's FFmpeg metadata postprocessor for both
audio and video. The source year is left unset when unavailable. The exact packaged Thunar media-tags plugin 0.6.0 reads TagLib's year and
substitutes `2006` when that value is zero (`audio-tags-page.c`,
`audio_tags_page_taglib_file_changed`). A read-only probe with its linked
TagLib 2.2.1 returned zero for the inspected WebM/Matroska files, including
those with FFprobe `DATE=2026`. Thus the reported 2006 is a viewer fallback,
not the embedded upload year. Viewer/TagLib compatibility is deferred; no
speculative tag workaround or rewriting of existing files is applied.

Disposable regression checks and runtime prerequisites are in
[tests/README.md](tests/README.md).

Audio and video share progress, retry handling, private staging, diagnostic logs,
and error handling. Completion prints the actual final filename and directory,
including `_review` destinations. Completion speed is hidden, and merges under
one second are omitted. Recovered extractor warnings are retained in diagnostics
but suppressed on successful normal-mode runs; actionable warnings remain visible. Metadata service errors are warnings when usable audio was
preserved in `_review`; an actual download or unusable-audio failure remains
nonzero. Add `-v` or `--verbose` to `download music` or `dlm` to stream yt-dlp
and worker diagnostics. Structured worker events are also retained, without
secret values, in `~/.local/state/phoenix-media/ingest.jsonl` with user-only
file permissions.

## Identification and routing policy

The worker invokes pyacoustid fingerprinting for each completed supported audio
file. `fpcalc` examines at most 120 seconds and is killed after 10 seconds.
AcoustID and MusicBrainz requests each have a 5-second network timeout. The
Secret Service lookup can wait up to 60 seconds for a first-use keyring unlock
prompt; rate-limit lock wait is capped at 2 seconds.
The worker emits one JSON record per stage/result; the download wrapper saves
these to the private local event log, while direct worker invocations emit them
to stdout. It never logs the AcoustID client key. Temporary lock
files live under `$XDG_RUNTIME_DIR` or `/tmp` and rate-limit AcoustID to at most
three requests per second and MusicBrainz to about one per second.

Automatic acceptance is deliberately conservative. Repeated AcoustID rows for
one MusicBrainz recording count as one identity. The best fingerprint score
must be at least `0.90`; a sole candidate above that floor or a lead of at least
`0.12` is accepted. If multiple strong candidates are closer, fallback title
and artist similarity can break the tie only when the combined score is at
least `0.82`, the lead is at least `0.12`, and both artist and title scores are
at least `0.70`. Text cannot rescue a fingerprint below `0.90`. Version words
such as live, remix, acoustic, and remaster remain part of tie-breaking. These
are local conservative cutoffs, not calibrated probabilities.

The chosen MusicBrainz recording supplies canonical artist/title and its
recording identifier. Release tags and album directories are added only for a
sole MusicBrainz release or when the source album hint matches a release title
at least `0.92` with a `0.12` margin; a matching source year can add only a
small tie-breaking preference. Without a selected release, there are no album,
album-artist, track-number, or disc-number tags. Genres are taken only from MusicBrainz genre entities: a genre needs
at least two votes and at least half as many votes as the top genre, with a
maximum of five. The worker does not split mixes or create genre directories.

Weak, ambiguous, no-match, missing-key, fingerprint, network, metadata, tag-write,
and filesystem outcomes preserve the original fallback-tagged file and route it
to `_unsorted/_review/<original-relative-path>`. Duplicate canonical names get
`(1)`, `(2)`, and later suffixes without overwriting an existing track. If an
operational error prevents the move, the file remains in the inbox and the
reason is logged distinctly. Once yt-dlp has produced a usable audio file,
successful review routing after an identification/metadata error returns success
to yt-dlp; unreadable audio or a failed review move returns nonzero.

AcoustID needs an **application/client key** for lookup; no submission key is
used. GNOME Keyring provides Phoenix's runtime Secret Service. Phoenix asks for
only its AcoustID credential, stored under an internal Phoenix-specific
identity; the key never enters the repository or Nix store. KeePassXC remains
independent and can keep its normal auto-lock behavior.

Set the key once using hidden terminal input:

```sh
phoenix-secret set acoustid
```

Check local availability without revealing it, or delete it when needed. The
check confirms the credential is stored, not that AcoustID accepts it:

```sh
phoenix-secret check acoustid
phoenix-secret delete acoustid
```

NixOS enables GNOME Keyring and its GCR Secret Service prompt without enabling
GNOME desktop or GDM. Its optional PAM hook can auto-unlock the keyring when
login provides the matching account password. Phoenix's SDDM login also allows
YubiKey U2F as a sufficient authentication path; that path supplies no
password to the keyring. After U2F login, the first Secret Service operation
(for example `phoenix-secret check acoustid` or `dlm`) therefore prompts once to
unlock the keyring. It stays unlocked for the remainder of the session, so
later downloads do not prompt. Password login can unlock it during PAM when
the login and keyring passwords match.

## Review and future playlists

Picard is a manual GUI tool for reviewing release/track choices and correcting
tags in `_review`; it is not used by the unattended worker. Future playlists
belong in `/home/v/sync/music/_playlists/`. Playlist files must be generated or
rewritten after the worker moves tracks so their paths point at final locations.
Playlist regeneration is not implemented yet.

## Video downloads

`download video`, `download v`, `dl video`, `dl v`, and `dlv` pass user options
through to yt-dlp and default to `/home/v/Downloads/videos/`. The default output
template is `%(title)s.%(ext)s` (without the YouTube ID), and `--no-overwrites`
protects existing files even if a forwarded option requests forced overwrites.
The wrapper prefers AV1 video and Opus audio sources. A shared Phoenix yt-dlp
postprocessor attempts **AV1 + Opus in WebM** after merge, then applies metadata
and validates the final file before moving it. Audio artwork follows metadata. Compatible streams are copied individually. Video
conversion uses the locked upstream `ab-av1` sampled quality search, preferring
NVIDIA AV1 NVENC when an actual device/driver probe succeeds. `ffmpeg-full` supplies
VMAF, NVENC, SVT-AV1 and Opus in one maintained package. The adapter uses upstream
`crf-search` (NVENC values map to CQ), then performs **one final encode** through
the existing stream-selective FFmpeg path. There is no local bitrate-search algorithm.

Search targets VMAF **96** with a maximum encoded percentage of **100**, minimum
three 10-second samples, the upstream default sample-every interval, eight VMAF
threads and no persistent cache. The one-point search margin responds to observed
sample/full-score variance. The completed file must independently measure
**VMAF >=95 and total size <=100% of the source** before publication. Estimates
are not guarantees: an infeasible search, unexpected optimizer failure, oversized
full output or below-target full score removes the candidate and retains the
validated original with its real codecs and container/extension. Quality limits
are never lowered. A valid download is not discarded for failed optional
compression. Corrupt source/output, required audio conversion, metadata/artwork
and publication failures remain errors. No second video encode is attempted on
optimizer/encoder failure. `--original` bypasses conversion explicitly. Existing
AV1 streams are copied without search. Multi-video sources needing conversion
retain the valid original rather than scoring the wrong track.

NVENC uses P7/HQ, VBR with no fixed bitrate, full-resolution multipass, 32-frame
lookahead and spatial/temporal AQ (strength 8); CQ is selected per source.
Software fallback uses SVT-AV1 preset 6 with eight logical processors and an
upstream-selected CRF under the same constraints. Resolution and timestamps/frame
rate are retained; 10-bit sources remain 10-bit. Search and full VMAF verification
show elapsed activity through the shared renderer, while final encoding shows
percentage/ETA. The complete FFmpeg argument list and search summary appear in
the private diagnostics log. Quality scores do not prove imperceptibility.
See [codec quality validation](MEDIA_CODEC_VALIDATION.md) for the acceptance evidence.
Global/stream metadata and chapters follow FFmpeg's mappings. Unmapped auxiliary
streams (such as embedded subtitles or attachments) are not copied.

`dlv --original <URL>` selects the best source streams and bypasses codec
conversion; merging can still remux their container. Both modes validate media
structure, duration and complete playback before publication. Destination
collisions fail without overwriting the existing output. The wrapper suppresses
extractor chatter. Supported yt-dlp progress templates emit records to a small terminal
adapter. It aggregates the selected stream sizes into a ten-block progress bar. When
sizes are unavailable, video/audio are weighted 90/10; completion is withheld
until every selected stream finishes. One download line updates in place on a
TTY, followed by the separate merge phase. Redirected output prints completed downloads/merges, concise original fallback
reasons and the final overall result. Encoding shares the renderer, uses
media timestamps for percentages, and shows ETA once useful timing is available.
Unknown duration shows activity without a percentage. Playback validation is a
separate phase; encoding stays below 100% and does not announce overall success.
Metadata and artwork have their own phase labels, and the final staged file is
validated again before publication. Only the `Merger` postprocessor gets a merge label;
`MoveFiles` does not. During a merge, the TTY shows elapsed seconds until one
completion line replaces it. Errors and warnings remain visible. Add `-v` or `--verbose` for
yt-dlp, FFmpeg and ab-av1 diagnostics. Internal optimizer INFO/debug output is
retained in the private log and shown only in verbose mode. Errors identify
download, encoding, metadata/artwork or validation stages. For example:

```sh
download video -S "res:1080" <URL>
download video <URL> -P /some/other/directory
dlv -F <URL>
dlv --verbose <URL>
```

For X/Twitter status URLs, `dlm` and `dlv` default to yt-dlp's
`--playlist-items 1`. This can exclude additional media in the requested post;
extractor ordering is not guaranteed, so it does not reliably identify the
requested post over a quoted post. An explicit `--playlist-items` (or `-I`)
overrides the default. Other providers are unchanged. Mixed-provider calls receive
no automatic limit because yt-dlp applies this option to the entire invocation.

Music and video retry recognizable transport failures (including HTTP 403,
408, 429, 5xx, timeout, and reset) with fresh yt-dlp processes: three complete
attempts at most, separated by 1 and 5 seconds. Recovered error messages are
hidden in normal mode; verbose mode shows them and the retries. Terminal errors
remain visible and nonzero. Attempt timestamps, arguments, and output are kept
in user-only `~/.local/state/phoenix-media/downloads/*.log`; those private logs
may contain temporary signed media URLs and should be shared selectively.

Normal audio/video components and partial outputs live in isolated
`~/.cache/phoenix-media/{audio,video}.XXXXXXXX/attempt-N/` directory via yt-dlp's supported
`--paths temp:` option. On Phoenix's default home Btrfs filesystem, the completed
video is renamed into the final directory, so incomplete media is never
published there. Owned staging directories are removed on success/failure.
Explicit `--keep-video` retains diagnostic staging and allows yt-dlp to publish
kept component streams alongside the final video; it is intentionally different
from normal mode. Advanced absolute output templates or destinations on another
filesystem can override yt-dlp's staging/rename behavior.

Phoenix keeps non-expiring tmpfiles rules for the music inbox, review directory,
and video destination.

### Merge diagnosis

An October 8, 2026 reproduction of the previously tested URL selected `401+251`
(AV1 in MP4, 62,272,441 bytes; Opus in WebM, 3,014,675 bytes). The installed
FFmpeg 8.1.2 merger used the same binary as the earlier local benchmark:

```text
/nix/store/sn7z7xxxq7jj211vglsyc81q4g8kxpk2-ffmpeg-8.1.2-bin/bin/ffmpeg
-y -loglevel repeat+info
-i file:<video.f401.mp4> -i file:<audio.f251.webm>
-c copy -map 0:v:0 -map 1:a:0 -movflags +faststart file:<output.temp.webm>
```

There was one merge, no pacing options (`-re`/`-readrate`), and no re-encoding.
Replaying the exact command on retained original components took 0.034 seconds,
also 0.034 seconds with output on the home Btrfs filesystem. A real yt-dlp
localhost fixture using those components completed the entire wrapper in
0.38 seconds, with merge time around 0.1 seconds. The reported three-minute
delay remains unexplained; no speculative FFmpeg tuning was applied. The old
repeated merge notices were `Merger` and `MoveFiles` progress events sharing the
same unconditional template. If the delay returns, retain components with
`dlv --verbose --keep-video <same URL>` and capture the running FFmpeg arguments
and process elapsed/CPU time while it is stalled. A fast remux of an already
merged file alone cannot explain the original delay.

The remaining slow-live-merge investigation needs process evidence during a
coordinated reproduction. Before running the known affected URL, start the
collector **on the host** (the agent sandbox needs explicit host-process access):

```sh
python3 modules/apps/media/media-cli.py diagnose-merge \
  --output /tmp/phoenix-live-merge.jsonl --seconds 240
dlv --verbose --keep-video <previously-tested-URL>
```

Run the collector in a second terminal. Its output file must not already exist;
it is created with mode 0600. It records only the user's FFmpeg processes:
executable, argument vector, CPU/wait state, I/O counters, and open-file sizes at
0.5-second intervals. It does not collect environment variables or credentials.
No performance flags have been changed without an observed mechanism.

The subsequent live acceptance test used the actual Phoenix `dlv`, but explicitly
changed the home output path to a private acceptance directory and enabled
`--keep-video`. Its output therefore did not belong in `~/Downloads/videos/`.
It downloaded both `401+251` streams, merged with `-c copy`, and published a
65,270,000-byte, 184.821-second AV1/Opus WebM at the requested test destination.
Beginning/end playback samples decoded successfully; a full packet scan timed
out, so a full decode was not established. The 0.5-second process collector
captured no samples and does not establish an exact merge duration.

The packaged yt-dlp executable prepends its own FFmpeg 9.0.1 to PATH, overriding
the Phoenix wrapper's stable FFmpeg 8.1.2 PATH entry. The live log confirms 9.0.1;
the earlier explicit-binary benchmark used 8.1.2. Consequently that benchmark
is not a comparison of identical executables. Staging and destination also
changed, so the fast test does not demonstrate that staging fixed the reported
three-minute delay. No performance tuning or binary-selection change has been
applied on that assumption.

Final verification compared identical retained inputs, output path, and copy
arguments: FFmpeg 8.1.2 completed in 0.036 seconds and 9.0.1 in 0.072 seconds.
The version difference does not establish the historical slowdown's cause.
A stalled packet scan was observed in `fanotify_handle_event`. Phoenix enables
ClamAV `OnAccessPrevention` and extra scanning under Downloads. After archiving
the exact unchanged video outside Downloads, full packet scanning completed
successfully (4,435 AV1 and 9,241 Opus packets). This identifies the diagnostic
timeout as location-dependent access scanning, rather than evidence of a corrupt
file. It also supports investigating scanning as the historical merge-delay
mechanism, without claiming a captured slow merge. ClamAV settings are unchanged.

## Earlier codec policy and recovery

Before preferred-output enforcement, fallback video downloads retained source
codecs and could use MKV or the original container. The current selective
AV1/Opus policy above supersedes that behavior; `--original` retains the earlier
source-codec behavior explicitly. Container-only `--recode-video webm` does not
provide this codec guarantee.

The existing X AAC/MP4 failure was caused by remux-only processing followed by
an ingestion extension rejection. It has been recovered to Opus and routed to
`_review` after a real AcoustID no-match result. Its original MP4 is preserved
privately under `~/.cache/phoenix-media/diagnostics/x-audio-recovery/`. New music
runs enforce Opus extraction before the common ingestion hook. An explicit
rejection by that hook now produces a CLI error rather than false success.
