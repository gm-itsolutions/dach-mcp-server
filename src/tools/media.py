"""
Media Processing Tools
======================
Video → Keyframes Extraktion und EXIF-Metadaten aus Baustellenfotos.
"""

import subprocess
import base64
import json
import os
import shutil
import uuid
from pathlib import Path

from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

TEMP_DIR = Path(os.getenv("TEMP_DIR", "/tmp/processing"))


def _get_work_dir() -> Path:
    """Erstellt ein einzigartiges temporäres Arbeitsverzeichnis."""
    work_dir = TEMP_DIR / f"job_{uuid.uuid4().hex[:12]}"
    work_dir.mkdir(parents=True, exist_ok=True)
    return work_dir


def _cleanup(work_dir: Path) -> None:
    """Räumt temporäre Dateien auf."""
    try:
        shutil.rmtree(work_dir, ignore_errors=True)
    except Exception:
        pass


def _gps_dms_to_decimal(dms_tuple, ref: str) -> float:
    """Konvertiert GPS DMS (Grad, Minuten, Sekunden) zu Dezimalgrad."""
    try:
        degrees = float(dms_tuple[0])
        minutes = float(dms_tuple[1])
        seconds = float(dms_tuple[2])
        decimal = degrees + minutes / 60.0 + seconds / 3600.0
        if ref in ("S", "W"):
            decimal = -decimal
        return round(decimal, 6)
    except (TypeError, IndexError, ValueError):
        return 0.0


def _extract_exif(image_path: Path) -> dict:
    """Extrahiert EXIF-Daten inkl. GPS-Koordinaten aus einem Bild."""
    try:
        img = Image.open(image_path)
        exif_data = img._getexif()
        if not exif_data:
            return {"info": "Keine EXIF-Daten vorhanden"}

        result = {}
        gps_raw = {}

        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, str(tag_id))

            if tag == "GPSInfo":
                for gps_tag_id, gps_value in value.items():
                    gps_tag = GPSTAGS.get(gps_tag_id, str(gps_tag_id))
                    gps_raw[gps_tag] = gps_value
            elif tag in ("DateTime", "DateTimeOriginal", "DateTimeDigitized"):
                result[tag] = str(value)
            elif tag in ("Make", "Model", "Software"):
                result[tag] = str(value)
            elif tag == "Orientation":
                result["Orientation"] = int(value)
            elif tag in ("ImageWidth", "ImageLength"):
                result[tag] = int(value)

        # GPS-Koordinaten berechnen
        if gps_raw:
            try:
                lat = _gps_dms_to_decimal(
                    gps_raw.get("GPSLatitude", (0, 0, 0)),
                    gps_raw.get("GPSLatitudeRef", "N"),
                )
                lon = _gps_dms_to_decimal(
                    gps_raw.get("GPSLongitude", (0, 0, 0)),
                    gps_raw.get("GPSLongitudeRef", "E"),
                )
                if lat != 0.0 or lon != 0.0:
                    result["gps_latitude"] = lat
                    result["gps_longitude"] = lon
                    result["gps_maps_url"] = (
                        f"https://www.google.com/maps?q={lat},{lon}"
                    )
            except Exception:
                pass

            if "GPSAltitude" in gps_raw:
                try:
                    alt = float(gps_raw["GPSAltitude"])
                    result["gps_altitude_m"] = round(alt, 1)
                except (TypeError, ValueError):
                    pass

        return result
    except Exception as e:
        return {"error": f"EXIF-Extraktion fehlgeschlagen: {str(e)}"}


def _get_video_info(video_path: Path) -> dict:
    """Extrahiert Video-Metadaten mit ffprobe."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format", "-show_streams",
                str(video_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        data = json.loads(result.stdout)
        fmt = data.get("format", {})

        info = {
            "duration_seconds": round(float(fmt.get("duration", 0)), 1),
            "size_mb": round(int(fmt.get("size", 0)) / (1024 * 1024), 2),
            "format": fmt.get("format_long_name", "unbekannt"),
        }

        # Video-Stream Info
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                info["width"] = stream.get("width")
                info["height"] = stream.get("height")
                info["codec"] = stream.get("codec_name")
                break

        return info
    except Exception as e:
        return {"error": str(e)}


def register_media_tools(mcp):
    """Registriert alle Media-Processing Tools beim MCP Server."""

    @mcp.tool()
    def video_to_frames(
        video_base64: str,
        interval_seconds: int = 3,
        max_frames: int = 8,
    ) -> str:
        """Extrahiert Keyframes aus einem Baustellenvideo für die Gefährdungsanalyse.

        Nimmt ein Base64-kodiertes Video, extrahiert Einzelbilder in regelmäßigen
        Abständen und gibt diese als Base64-Bilder zurück. Zusätzlich werden
        Video-Metadaten (Dauer, Auflösung) extrahiert.

        Die extrahierten Frames können anschließend vom Vision-Modell analysiert
        werden, um Gefährdungen auf der Baustelle zu erkennen.

        Args:
            video_base64: Das Video als Base64-kodierter String
            interval_seconds: Zeitabstand zwischen den extrahierten Frames (Standard: 3 Sek.)
            max_frames: Maximale Anzahl der Frames (Standard: 8, Maximum: 15)

        Returns:
            JSON-String mit:
            - frames: Array mit frame_number, timestamp_seconds und image_base64
            - video_info: Metadaten zum Video (Dauer, Auflösung, Format)
            - frame_count: Anzahl der extrahierten Frames
        """
        max_frames = min(max_frames, 15)  # Hardlimit
        work_dir = _get_work_dir()

        try:
            # Video dekodieren und speichern
            video_bytes = base64.b64decode(video_base64)
            video_path = work_dir / "input.mp4"
            video_path.write_bytes(video_bytes)

            # Video-Metadaten
            video_info = _get_video_info(video_path)

            # Frames extrahieren mit ffmpeg
            output_pattern = str(work_dir / "frame_%04d.jpg")
            cmd = [
                "ffmpeg", "-i", str(video_path),
                "-vf", f"fps=1/{interval_seconds}",
                "-frames:v", str(max_frames),
                "-q:v", "3",       # Gute Qualität (1=best, 31=worst)
                "-vf", f"fps=1/{interval_seconds},scale='min(1920,iw)':'-1'",
                output_pattern,
            ]

            proc = subprocess.run(cmd, capture_output=True, timeout=120)
            if proc.returncode != 0:
                return json.dumps({
                    "success": False,
                    "error": f"ffmpeg Fehler: {proc.stderr.decode()[-500:]}",
                })

            # Frames einlesen
            frames = []
            for frame_path in sorted(work_dir.glob("frame_*.jpg")):
                frame_b64 = base64.b64encode(frame_path.read_bytes()).decode()
                frame_num = len(frames) + 1

                frame_data = {
                    "frame_number": frame_num,
                    "timestamp_seconds": (frame_num - 1) * interval_seconds,
                    "image_base64": frame_b64,
                }

                # EXIF aus erstem Frame extrahieren (für GPS falls vorhanden)
                if frame_num == 1:
                    exif = _extract_exif(frame_path)
                    if exif and "error" not in exif:
                        frame_data["metadata"] = exif

                frames.append(frame_data)

            return json.dumps({
                "success": True,
                "frame_count": len(frames),
                "video_info": video_info,
                "frames": frames,
            })

        except subprocess.TimeoutExpired:
            return json.dumps({
                "success": False,
                "error": "Video-Verarbeitung hat zu lange gedauert (Timeout 120s)",
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Fehler bei Video-Verarbeitung: {str(e)}",
            })
        finally:
            _cleanup(work_dir)

    @mcp.tool()
    def extract_image_metadata(image_base64: str) -> str:
        """Extrahiert EXIF-Metadaten aus einem Baustellenfoto.

        Liest GPS-Koordinaten (für automatische Baustellenzuordnung),
        Aufnahmezeitpunkt und Kamera-Informationen aus dem Bild.

        Args:
            image_base64: Das Bild als Base64-kodierter String (JPEG oder PNG)

        Returns:
            JSON-String mit EXIF-Daten:
            - gps_latitude/gps_longitude: Koordinaten (falls vorhanden)
            - gps_maps_url: Google Maps Link zur Position
            - DateTime: Aufnahmezeitpunkt
            - Make/Model: Kamera/Smartphone-Modell
            - ImageWidth/ImageLength: Bildauflösung
        """
        work_dir = _get_work_dir()

        try:
            img_bytes = base64.b64decode(image_base64)
            img_path = work_dir / "image.jpg"
            img_path.write_bytes(img_bytes)

            exif = _extract_exif(img_path)

            # Zusätzlich Bilddimensionen ermitteln falls nicht in EXIF
            if "ImageWidth" not in exif:
                try:
                    img = Image.open(img_path)
                    exif["ImageWidth"] = img.width
                    exif["ImageLength"] = img.height
                except Exception:
                    pass

            return json.dumps({
                "success": True,
                "metadata": exif,
            })

        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Fehler bei Metadaten-Extraktion: {str(e)}",
            })
        finally:
            _cleanup(work_dir)
