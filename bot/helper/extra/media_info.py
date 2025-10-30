import os
import ffmpeg

from bot import LOGGER, bot

MAX_ANALYSIS_SIZE = 10 * 1024 * 1024  # 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

async def download_first_10mb(message, download_path: str):
    """Download first 10MB of a file using Pyrogram 2.0.106"""
    try:
        LOGGER.info("Starting download...")
        
        # Get the media file reference
        media = message.video or message.document
        if not media:
            raise ValueError("No media found in message")

        # Get file details
        file_id = media.file_id

        # Download in chunks with proper streaming
        bytes_written = 0
        
        with open(download_path, "wb") as f:
            async for chunk in bot.stream_media(
                file_id,
                limit=1024*1024  # 1MB chunks
            ):
                remaining = MAX_ANALYSIS_SIZE - bytes_written
                if remaining <= 0:
                    break
                
                # Write only the needed portion
                write_size = min(len(chunk), remaining)
                f.write(chunk[:write_size])
                bytes_written += write_size
                #LOGGER.info(f"Downloaded {bytes_written/1024/1024:.1f}MB/10MB")

                if bytes_written >= MAX_ANALYSIS_SIZE:
                    break

        LOGGER.info(f"Download completed. Total downloaded: {bytes_written} bytes")
        return bytes_written

    except Exception as e:
        LOGGER.error(f"Download failed: {str(e)}")
        raise

async def extract_media_info(file_path: str, original_filename: str):
    """Extract media information using ffmpeg"""
    try:
        LOGGER.info("Starting media analysis...")
        probe = ffmpeg.probe(file_path)
        info = {
            "file_name": original_filename,
            "video": {},
            "audio_tracks": [],
            "subtitle_tracks": [],
            "chapters": [],
            "container": "N/A",
            "hdr": None,
            "partial": False
        }

        # Add container format
        info["container"] = probe['format']['format_name'].upper()

        # Check if we got partial file
        file_size = os.path.getsize(file_path)
        info["partial"] = file_size >= MAX_ANALYSIS_SIZE

        # Video information
        video_streams = [s for s in probe["streams"] if s["codec_type"] == "video"]
        if video_streams:
            vs = video_streams[0]
            # Get duration from video stream or format
            video_duration = float(vs.get('duration', 0))
            format_duration = float(probe['format'].get('duration', 0))
            duration = video_duration if video_duration > 0 else format_duration
            # Frame rate calculation
            try:
                if '/' in vs.get('avg_frame_rate', ''):
                    num, den = vs['avg_frame_rate'].split('/')
                    fps = round(float(num)/float(den), 2)
                else:
                    fps = vs.get('r_frame_rate', 'N/A')
            except:
                fps = 'N/A'

            # HDR detection
            hdr_type = None
            color_transfer = vs.get('color_transfer', '')
            if color_transfer == 'smpte2084':
                hdr_type = "HDR10"
            elif color_transfer == 'arib-std-b67':
                hdr_type = "HLG"
            

            info["video"] = {
                "resolution": f"{vs.get('width', 'N/A')}x{vs.get('height', 'N/A')}",
                "codec": vs.get("codec_name", "N/A").upper(),
                "duration": duration,
                "fps": fps,
                "bitrate": int(vs.get('bit_rate', 0)) if vs.get('bit_rate') else None,
                "hdr": hdr_type
            }

        # Audio tracks with enhanced info
        AUDIO_CODEC_MAP = {
            'vorbis': 'Vorbis',
            'opus': 'Opus',
            'aac': 'AAC',
            'mp3': 'MP3',
            'flac': 'FLAC',
            'ac3': 'Dolby Digital',
            'eac3': 'Dolby Digital+',
            'dts': 'DTS',
            'truehd': 'Dolby TrueHD',
            'pcm': 'PCM'
        }
        audio_streams = [s for s in probe["streams"] if s["codec_type"] == "audio"]
        info["audio_tracks"] = [
            {
                "title": s.get("tags", {}).get("title", f"Audio {i+1}"),
                "codec": AUDIO_CODEC_MAP.get(
                    s.get("codec_name", "N/A").lower(), 
                    s.get("codec_name", "N/A").upper()
                ),
                "language": s.get("tags", {}).get("language", "unknown")[:3].upper(),
                "channels": s.get("channels"),
                "sample_rate": int(s.get("sample_rate", 0)) if s.get("sample_rate") else None
            }
            for i, s in enumerate(audio_streams)
        ]

        # Subtitles with codec info
        subtitle_streams = [s for s in probe["streams"] if s["codec_type"] == "subtitle"]
        info["subtitle_tracks"] = [
            {
                "title": s.get("tags", {}).get("title", f"Subtitle {i+1}"),
                "language": s.get("tags", {}).get("language", "unknown")[:3].upper(),
                "codec": s.get("codec_name", "N/A").upper().replace('_', '')
            }
            for i, s in enumerate(subtitle_streams)
        ]

        # Chapter extraction
        try:
            chapter_probe = ffmpeg.probe(
                file_path,
                show_chapters=None,
                print_format="json"
            )
            info["chapters"] = [
                {
                    "id": ch.get("id"),
                    "start": float(ch["start_time"]),
                    "end": float(ch["end_time"]),
                    "title": ch["tags"].get("title", f"Chapter {ch['id']}")
                }
                for ch in chapter_probe.get("chapters", [])
            ]
        except Exception as chap_error:
            LOGGER.warning(f"Chapter extraction failed: {chap_error}")
            info["chapters"] = []

        return info

    except ffmpeg.Error as e:
        LOGGER.error(f"FFmpeg error: {e.stderr.decode()}")
        raise Exception("Failed to analyze media file structure")
    except Exception as e:
        LOGGER.error(f"Analysis error: {str(e)}")
        raise