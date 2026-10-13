"""Unit and integration tests for real-time WebSocket streaming pipeline."""

import base64

import pytest
from fastapi.testclient import TestClient

from app.api.sessions import get_session_repo
from app.main import app
from app.models.streaming import (
    ClientMessageType,
    ServerMessageType,
)
from app.storage.database import Database
from app.storage.session_repository import SessionRepository


@pytest.fixture
def temp_db(tmp_path):
    """Fixture providing an isolated temporary SQLite database."""
    db_file = tmp_path / "test_streaming.db"
    db = Database(db_path=str(db_file))
    yield db
    db.close()


@pytest.fixture
def repo(temp_db):
    """Fixture providing a SessionRepository connected to the temporary database."""
    return SessionRepository(db=temp_db)


@pytest.fixture
def client(repo):
    """FastAPI TestClient with overridden repository."""
    app.dependency_overrides[get_session_repo] = lambda: repo
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_websocket_handshake_and_ready(client):
    """Verify WebSocket connection initializes and emits stream_ready."""
    with client.websocket_connect("/api/v1/ws/practice") as ws:
        ready_msg = ws.receive_json()
        assert ready_msg["type"] == ServerMessageType.READY
        assert "session_id" in ready_msg


def test_websocket_custom_start_configuration(client):
    """Verify client can configure session parameters via stream_start."""
    with client.websocket_connect("/api/v1/ws/practice/custom_sess_100") as ws:
        ready1 = ws.receive_json()
        assert ready1["type"] == ServerMessageType.READY

        # Send custom start config
        ws.send_json(
            {
                "type": ClientMessageType.START,
                "config": {
                    "session_id": "custom_sess_100",
                    "title": "Live Technical Mock",
                    "language": "en",
                    "pause_threshold_seconds": 0.6,
                },
            }
        )
        ready2 = ws.receive_json()
        assert ready2["type"] == ServerMessageType.READY
        assert ready2["session_id"] == "custom_sess_100"


def test_websocket_visual_frame_metrics_update(client):
    """Verify streaming landmark frames triggers incremental metrics updates."""
    with client.websocket_connect("/api/v1/ws/practice") as ws:
        ws.receive_json()  # ready

        frame = {
            "timestamp": 1.0,
            "nose_tip": {"x": 0.50, "y": 0.45},
            "left_iris": {"x": 0.45, "y": 0.40},
            "right_iris": {"x": 0.55, "y": 0.40},
        }

        ws.send_json({"type": ClientMessageType.VISUAL_FRAME, "frame": frame})

        update_msg = ws.receive_json()
        assert update_msg["type"] == ServerMessageType.METRICS_UPDATE
        assert update_msg["update"]["face_detected"] is True
        assert update_msg["update"]["centered_gaze_ratio"] == 1.0


def test_websocket_off_center_gaze_alert(client):
    """Verify gaze shifting away for extended duration triggers caution alert."""
    with client.websocket_connect("/api/v1/ws/practice") as ws:
        ws.receive_json()  # ready

        # Initial frame at t=0
        ws.send_json(
            {
                "type": ClientMessageType.VISUAL_FRAME,
                "frame": {
                    "timestamp": 0.0,
                    "nose_tip": {"x": 0.50, "y": 0.45},
                },
            }
        )
        ws.receive_json()  # metrics_update

        # Frame with shifted nose position at t=4.5s
        ws.send_json(
            {
                "type": ClientMessageType.VISUAL_FRAME,
                "frame": {
                    "timestamp": 4.5,
                    "nose_tip": {"x": 0.85, "y": 0.45},
                },
            }
        )
        update_msg = ws.receive_json()
        assert update_msg["type"] == ServerMessageType.METRICS_UPDATE

        alert_msg = ws.receive_json()
        assert alert_msg["type"] == ServerMessageType.ALERT
        assert alert_msg["alert"]["alert_type"] == "off_center_gaze"
        assert "gaze" in alert_msg["alert"]["message"].lower()


def test_websocket_missing_face_alert(client):
    """Verify camera framing loss for extended duration triggers warning alert."""
    with client.websocket_connect("/api/v1/ws/practice") as ws:
        ws.receive_json()  # ready

        # Initial frame at t=0 with face
        ws.send_json(
            {
                "type": ClientMessageType.VISUAL_FRAME,
                "frame": {"timestamp": 0.0, "nose_tip": {"x": 0.50, "y": 0.45}},
            }
        )
        ws.receive_json()

        # Missing face at t=3.0s
        ws.send_json(
            {
                "type": ClientMessageType.VISUAL_FRAME,
                "frame": {"timestamp": 3.0, "nose_tip": None},
            }
        )
        update_msg = ws.receive_json()
        assert update_msg["type"] == ServerMessageType.METRICS_UPDATE
        assert update_msg["update"]["face_detected"] is False

        alert_msg = ws.receive_json()
        assert alert_msg["type"] == ServerMessageType.ALERT
        assert alert_msg["alert"]["alert_type"] == "face_missing"


def test_websocket_extended_pause_alert(client):
    """Verify silence check triggers extended pause alert."""
    with client.websocket_connect("/api/v1/ws/practice") as ws:
        ws.receive_json()  # ready

        ws.send_json(
            {
                "type": "silence_check",
                "elapsed_seconds": 3.8,
            }
        )
        alert_msg = ws.receive_json()
        assert alert_msg["type"] == ServerMessageType.ALERT
        assert alert_msg["alert"]["alert_type"] == "extended_pause"
        assert "pause in progress" in alert_msg["alert"]["message"].lower()


def test_websocket_audio_chunk_and_final_report(client):
    """Verify sending audio chunks and stopping stream returns consolidated final report."""
    with client.websocket_connect("/api/v1/ws/practice") as ws:
        ws.receive_json()  # ready

        # Send audio chunk
        dummy_audio = b"\x00" * 2000
        b64_audio = base64.b64encode(dummy_audio).decode("ascii")
        ws.send_json(
            {
                "type": ClientMessageType.AUDIO_CHUNK,
                "data": b64_audio,
                "elapsed_seconds": 1.0,
            }
        )

        # Send stop
        ws.send_json({"type": ClientMessageType.STOP})

        report_msg = ws.receive_json()
        assert report_msg["type"] == ServerMessageType.FINAL_REPORT
        assert "session_id" in report_msg["report"]
        assert report_msg["report"]["total_duration_seconds"] > 0


def test_websocket_ping_pong_heartbeat(client):
    """Verify WebSocket ping receives pong heartbeat."""
    with client.websocket_connect("/api/v1/ws/practice") as ws:
        ws.receive_json()  # ready

        ws.send_json({"type": ClientMessageType.PING})
        pong_msg = ws.receive_json()
        assert pong_msg["type"] == ServerMessageType.PONG


def test_websocket_error_handling_malformed_and_unknown(client):
    """Verify malformed JSON or unknown message types receive error responses cleanly."""
    with client.websocket_connect("/api/v1/ws/practice") as ws:
        ws.receive_json()  # ready

        # Send malformed string
        ws.send_text("not a valid json")
        err1 = ws.receive_json()
        assert err1["type"] == ServerMessageType.ERROR
        assert "malformed" in err1["message"].lower()

        # Send unknown type
        ws.send_json({"type": "unknown_action_type"})
        err2 = ws.receive_json()
        assert err2["type"] == ServerMessageType.ERROR
        assert "unrecognized" in err2["message"].lower()


def test_websocket_graceful_disconnect(client):
    """Verify client closing connection unexpectedly does not raise unhandled exception."""
    with client.websocket_connect("/api/v1/ws/practice") as ws:
        ws.receive_json()  # ready
        # Immediately exit context manager (disconnects)
