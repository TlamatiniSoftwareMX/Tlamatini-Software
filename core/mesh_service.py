from __future__ import annotations

import importlib
import os
import threading
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

from core.chat_mesh import (
    cargar_chat_mesh,
    construir_paquete_mesh,
    listar_conversations,
    listar_peers,
    registrar_mensaje,
    registrar_peer,
    actualizar_estado_mensaje,
    guardar_chat_mesh,
)


def _ahora_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class MeshDeviceCandidate:
    device_id: str
    label: str
    transport: str
    path: str
    hardware_hint: str = ""
    origin: str = "scan"
    status: str = "detected"
    last_seen: str = field(default_factory=_ahora_iso)

    def to_dict(self) -> Dict[str, str]:
        return {
            "device_id": self.device_id,
            "label": self.label,
            "transport": self.transport,
            "path": self.path,
            "hardware_hint": self.hardware_hint,
            "origin": self.origin,
            "status": self.status,
            "last_seen": self.last_seen,
        }


class MeshEventBus:
    def __init__(self) -> None:
        self._listeners: List[Callable[[Dict], None]] = []
        self._lock = threading.RLock()

    def subscribe(self, listener: Callable[[Dict], None]) -> Callable[[], None]:
        with self._lock:
            self._listeners.append(listener)

        def _unsubscribe() -> None:
            with self._lock:
                if listener in self._listeners:
                    self._listeners.remove(listener)

        return _unsubscribe

    def emit(self, event_type: str, payload: Optional[Dict] = None) -> None:
        event = {
            "type": event_type,
            "timestamp": _ahora_iso(),
            "payload": deepcopy(payload or {}),
        }
        with self._lock:
            listeners = list(self._listeners)
        for listener in listeners:
            try:
                listener(event)
            except Exception:
                continue


class MeshTransportAdapter:
    adapter_id = "abstract"

    def availability(self) -> Dict[str, str]:
        return {"available": False, "reason": "Adapter no implementado."}

    def connect(self, candidate: MeshDeviceCandidate) -> Dict:
        raise NotImplementedError

    def disconnect(self) -> None:
        return None

    def send_text(self, peer_id: str, body: str, requires_ack: bool = True) -> Dict:
        raise NotImplementedError


class MeshtasticPythonAdapter(MeshTransportAdapter):
    adapter_id = "meshtastic-python"

    def __init__(self) -> None:
        self.module = None
        self.connected_device: Optional[MeshDeviceCandidate] = None
        self._load_error = ""
        try:
            self.module = importlib.import_module("meshtastic")
        except Exception as exc:
            self._load_error = str(exc)

    def availability(self) -> Dict[str, str]:
        if self.module is None:
            return {
                "available": False,
                "reason": "Dependencia Meshtastic no instalada.",
                "detail": self._load_error,
            }
        return {
            "available": False,
            "reason": "Adaptador reservado para una implementación futura dentro de TLAMATINI.",
        }


class NullMeshAdapter(MeshTransportAdapter):
    adapter_id = "monitor-only"

    def __init__(self, reason: str = "Sin backend Meshtastic integrado.") -> None:
        self.reason = reason
        self.connected_device: Optional[MeshDeviceCandidate] = None

    def availability(self) -> Dict[str, str]:
        return {"available": True, "reason": self.reason}

    def connect(self, candidate: MeshDeviceCandidate) -> Dict:
        self.connected_device = candidate
        return {
            "connected": True,
            "mode": "monitor-only",
            "reason": self.reason,
            "device": candidate.to_dict(),
        }

    def disconnect(self) -> None:
        self.connected_device = None

    def send_text(self, peer_id: str, body: str, requires_ack: bool = True) -> Dict:
        packet = construir_paquete_mesh(peer_id, body, requires_ack=requires_ack)
        return {
            "sent": False,
            "mode": "monitor-only",
            "reason": self.reason,
            "packet": packet,
        }


class MeshDeviceScanner:
    USB_PATTERNS = (
        "/dev/ttyUSB*",
        "/dev/ttyACM*",
        "/dev/cu.usbmodem*",
        "/dev/cu.usbserial*",
        "/dev/serial/by-id/*",
    )
    BT_PATTERNS = (
        "/dev/rfcomm*",
        "/dev/cu.Bluetooth*",
        "/dev/tty.Bluetooth*",
    )

    def scan(self) -> List[MeshDeviceCandidate]:
        results: List[MeshDeviceCandidate] = []
        results.extend(self._scan_patterns(self.USB_PATTERNS, "usb"))
        results.extend(self._scan_patterns(self.BT_PATTERNS, "bluetooth"))

        env_device = os.environ.get("TLAMATINI_MESH_DEVICE", "").strip()
        if env_device:
            results.append(
                MeshDeviceCandidate(
                    device_id=f"env:{env_device}",
                    label=f"Configurado manualmente · {Path(env_device).name or env_device}",
                    transport="usb" if "tty" in env_device.lower() or "com" in env_device.lower() else "bluetooth",
                    path=env_device,
                    origin="env",
                    status="preferred",
                )
            )
        unique: Dict[str, MeshDeviceCandidate] = {}
        for item in results:
            unique[item.path] = item
        return sorted(unique.values(), key=lambda item: (item.transport, item.path))

    def _scan_patterns(self, patterns: tuple[str, ...], transport: str) -> List[MeshDeviceCandidate]:
        matches: List[MeshDeviceCandidate] = []
        for pattern in patterns:
            for path in sorted(Path("/").glob(pattern.lstrip("/"))):
                if not path.exists():
                    continue
                hardware_hint = self._infer_hardware_hint(path.name)
                matches.append(
                    MeshDeviceCandidate(
                        device_id=f"{transport}:{path}",
                        label=f"{transport.upper()} · {path.name}",
                        transport=transport,
                        path=str(path),
                        hardware_hint=hardware_hint,
                    )
                )
        return matches

    @staticmethod
    def _infer_hardware_hint(name: str) -> str:
        lowered = name.lower()
        if "t114" in lowered:
            return "t114"
        if "esp32" in lowered:
            return "esp32"
        return ""


class MeshSessionService:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._bus = MeshEventBus()
        self._scanner = MeshDeviceScanner()
        self._adapter: MeshTransportAdapter = self._build_adapter()
        self._device: Optional[MeshDeviceCandidate] = None
        self._status = self._base_status()
        self._persist_runtime()

    def subscribe(self, listener: Callable[[Dict], None]) -> Callable[[], None]:
        return self._bus.subscribe(listener)

    def get_snapshot(self) -> Dict:
        with self._lock:
            return {
                "status": deepcopy(self._status),
                "devices": [item.to_dict() for item in self._scanner.scan()],
                "peers": listar_peers(),
                "conversations": listar_conversations(),
            }

    def refresh_devices(self, auto_connect: bool = True) -> Dict:
        with self._lock:
            devices = self._scanner.scan()
            self._status["devices"] = [item.to_dict() for item in devices]
            self._status["last_scan_at"] = _ahora_iso()
            if auto_connect and devices and not self._status.get("connected"):
                self._connect_locked(devices[0])
            elif not devices:
                self._status["detected_device"] = None
                if self._status.get("connected"):
                    self._disconnect_locked("Dispositivo removido o no detectable.")
            self._persist_runtime()
            snapshot = self.get_snapshot()
        self._bus.emit("devices_refreshed", snapshot["status"])
        return snapshot

    def connect_preferred_device(self) -> Dict:
        with self._lock:
            devices = self._scanner.scan()
            if not devices:
                self._status["connected"] = False
                self._status["connection_state"] = "idle"
                self._status["status_text"] = "Sin dispositivo Meshtastic detectable."
                self._persist_runtime()
                return self.get_snapshot()
            self._connect_locked(devices[0])
            snapshot = self.get_snapshot()
        self._bus.emit("session_changed", snapshot["status"])
        return snapshot

    def send_message(self, peer_id: str, body: str, requires_ack: bool = True) -> Dict:
        with self._lock:
            record = registrar_mensaje(peer_id, body, direction="outbound", requires_ack=requires_ack)
            result = self._adapter.send_text(peer_id, body, requires_ack=requires_ack)
            if result.get("sent"):
                actualizar_estado_mensaje(peer_id, record["message_id"], "sent")
            else:
                actualizar_estado_mensaje(peer_id, record["message_id"], "queued")
            payload = {
                "peer_id": peer_id,
                "message_id": record["message_id"],
                "transport_result": deepcopy(result),
            }
            snapshot = self.get_snapshot()
        self._bus.emit("message_sent", payload)
        return {"record": record, "transport": result, "snapshot": snapshot}

    def register_inbound_message(self, peer_id: str, body: str, hardware_hint: str = "") -> Dict:
        with self._lock:
            peer = next((item for item in listar_peers() if item.get("node_id") == peer_id), None)
            if peer is None:
                registrar_peer(peer_id, display_name=peer_id, hardware=hardware_hint or "esp32", origin="auto_discovered")
            record = registrar_mensaje(peer_id, body, direction="inbound", hardware_hint=hardware_hint, requires_ack=False)
            snapshot = self.get_snapshot()
        self._bus.emit("message_received", {"peer_id": peer_id, "message_id": record["message_id"]})
        return {"record": record, "snapshot": snapshot}

    def _build_adapter(self) -> MeshTransportAdapter:
        candidate = MeshtasticPythonAdapter()
        availability = candidate.availability()
        if availability.get("available"):
            return candidate
        return NullMeshAdapter(reason=availability.get("reason", "Sin backend Meshtastic integrado."))

    def _base_status(self) -> Dict:
        availability = self._adapter.availability()
        return {
            "adapter_id": getattr(self._adapter, "adapter_id", "unknown"),
            "adapter_reason": availability.get("reason", ""),
            "connection_state": "idle",
            "connected": False,
            "status_text": "Esperando una placa Meshtastic por USB o Bluetooth.",
            "detected_device": None,
            "last_scan_at": "",
            "devices": [],
        }

    def _connect_locked(self, candidate: MeshDeviceCandidate) -> None:
        result = self._adapter.connect(candidate)
        self._device = candidate
        self._status["connected"] = bool(result.get("connected"))
        self._status["connection_state"] = "monitoring" if result.get("connected") else "error"
        self._status["status_text"] = result.get("reason") or f"Conectado a {candidate.label}"
        self._status["detected_device"] = candidate.to_dict()
        self._persist_runtime()

    def _disconnect_locked(self, reason: str) -> None:
        self._adapter.disconnect()
        self._device = None
        self._status["connected"] = False
        self._status["connection_state"] = "idle"
        self._status["status_text"] = reason
        self._status["detected_device"] = None
        self._persist_runtime()

    def _persist_runtime(self) -> None:
        data = cargar_chat_mesh()
        data["runtime"] = deepcopy(self._status)
        guardar_chat_mesh(data)


_SERVICE: Optional[MeshSessionService] = None
_SERVICE_LOCK = threading.RLock()


def get_mesh_session_service() -> MeshSessionService:
    global _SERVICE
    with _SERVICE_LOCK:
        if _SERVICE is None:
            _SERVICE = MeshSessionService()
        return _SERVICE
