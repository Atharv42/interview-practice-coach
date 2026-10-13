"""WebSocket API endpoints for real-time practice audio, visual frames, and live alerts."""

import base64
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.models.streaming import (
    ClientMessageType,
    ServerMessageType,
    StreamStartConfig,
)
from app.models.visual import VisualFrameSample
from app.pipeline.streaming_session import StreamingSession
from app.storage.session_repository import SessionRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["Real-Time Streaming"])


@router.websocket("/practice")
@router.websocket("/practice/{session_id}")
async def practice_streaming_endpoint(
    websocket: WebSocket,
    session_id: str | None = None,
) -> None:
    """Handle bidirectional real-time delivery mechanics streaming.

    Accepts live audio chunks and geometric visual landmark frames. Emits live
    pacing updates and delivery alerts. Consolidates final report when stream ends.
    """
    await websocket.accept()

    repo = SessionRepository()
    active_session: StreamingSession | None = None

    try:
        # Default starting configuration if not explicitly provided
        active_session = StreamingSession(
            config=StreamStartConfig(session_id=session_id),
            repository=repo,
        )

        # Notify client connection is ready
        await websocket.send_json(
            {
                "type": ServerMessageType.READY,
                "session_id": active_session.session_id,
                "message": "Real-time streaming pipeline initialized and ready.",
            }
        )

        while True:
            # Handle both text (JSON) and binary (direct audio bytes) frames
            message = await websocket.receive()

            if "bytes" in message and message["bytes"]:
                # Direct binary audio chunk
                raw_bytes = message["bytes"]
                alerts = active_session.process_audio_chunk(raw_bytes)
                for alert in alerts:
                    await websocket.send_json(
                        {"type": ServerMessageType.ALERT, "alert": alert.model_dump()}
                    )
                continue

            if "text" not in message or not message["text"]:
                continue

            text_payload = message["text"]
            try:
                data = json.loads(text_payload)
            except json.JSONDecodeError:
                await websocket.send_json(
                    {
                        "type": ServerMessageType.ERROR,
                        "message": "Malformed JSON payload received.",
                    }
                )
                continue

            msg_type = data.get("type")

            # 1. Custom initialization
            if msg_type == ClientMessageType.START:
                raw_cfg = data.get("config", {})
                if session_id and "session_id" not in raw_cfg:
                    raw_cfg["session_id"] = session_id
                cfg = StreamStartConfig(**raw_cfg)
                active_session = StreamingSession(config=cfg, repository=repo)
                await websocket.send_json(
                    {
                        "type": ServerMessageType.READY,
                        "session_id": active_session.session_id,
                        "message": "Stream configured.",
                    }
                )

            # 2. Audio chunk (base64 encoded)
            elif msg_type == ClientMessageType.AUDIO_CHUNK:
                b64_data = data.get("data", "")
                if b64_data:
                    raw_audio = base64.b64decode(b64_data)
                    elapsed = data.get("elapsed_seconds")
                    alerts = active_session.process_audio_chunk(raw_audio, elapsed)
                    for alert in alerts:
                        await websocket.send_json(
                            {"type": ServerMessageType.ALERT, "alert": alert.model_dump()}
                        )

            # 3. Client-side visual landmark frame
            elif msg_type == ClientMessageType.VISUAL_FRAME:
                raw_frame = data.get("frame", {})
                frame = VisualFrameSample(**raw_frame)
                update, alerts = active_session.process_visual_frame(frame)

                # Send running metrics update
                await websocket.send_json(
                    {
                        "type": ServerMessageType.METRICS_UPDATE,
                        "update": update.model_dump(),
                    }
                )

                # Send any triggered alerts
                for alert in alerts:
                    await websocket.send_json(
                        {"type": ServerMessageType.ALERT, "alert": alert.model_dump()}
                    )

            # 4. Check silence / pause
            elif msg_type == "silence_check":
                elapsed = data.get("elapsed_seconds", active_session.get_elapsed_seconds())
                alerts = active_session.process_silence_interval(float(elapsed))
                for alert in alerts:
                    await websocket.send_json(
                        {"type": ServerMessageType.ALERT, "alert": alert.model_dump()}
                    )

            # 5. Heartbeat Ping
            elif msg_type == ClientMessageType.PING:
                await websocket.send_json({"type": ServerMessageType.PONG})

            # 6. Stream completion
            elif msg_type == ClientMessageType.STOP:
                report = active_session.finalize()
                await websocket.send_json(
                    {
                        "type": ServerMessageType.FINAL_REPORT,
                        "report": report.model_dump(),
                    }
                )
                break

            else:
                await websocket.send_json(
                    {
                        "type": ServerMessageType.ERROR,
                        "message": f"Unrecognized message type '{msg_type}'.",
                    }
                )

    except WebSocketDisconnect:
        # Graceful disconnect
        if active_session:
            try:
                active_session.finalize()
            except Exception as e:
                logger.warning("Error finalizing disconnected session: %s", e)
    except Exception as e:
        logger.exception("Unexpected error in WebSocket session: %s", e)
        try:
            await websocket.send_json(
                {
                    "type": ServerMessageType.ERROR,
                    "message": f"Server processing error: {e}",
                }
            )
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
