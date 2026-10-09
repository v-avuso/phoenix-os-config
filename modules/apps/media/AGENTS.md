# Media pipeline guidance

- Keep codec policy in `media-cli.py` and framework sequencing in the yt-dlp
  plugin. Reuse pinned yt-dlp postprocessors and upstream ab-av1 search; inspect
  their actual ordering/options before extending the pipeline.
- For audio, finish codec conversion and metadata remux before adding artwork.
  FFmpeg exposes Ogg cover art as attached video, which the Opus muxer cannot
  stream-copy. Exclude picture streams from metadata remux and preserve existing
  Vorbis pictures with Mutagen. Verify both AAC conversion and packet-identical
  Opus copying with tags/artwork through the real downloader and ingestion hook.
- Optional video optimization must not discard a valid source. Validate the
  source, search under the current quality/size policy, and check the completed
  output including metadata. On optimizer/constraint failure, clean the candidate
  and publish the valid original with its actual extension/codecs. Integrity,
  required audio encoding, metadata/artwork and publication failures still fail.
- Encoding completion is not overall success. Validate after final metadata and
  artwork, before yt-dlp moves the file or invokes ingestion. Keep internal tool
  diagnostics in the private log and verbose mode; normal progress names phases.
- Test through the actual pinned yt-dlp/FFmpeg pipeline in addition to helper
  fixtures. A helper-only codec test cannot establish postprocessor ordering,
  final path/extension, artwork survival or safe publication.
- Diagnose year reports against embedded FFprobe tags and extractor metadata
  before changing mapping. Thunar media-tags 0.6.0 displays 2006 when TagLib
  returns year zero; a viewer value alone does not justify inventing a tag.
