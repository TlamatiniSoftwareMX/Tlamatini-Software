import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from core.memoria import DATA_DIR


RUTA_CHAT_MESH = DATA_DIR / "memoria" / "chat_mesh.json"


ESTRUCTURA_CHAT_BASE = {
    "schema_version": "1.0",
    "protocol_id": "tlamatini.mesh.chat.v1",
    "settings": {
        "ack_default": True,
        "max_payload_bytes": 512,
        "encoding": "utf-8",
    },
    "local_node": {
        "node_id": "tlamatini.local",
        "display_name": "TLAMATINI",
        "hardware": "t114",
        "transport": "mesh",
        "mesh_role": "bridge",
    },
    "runtime": {
        "adapter_id": "monitor-only",
        "adapter_reason": "Sin backend Meshtastic integrado.",
        "connection_state": "idle",
        "connected": False,
        "status_text": "Esperando una placa Meshtastic por USB o Bluetooth.",
        "detected_device": None,
        "last_scan_at": "",
        "devices": [],
    },
    "peers": [],
    "conversations": [],
}


def _ahora_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _asegurar_archivo() -> None:
    RUTA_CHAT_MESH.parent.mkdir(parents=True, exist_ok=True)
    if not RUTA_CHAT_MESH.exists():
        RUTA_CHAT_MESH.write_text(json.dumps(ESTRUCTURA_CHAT_BASE, indent=4, ensure_ascii=False), encoding="utf-8")


def _ordenar_peers(peers: List[Dict]) -> List[Dict]:
    return sorted(peers, key=lambda item: ((item.get("display_name") or item.get("node_id") or "").lower(), item.get("node_id", "")))


def _normalizar_peer(peer: Dict) -> Dict:
    return {
        "node_id": str(peer.get("node_id", "")).strip(),
        "display_name": str(peer.get("display_name", "")).strip() or str(peer.get("node_id", "")).strip(),
        "hardware": str(peer.get("hardware", "esp32")).strip().lower() or "esp32",
        "transport": str(peer.get("transport", "mesh")).strip().lower() or "mesh",
        "mesh_role": str(peer.get("mesh_role", "node")).strip().lower() or "node",
        "origin": str(peer.get("origin", "manual")).strip().lower() or "manual",
        "notes": str(peer.get("notes", "")).strip(),
        "updated_at": peer.get("updated_at") or _ahora_iso(),
    }


def _normalizar_message(message: Dict, local_node_id: str, peer_id: str) -> Dict:
    body = str(message.get("body", "")).strip()
    direction = str(message.get("direction", "outbound")).strip().lower() or "outbound"
    source = str(message.get("source_node", local_node_id if direction == "outbound" else peer_id)).strip()
    destination = str(message.get("destination_node", peer_id if direction == "outbound" else local_node_id)).strip()
    return {
        "message_id": str(message.get("message_id") or f"MSG-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"),
        "timestamp": message.get("timestamp") or _ahora_iso(),
        "direction": direction,
        "status": str(message.get("status", "draft" if direction == "outbound" else "received")).strip().lower(),
        "source_node": source,
        "destination_node": destination,
        "body": body,
        "transport": str(message.get("transport", "mesh")).strip().lower() or "mesh",
        "hardware_hint": str(message.get("hardware_hint", "")).strip().lower(),
        "requires_ack": bool(message.get("requires_ack", True)),
        "payload_type": "text/plain",
    }


def _normalizar_conversation(conversation: Dict, local_node_id: str) -> Dict:
    peer_id = str(conversation.get("peer_id", "")).strip()
    messages = [
        _normalizar_message(message, local_node_id, peer_id)
        for message in list(conversation.get("messages", []) or [])
        if isinstance(message, dict)
    ]
    return {
        "peer_id": peer_id,
        "display_name": str(conversation.get("display_name", "")).strip() or peer_id,
        "messages": messages,
        "updated_at": conversation.get("updated_at") or (messages[-1]["timestamp"] if messages else _ahora_iso()),
    }


def _normalizar_data(data: Dict) -> Dict:
    base = deepcopy(ESTRUCTURA_CHAT_BASE)
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                base[key].update(value)
            else:
                base[key] = value

    local_node = base.get("local_node", {}) or {}
    base["local_node"] = {
        "node_id": str(local_node.get("node_id", "tlamatini.local")).strip() or "tlamatini.local",
        "display_name": str(local_node.get("display_name", "TLAMATINI")).strip() or "TLAMATINI",
        "hardware": str(local_node.get("hardware", "t114")).strip().lower() or "t114",
        "transport": str(local_node.get("transport", "mesh")).strip().lower() or "mesh",
        "mesh_role": str(local_node.get("mesh_role", "bridge")).strip().lower() or "bridge",
    }
    runtime = base.get("runtime", {}) or {}
    base["runtime"] = {
        "adapter_id": str(runtime.get("adapter_id", "monitor-only")).strip() or "monitor-only",
        "adapter_reason": str(runtime.get("adapter_reason", "Sin backend Meshtastic integrado.")).strip(),
        "connection_state": str(runtime.get("connection_state", "idle")).strip().lower() or "idle",
        "connected": bool(runtime.get("connected", False)),
        "status_text": str(runtime.get("status_text", "Esperando una placa Meshtastic por USB o Bluetooth.")).strip(),
        "detected_device": runtime.get("detected_device"),
        "last_scan_at": str(runtime.get("last_scan_at", "")).strip(),
        "devices": list(runtime.get("devices", []) or []),
    }
    base["peers"] = _ordenar_peers([_normalizar_peer(peer) for peer in list(base.get("peers", []) or []) if isinstance(peer, dict) and str(peer.get("node_id", "")).strip()])
    base["conversations"] = [
        _normalizar_conversation(conversation, base["local_node"]["node_id"])
        for conversation in list(base.get("conversations", []) or [])
        if isinstance(conversation, dict) and str(conversation.get("peer_id", "")).strip()
    ]
    return base


def cargar_chat_mesh() -> Dict:
    _asegurar_archivo()
    try:
        data = json.loads(RUTA_CHAT_MESH.read_text(encoding="utf-8"))
    except Exception:
        data = deepcopy(ESTRUCTURA_CHAT_BASE)
    normalizado = _normalizar_data(data)
    guardar_chat_mesh(normalizado)
    return normalizado


def guardar_chat_mesh(data: Dict) -> Dict:
    _asegurar_archivo()
    normalizado = _normalizar_data(data)
    RUTA_CHAT_MESH.write_text(json.dumps(normalizado, indent=4, ensure_ascii=False), encoding="utf-8")
    return normalizado


def registrar_peer(node_id: str, display_name: str = "", hardware: str = "esp32", transport: str = "mesh", mesh_role: str = "node", origin: str = "manual", notes: str = "") -> Dict:
    data = cargar_chat_mesh()
    node_id = str(node_id or "").strip()
    if not node_id:
        raise ValueError("El node_id es obligatorio.")
    peers = [peer for peer in data["peers"] if peer.get("node_id") != node_id]
    peers.append(
        _normalizar_peer(
            {
                "node_id": node_id,
                "display_name": display_name,
                "hardware": hardware,
                "transport": transport,
                "mesh_role": mesh_role,
                "origin": origin,
                "notes": notes,
                "updated_at": _ahora_iso(),
            }
        )
    )
    data["peers"] = _ordenar_peers(peers)
    guardar_chat_mesh(data)
    return next(peer for peer in data["peers"] if peer["node_id"] == node_id)


def listar_peers() -> List[Dict]:
    return deepcopy(cargar_chat_mesh().get("peers", []))


def listar_conversations() -> List[Dict]:
    conversaciones = deepcopy(cargar_chat_mesh().get("conversations", []))
    conversaciones.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
    return conversaciones


def _upsert_conversation(data: Dict, peer_id: str, display_name: str = "") -> Dict:
    for conversation in data["conversations"]:
        if conversation.get("peer_id") == peer_id:
            if display_name:
                conversation["display_name"] = display_name
            return conversation
    conversation = _normalizar_conversation({"peer_id": peer_id, "display_name": display_name, "messages": [], "updated_at": _ahora_iso()}, data["local_node"]["node_id"])
    data["conversations"].append(conversation)
    return conversation


def registrar_mensaje(peer_id: str, body: str, direction: str = "outbound", hardware_hint: str = "", requires_ack: bool = True) -> Dict:
    data = cargar_chat_mesh()
    peer_id = str(peer_id or "").strip()
    body = str(body or "").strip()
    if not peer_id:
        raise ValueError("Selecciona un nodo destino.")
    if not body:
        raise ValueError("Escribe un mensaje.")

    peer = next((item for item in data["peers"] if item.get("node_id") == peer_id), None)
    display_name = peer.get("display_name", peer_id) if peer else peer_id
    conversation = _upsert_conversation(data, peer_id, display_name)
    message = _normalizar_message(
        {
            "body": body,
            "direction": direction,
            "status": "queued" if direction == "outbound" else "received",
            "transport": (peer or {}).get("transport", "mesh"),
            "hardware_hint": hardware_hint or (peer or {}).get("hardware", ""),
            "requires_ack": requires_ack,
        },
        data["local_node"]["node_id"],
        peer_id,
    )
    conversation["messages"].append(message)
    conversation["updated_at"] = message["timestamp"]
    guardar_chat_mesh(data)
    return message


def actualizar_estado_mensaje(peer_id: str, message_id: str, status: str) -> Dict:
    data = cargar_chat_mesh()
    peer_id = str(peer_id or "").strip()
    message_id = str(message_id or "").strip()
    status = str(status or "").strip().lower()
    if not peer_id or not message_id or not status:
        raise ValueError("peer_id, message_id y status son obligatorios.")

    for conversation in data.get("conversations", []):
        if conversation.get("peer_id") != peer_id:
            continue
        for message in conversation.get("messages", []):
            if message.get("message_id") == message_id:
                message["status"] = status
                guardar_chat_mesh(data)
                return deepcopy(message)
    raise ValueError("No se encontró el mensaje a actualizar.")


def construir_paquete_mesh(peer_id: str, body: str, requires_ack: bool = True) -> Dict:
    data = cargar_chat_mesh()
    peer = next((item for item in data["peers"] if item.get("node_id") == peer_id), None)
    local_node = data["local_node"]
    return {
        "protocol": data["protocol_id"],
        "schema_version": data["schema_version"],
        "message": {
            "message_id": f"MSG-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            "timestamp": _ahora_iso(),
            "source_node": local_node["node_id"],
            "destination_node": peer_id,
            "source_hardware": local_node.get("hardware", "t114"),
            "destination_hardware": (peer or {}).get("hardware", ""),
            "transport": (peer or {}).get("transport", "mesh"),
            "mesh_role_source": local_node.get("mesh_role", "bridge"),
            "mesh_role_destination": (peer or {}).get("mesh_role", "node"),
            "payload_type": "text/plain",
            "encoding": data.get("settings", {}).get("encoding", "utf-8"),
            "requires_ack": bool(requires_ack),
            "body": str(body or "").strip(),
        },
    }
