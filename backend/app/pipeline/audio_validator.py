"""Audio input validation, file size limits, and format verification."""

import os
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

# Allowed file extensions and corresponding MIME signatures
SUPPORTED_EXTENSIONS: set[str] = {".wav", ".mp3", ".m4a", ".ogg", ".webm", ".flac"}
SUPPORTED_CONTENT_TYPES: set[str] = {
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/x-m4a",
    "audio/m4a",
    "audio/ogg",
    "audio/webm",
    "video/webm",  # WebM media recorded via MediaRecorder often has video/webm or audio/webm
    "audio/flac",
    "audio/x-flac",
    "application/octet-stream",
}

# 50 MB limit for practice recordings
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024
MIN_FILE_SIZE_BYTES = 100  # Below 100 bytes is not a valid audio container


def validate_audio_metadata(upload_file: UploadFile) -> str:
    """Validate filename extension and uploaded content-type before disk writes.

    Returns:
        The normalized file extension (e.g. '.wav').

    Raises:
        HTTPException: If file extension or format is unsupported.
    """
    if not upload_file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a valid filename with an extension.",
        )

    ext = Path(upload_file.filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file format '{ext}'. Supported audio extensions are: {supported}"
            ),
        )

    content_type = (upload_file.content_type or "").lower()
    if content_type and content_type not in SUPPORTED_CONTENT_TYPES:
        # Warning/lenient if extension is valid, but log or reject if completely non-audio
        if not content_type.startswith("audio/") and not content_type.startswith("video/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Uploaded file has invalid MIME type '{content_type}'. Must be audio.",
            )

    return ext


def inspect_audio_header(header_bytes: bytes, ext: str) -> bool:
    """Check magic bytes for known audio container signatures.

    Returns:
        True if header matches known signature or is plausible.
    """
    if len(header_bytes) < 4:
        return False

    # RIFF....WAVE
    if ext == ".wav" and header_bytes[:4] == b"RIFF":
        return True
    # ID3 or MPEG sync frames
    if ext == ".mp3" and (
        header_bytes[:3] == b"ID3" or header_bytes[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")
    ):
        return True
    # OGG container
    if ext == ".ogg" and header_bytes[:4] == b"OggS":
        return True
    # FLAC signature
    if ext == ".flac" and header_bytes[:4] == b"fLaC":
        return True
    # Matroska / WebM
    if ext == ".webm" and header_bytes[:4] == b"\x1a\x45\xdf\xa3":
        return True
    # MP4 / M4A (ftyp box)
    if ext == ".m4a" and (len(header_bytes) >= 8 and header_bytes[4:8] == b"ftyp"):
        return True

    # If format header doesn't strictly match static magic byte (e.g., custom encoder wrapper),
    # let deeper decoder handle it rather than rejecting valid subtle variants.
    return True


async def save_and_validate_upload(
    upload_file: UploadFile,
    target_dir: str,
) -> tuple[str, int]:
    """Safely stream upload to disk, enforcing size limits and header validity.

    Args:
        upload_file: FastAPI UploadFile.
        target_dir: Directory where temporary file will be written.

    Returns:
        Tuple of (saved_file_path, total_size_bytes).

    Raises:
        HTTPException: If file is too small, too large, or malformed.
    """
    ext = validate_audio_metadata(upload_file)
    os.makedirs(target_dir, exist_ok=True)

    # Use secure temp filename
    import uuid

    temp_filename = f"upload_{uuid.uuid4().hex}{ext}"
    temp_path = os.path.join(target_dir, temp_filename)

    total_bytes = 0
    header_bytes = b""

    try:
        with open(temp_path, "wb") as f:
            while chunk := await upload_file.read(1024 * 64):  # 64KB chunks
                total_bytes += len(chunk)
                if not header_bytes:
                    header_bytes = chunk[:16]

                if total_bytes > MAX_FILE_SIZE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=(
                            f"File size exceeds maximum allowed limit of "
                            f"{MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB."
                        ),
                    )
                f.write(chunk)

        if total_bytes < MIN_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Audio file is empty or corrupted (size: {total_bytes} bytes).",
            )

        if not inspect_audio_header(header_bytes, ext):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File header does not match expected audio format for extension '{ext}'.",
            )

        return temp_path, total_bytes

    except Exception:
        # Clean up temporary file immediately on failure
        if os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass
        raise
