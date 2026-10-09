# Preferred media codec validation

Validation on Phoenix's RTX 5090, 8 October 2026. Decimal MB below.
The source is the previously saved [Astra Blue AI clip](https://x.com/AstrablueAI/status/2107859808657490208).
Original SHA-256: `607d6ce8658b1d8b3dadc76691c4b8d02a9af51bb2e46026ae137d994114dd96`.
It was preserved throughout testing.

## Source and initial output

FFprobe reports 269.738 seconds, H.264/AAC, 1920×1080,
`10103/421` average FPS, `yuv420p`, 252,408,928 bytes, 7.486 Mbit/s overall.
Compressed packet payloads are 247,949,303 bytes video and 4,315,820 bytes audio.
The audio's packet-byte/PTS-span rate is about 128 kbit/s.

The initial fixed CQ 23 output was AV1/Opus WebM, 269.746 seconds,
with the same resolution, average FPS and pixel format. It contained
372,254,507 bytes, 11.040 Mbit/s overall: video payload 367,841,673 bytes,
audio payload 4,268,050 bytes. Encoding took 24.03 seconds.
NVENC VBR with `-b:v 0 -cq 23` correctly applied its quality target; verbose
encoder diagnostics reported CQ 5888 (23 × 256). That high, unconstrained
quality target spent more bits than the compressed source. This was a policy
problem, not an ignored CQ setting or a bitrate conversion bug.

## Bounded evaluation

Three decoded-source, lossless reference segments at 15, 120 and 235 seconds,
each approximately ten seconds, were compared with matching decoded frames.
NVENC settings were P7/HQ, VBR, zero bitrate target, full-resolution multipass,
32-frame lookahead, spatial and temporal AQ, GOP 250, original frame timing.

| CQ | Aggregate video MB | Mean VMAF | Encode seconds |
| --- | ---: | ---: | ---: |
| 23 | 41.73 | 98.54 | 4.16 |
| 28 | 26.69 | 97.63 | 4.14 |
| 32 | 18.00 | 96.53 | 4.21 |
| 36 | 11.92 | 95.01 | 4.17 |

This small evaluation established that useful savings were feasible. It is not
an optimization framework and does not select the production quality setting.

## Upstream search and completed output

Locked Nixpkgs supplies ab-av1 0.11.2. Its exact source maps NVENC search CRF to
FFmpeg `-cq`; its sampled search supports the size constraint directly.
Phoenix's maintained FFmpeg-full 8.1.2 provides NVENC, libopus, libsvtav1 and
libvmaf. The former minimal FFmpeg build lacked libvmaf. No lock update,
custom FFmpeg build or vendor abstraction is needed.

Initial upstream search at VMAF 95 / maximum encoded size 80%, three ten-second
samples, took 32.47 seconds and selected CQ 38 with sampled VMAF 95.13.
The full output scored 94.76227. The independent publication gate rejected it
and removed its staging output; it was not published. Its completed byte count
was not recorded before cleanup.

The initial policy evaluated here searched at VMAF 96, retaining a full-output
floor of 95 and an actual total-file ceiling of 80% of source bytes. The revised
100% policy and original fallback below supersede that initial size/error policy. The one-point sample
margin addresses this observed sample/full variance; it is not a guarantee.

| Completed encode | Bytes (MB) | Full VMAF | Encode seconds |
| --- | ---: | ---: | ---: |
| Previous CQ 23 | 372,254,507 (372.25) | 98.87488 | 24.03 |
| Manual CQ 32 feasibility check | 168,339,797 (168.34) | 97.14642 | 23.99 |
| Upstream search at 96: CQ 35 | 125,372,419 (125.37) | 96.09109 | 24.13 |

The final sampled score was 96.17. Search took approximately 33.09 seconds;
encoding plus playback/quality validation took 63.45 seconds, for 96.54 seconds
total. Actual savings are 50.3% against the original and 66.3% against CQ 23.
The final output is AV1/Opus WebM, 1920×1080, original average FPS, `yuv420p`,
269.746 seconds, 3.718 Mbit/s overall. AAC became Opus VBR at 128 kbit/s.
Full decoding passed; title, artist, date and source URL metadata survived.

Actual final video arguments (stream-scoped in the implementation):

```text
-c:v av1_nvenc -preset p7 -tune hq -rc vbr -b:v 0
-multipass fullres -rc-lookahead 32 -spatial-aq 1 -temporal-aq 1
-cq 35 -g 250 -pix_fmt yuv420p -fps_mode passthrough
```

Production search uses `--min-vmaf 96 --max-encoded-percent 80 --min-samples 3
--sample-duration 10s --cache false --vmaf n_threads=8 --vmaf-fps 0
--vmaf-scale none`, with identical encoder settings. Upstream chooses sample
positions/count, and may use a full pass for very short inputs. Search never
uses repeated full-file encodes on this representative clip. Full validation
uses upstream `ab-av1 vmaf`, preserving its nearest-timestamp alignment for VFR.
A naive manual VFR comparison without matching timestamps gave a misleading
score and was excluded from the results above.

Objective scores measure decoded-source similarity, not perceptual equivalence.
Spot checks of text, faces and detailed scene frames supplement decoding and
metrics; they cannot establish imperceptibility for every viewer or scene.
HDR, 4K, long-form sources and real software-search performance remain outside
this representative acceptance benchmark. Fixtures cover software conversion,
selective copying, original bypass and publication failure cleanup.

Sources: [ab-av1 0.11.2](https://github.com/alexheretic/ab-av1/tree/v0.11.2),
[NVENC CQ mapping](https://github.com/alexheretic/ab-av1/blob/v0.11.2/src/ffmpeg.rs),
[FFmpeg NVENC implementation](https://github.com/FFmpeg/FFmpeg/blob/n8.1.2/libavcodec/nvenc.c).

## Integrated acceptance

All 75 media tests passed with FFmpeg-full on PATH, including real codec copying,
conversion, playback validation, software conversion and quality-failure cleanup.
`nix flake check --no-build --no-write-lock-file .` passed for metal, VM and default.
`phoenix-build` completed the full system build. The built configuration was
activated temporarily via the documented graphical Polkit test flow (the pinned
`phoenix-test` rebuild path hardcodes terminal sudo). No boot profile was changed.

The installed `dlv` then processed the preserved local source end to end:
96.80 seconds, successful publication of 125,372,526 bytes, with the same CQ 35
and validation result. The 107-byte difference from the helper benchmark is
container metadata from yt-dlp. Download staging was removed after completion.
Original source hash remained unchanged. Visual spot checks at 20 and 125 seconds
retained readable text and scene structure, with visible fine-grain smoothing;
no claim of imperceptibility is made. Human playback acceptance remains pending.

An installed `dlv` run on the completed AV1/Opus output took 10.08 seconds and
copied both streams with identical per-packet SHA-256 hashes. It bypassed encoding
and quality search as intended.


## Regression correction and current acceptance

The current search ceiling is **100%**, with sampled VMAF **96** and full-file
VMAF **95** unchanged. Converted video must still be no larger than its source,
including final container metadata. Unavailable optimization or an unacceptable
candidate retains the fully validated original. No relaxed quality setting or
second full video encode is attempted. Genuine integrity and required audio,
metadata/artwork or publication failures remain errors.

The audio regression was reproduced on the original X URL with verbose logging.
Opus conversion and Mutagen artwork embedding succeeded. The later upstream
metadata processor ran `-map 0 -c copy` on the Ogg file; FFmpeg exposed the cover
as an attached MJPEG stream and failed with:

```text
[opus] Unsupported codec id in stream 1
Could not write header (incorrect codec parameters ?): Invalid argument
```

The plugin now explicitly sequences supported yt-dlp processors: codec conversion,
FFmpeg metadata, Mutagen artwork, final playback validation, then move/ingestion.
Built-in duplicate metadata/artwork processors are disabled. Audio metadata remux
excludes picture streams, and existing Ogg Vorbis pictures are restored with
Mutagen after remux, including when no new thumbnail is available. This keeps
upstream metadata mapping and artwork handling rather than adding a tag framework.

Real-runtime source-wrapper trials used the same pinned yt-dlp, FFmpeg-full and
ab-av1 packages as Nix. Disposable staging/output and a review hook with an
explicitly unavailable test key avoided modifying the personal library or reading
credentials. The X AAC clip produced a **4,378,237-byte Opus** file with cover art,
title, artist, year and source URL, passed final decoding, and reached review.
The missing-key review notice was expected in this isolated trial.

The other X post had two video entries:

| Entry | Published file | Actual codecs | Result |
| --- | ---: | --- | --- |
| 1 | 353,240,090-byte MKV | H.264/AAC | Search infeasible; validated original retained |
| 2 | 114,257,518-byte WebM | AV1/Opus | CQ 33; sampled VMAF 96.44; full VMAF 95.70175 |

Entry 2 encoded once in **15.98 seconds**. Encoding plus helper playback/VMAF
validation took 43.46 seconds; subsequent metadata and final playback validation
preceded publication. Downloaded components totaled 123,903,639 bytes; the exact
merged input byte count was not retained before staging cleanup. Both final files
had correct extensions and destinations; no INFO/debug logs escaped normal mode.
Private diagnostics retain the upstream search logs and actual FFmpeg arguments.

Regression fixtures include both AAC and existing Opus with metadata/artwork,
packet-identical Opus copying, preservation of existing artwork without a new
thumbnail, actual ingestion/review routing, optimization success/infeasibility/
unexpected failure, candidate cleanup, and failure after metadata/artwork before
publication. Video integration fixtures stub optimizer results, while the real X
trial above establishes upstream search and full-file quality behavior.

Regression verification at that stage: **87 media tests passed** with the pinned runtime
and no runtime cases skipped; flake evaluation and the full Phoenix build passed.
The built helper/plugin were byte-identical to the tested working sources.
The Nix-built `dlv` also copied the real accepted AV1/Opus clip in 16.83 seconds
with identical video/audio packet hashes, final metadata, and playback validation.

Temporary activation was attempted through graphical Polkit but authentication
did not complete. The pending request was cancelled; at that stage the revision was **not
activated**, no boot profile was changed and no commit had been made. The prior test
configuration remains active. Installed-command activation, personal-library
AcoustID acceptance and human playback/visual acceptance remain separate from
the completed disposable runtime evidence above.

## Final workstream verification

All **91 media tests passed**, including real yt-dlp/FFmpeg checks for video
upload-year mapping on optimized WebM and original MP4 fallback, and absence
of an invented year when no upload date exists. Flake evaluation and the full
Phoenix build passed. Existing files were inspected without new downloads;
no activation was performed. Workflow and validation documentation and fixture
instructions now live with the media module.

Read-only inspection of existing X downloads found FFprobe `DATE=2026` and
correct artists. The exact Thunar media-tags 0.6.0 source substitutes 2006 for
TagLib year zero; its linked TagLib 2.2.1 returned zero for those same video
files. Earlier files with no date also returned zero. This establishes the
display fallback; Phoenix's supported upload-year mapping is unchanged.
