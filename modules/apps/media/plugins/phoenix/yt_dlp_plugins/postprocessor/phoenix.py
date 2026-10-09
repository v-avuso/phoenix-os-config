"""Phoenix conversion, metadata, artwork and validation run before publication."""
import importlib.util
import json
import os
from pathlib import Path

from mutagen import MutagenError
from mutagen.oggopus import OggOpus

from yt_dlp.postprocessor.common import PostProcessor
from yt_dlp.postprocessor.embedthumbnail import EmbedThumbnailPP
from yt_dlp.postprocessor.ffmpeg import FFmpegMetadataPP
from yt_dlp.utils import PostProcessingError


class PhoenixCodecsPP(PostProcessor):
    def __init__(self, downloader=None, mode="video", original="false"):
        super().__init__(downloader)
        self.mode = mode
        self.original = original == "true"
        helper = Path(os.environ["PHOENIX_MEDIA_CLI_HELPER"])
        spec = importlib.util.spec_from_file_location("phoenix_media_cli", helper)
        self.cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.cli)

    @staticmethod
    def emit(**event):
        print('PHOENIX_ENCODE ' + json.dumps(event), flush=True)

    def destination_available(self, info, output):
        final = Path(info.get("__finaldir", output.parent)) / output.name
        # yt-dlp's move step only warns about collisions. Refuse before publication.
        if final.exists() and (final.absolute() != output.absolute() or info.get("__real_download") is False):
            raise PostProcessingError(f"Publication failed: destination already exists: {final.name}")

    def metadata(self, info, output):
        info["filepath"], info["ext"] = str(output), output.suffix[1:]
        streams = self.cli.probe_media(output).get("streams", [])
        info["vcodec"] = next((s["codec_name"] for s in streams if s.get("codec_type") == "video"
                               and not s.get("disposition", {}).get("attached_pic")), "none")
        info["acodec"] = next((s["codec_name"] for s in streams if s.get("codec_type") == "audio"), "none")
        self.emit(status="metadata")
        try:
            pictures = OggOpus(output).get("metadata_block_picture", []) if self.mode == "audio" else []
            # Upstream remuxes all streams. Artwork must be attached only AFTER this
            # step: Ogg cover art is exposed as video that the Opus muxer rejects.
            files, info = FFmpegMetadataPP(self._downloader, add_metadata=True,
                                          add_chapters=True, add_infojson=False).run(info)
            if pictures:
                audio = OggOpus(output)
                audio["metadata_block_picture"] = pictures
                audio.save()
            return files, info
        except (PostProcessingError, MutagenError, OSError, ValueError) as error:
            raise PostProcessingError(f"Metadata processing failed: {error}") from error

    def run(self, info):
        source = Path(info["filepath"])
        try:
            source_media = self.cli.probe_media(source)
        except self.cli.MediaIntegrityError as error:
            raise PostProcessingError(f"Media validation failed: {error}") from error
        source_size = source.stat().st_size
        expected = source if self.original else source.with_suffix(".webm" if self.mode == "video" else ".opus")
        self.destination_available(info, expected)
        try:
            output = self.cli.enforce_codecs(source, self.mode, original=self.original,
                                             emit=lambda record: print(record, flush=True))
        except self.cli.MediaIntegrityError as error:
            raise PostProcessingError(f"Media validation failed: {error}") from error
        except (OSError, ValueError, RuntimeError) as error:
            raise PostProcessingError(f"Encoding failed: {error}") from error
        self.destination_available(info, output)
        deleted, info = self.metadata(info, output)
        converted_video = self.mode == "video" and output != source and info["vcodec"] == "av1" and any(
            s.get("codec_type") == "video" and s.get("codec_name") != "av1"
            for s in source_media.get("streams", []))
        if converted_video and output.stat().st_size > source_size:
            # Container tags count toward the completed-size limit too.
            output.unlink()
            output = self.cli.retain_original(source, source_media,
                       self.cli.OptimizationUnavailable("completed output with metadata exceeds source size"),
                       lambda record: print(record, flush=True))
            self.destination_available(info, output)
            files, info = self.metadata(info, output)
            deleted.extend(files)
        if self.mode == "audio" and info.get("thumbnails"):
            self.emit(status="artwork")
            try:
                files, info = EmbedThumbnailPP(self._downloader).run(info)
                deleted.extend(files)
            except PostProcessingError as error:
                raise PostProcessingError(f"Artwork processing failed: {error}") from error
        self.emit(status="validating")
        try:
            fallback = self.mode == "video" and (info["vcodec"] != "av1" or info["acodec"] not in ("opus", "none"))
            self.cli.validate_media(output, self.mode, source_media, original=self.original or fallback)
        except (OSError, ValueError, RuntimeError) as error:
            raise PostProcessingError(f"Media validation failed after metadata/artwork: {error}") from error
        if output != source:
            deleted.append(str(source))
        return deleted, info
