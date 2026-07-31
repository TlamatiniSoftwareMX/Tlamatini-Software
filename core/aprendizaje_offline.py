from __future__ import annotations

import html
import json
import os
import re
import shutil
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable, Dict, List, Optional

from core.logs import registrar_log
from core.memoria import APP_DIR
from core.path_manager import offline_learning_dir
from core.texto import normalizar_texto


CATALOG_ASSET_PATH = APP_DIR / "assets" / "offline_learning" / "catalog.json"
PRACTICAL_GUIDES_ASSET_PATH = APP_DIR / "assets" / "offline_learning" / "practical_guides.json"
LOCAL_LEARNING_DIR = offline_learning_dir()
CATALOG_DIR = LOCAL_LEARNING_DIR / "catalog"
COURSES_DIR = LOCAL_LEARNING_DIR / "courses"
TEMP_DIR = LOCAL_LEARNING_DIR / "temp"
METADATA_DIR = LOCAL_LEARNING_DIR / "metadata"
PROGRESS_DIR = LOCAL_LEARNING_DIR / "progress"
CACHE_DIR = LOCAL_LEARNING_DIR / "cache"
FAVORITES_DIR = LOCAL_LEARNING_DIR / "favorites"
STATE_PATH = METADATA_DIR / "learning_state.json"
CATALOG_CACHE_PATH = CATALOG_DIR / "resolved_catalog.json"

ProgressCallback = Callable[[Dict[str, object]], None]
_STATE_LOCK = threading.RLock()


DEFAULT_STATE = {
    "installed": {},
    "downloads": {},
    "favorites": [],
    "last_course": "",
    "last_lesson": "",
    "progress": {},
}


class DownloadCancelledError(RuntimeError):
    pass


class _TextExtractor(HTMLParser):
    BLOCK_TAGS = {
        "p",
        "div",
        "section",
        "article",
        "header",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "ul",
        "ol",
        "li",
        "table",
        "tr",
        "td",
        "th",
        "blockquote",
        "pre",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: List[str] = []
        self.skip_depth = 0
        self._li_open = False

    def handle_starttag(self, tag, attrs):
        attrs_map = dict(attrs)
        if tag in {"script", "style", "sup"}:
            classes = attrs_map.get("class", "") or ""
            if tag != "sup" or "reference" in classes:
                self.skip_depth += 1
                return
        if self.skip_depth:
            return
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")
        if tag == "li":
            self.parts.append("- ")
            self._li_open = True

    def handle_endtag(self, tag):
        if self.skip_depth:
            if tag in {"script", "style", "sup"}:
                self.skip_depth = max(0, self.skip_depth - 1)
            return
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")
        if tag == "li" and self._li_open:
            self.parts.append("\n")
            self._li_open = False

    def handle_data(self, data):
        if self.skip_depth:
            return
        text = data.strip()
        if text:
            self.parts.append(text)
            self.parts.append(" ")

    def get_text(self) -> str:
        text = "".join(self.parts)
        text = html.unescape(text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n[ \t]+", "\n", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        return text.strip()


def _clean_extracted_text(text: str) -> str:
    text = text.replace("[ editar ]", " ")
    text = text.replace("[ editar código ]", " ")
    text = re.sub(r"\[\s*\d+\s*\]", " ", text)
    text = re.sub(r"\b(Ocultar|Mostrar)\b", " ", text)
    text = re.sub(r"(Coordenadas|Véase también|Enlaces externos|Referencias)\s*\n", r"\1\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def _default_state() -> Dict:
    return json.loads(json.dumps(DEFAULT_STATE))


def _ensure_dirs() -> None:
    for ruta in (
        LOCAL_LEARNING_DIR,
        CATALOG_DIR,
        COURSES_DIR,
        TEMP_DIR,
        METADATA_DIR,
        PROGRESS_DIR,
        CACHE_DIR,
        FAVORITES_DIR,
    ):
        ruta.mkdir(parents=True, exist_ok=True)


def _atomic_write_json(ruta: Path, payload: Dict) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=str(ruta.parent)) as tmp:
        json.dump(payload, tmp, indent=2, ensure_ascii=False)
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, ruta)


def _load_json(ruta: Path, default):
    try:
        if not ruta.exists():
            return default
        with open(ruta, "r", encoding="utf-8") as archivo:
            return json.load(archivo)
    except Exception:
        return default


def _now_label() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def load_state() -> Dict:
    _ensure_dirs()
    with _STATE_LOCK:
        state = _load_json(STATE_PATH, _default_state())
        for clave, valor in DEFAULT_STATE.items():
            if clave not in state:
                state[clave] = json.loads(json.dumps(valor))
        return state


def save_state(state: Dict) -> Dict:
    _ensure_dirs()
    with _STATE_LOCK:
        _atomic_write_json(STATE_PATH, state)
    return state


def _course_dir(course_id: str) -> Path:
    return COURSES_DIR / course_id


def _temp_dir(course_id: str) -> Path:
    return TEMP_DIR / f"{course_id}.part"


def _lesson_path(course_id: str, lesson_id: str, *, temp: bool = False) -> Path:
    base = _temp_dir(course_id) if temp else _course_dir(course_id)
    return base / "lessons" / f"{lesson_id}.json"


def _manifest_path(course_id: str, *, temp: bool = False) -> Path:
    base = _temp_dir(course_id) if temp else _course_dir(course_id)
    return base / "course.json"


def _merge_status(entry: Dict, state: Dict) -> Dict:
    item = dict(entry)
    course_id = item.get("id", "")
    installed = state.get("installed", {}).get(course_id, {})
    download = state.get("downloads", {}).get(course_id, {})
    progress = state.get("progress", {}).get(course_id, {})
    favorites = set(state.get("favorites", []))

    status = "no_descargado"
    if download.get("status"):
        status = str(download.get("status"))
    elif installed and Path(installed.get("path", "")).exists():
        status = str(installed.get("status", "listo"))

    item["status"] = status
    item["favorite"] = course_id in favorites
    item["installed_path"] = installed.get("path", "")
    item["download_progress"] = float(download.get("progress", 0.0) or 0.0)
    item["download_error"] = download.get("error", "")
    item["download_phase"] = download.get("phase", "")
    item["downloaded_lessons"] = int(download.get("downloaded_lessons", 0) or 0)
    item["total_lessons"] = int(download.get("total_lessons", 0) or installed.get("lesson_count", 0) or 0)
    item["downloaded_bytes"] = int(download.get("downloaded_bytes", 0) or 0)
    item["total_bytes"] = int(download.get("total_bytes", 0) or installed.get("size_bytes", 0) or 0)
    item["activity"] = download.get("activity", "")
    item["completed_lessons"] = len(progress.get("completed_lessons", []))
    item["progress_percent"] = float(progress.get("percent", 0.0) or 0.0)
    item["last_lesson"] = progress.get("last_lesson", "")
    item["installed_at"] = installed.get("installed_at", "")
    item["last_opened"] = progress.get("last_opened", "")
    return item


def _reconcile_state(state: Dict, entries: List[Dict]) -> Dict:
    by_id = {entry.get("id"): entry for entry in entries if entry.get("id")}
    changed = False

    for course_id, download in list(state.get("downloads", {}).items()):
        entry = by_id.get(course_id)
        if not entry:
            continue
        tmp = _temp_dir(course_id)
        final_dir = _course_dir(course_id)
        status = str(download.get("status", "") or "")
        if status in {"en_cola", "descargando", "instalando", "verificando"} and not tmp.exists() and not final_dir.exists():
            download["status"] = "error"
            download["error"] = "La descarga anterior fue interrumpida."
            changed = True

    for course_id, installed in list(state.get("installed", {}).items()):
        if not Path(installed.get("path", "")).exists():
            installed["status"] = "error"
            changed = True
        elif installed.get("status") in {"instalado", "", None}:
            installed["status"] = "listo"
            changed = True

    if changed:
        save_state(state)
    return state


def load_catalog() -> List[Dict]:
    _ensure_dirs()
    payload = _load_json(CATALOG_ASSET_PATH, {"entries": []})
    entries = payload.get("entries", []) if isinstance(payload, dict) else []
    practical_payload = _load_json(PRACTICAL_GUIDES_ASSET_PATH, {"entries": []})
    practical_entries = practical_payload.get("entries", []) if isinstance(practical_payload, dict) else []
    # Las guías incluidas viven en un archivo separado para poder ampliarlas sin
    # convertir el catálogo de descargas remotas en un archivo inmanejable.
    entries = [*entries, *practical_entries]
    state = _reconcile_state(load_state(), entries)
    merged = [_merge_status(entry, state) for entry in entries if isinstance(entry, dict) and entry.get("id")]
    _atomic_write_json(CATALOG_CACHE_PATH, {"generated_at": _now_label(), "entries": merged})
    return merged


def get_course_entry(course_id: str) -> Optional[Dict]:
    for entry in load_catalog():
        if entry.get("id") == course_id:
            return entry
    return None


def _searchable_text(entry: Dict) -> str:
    return " ".join(
        [
            str(entry.get("id", "")),
            str(entry.get("name", "")),
            str(entry.get("language", "")),
            str(entry.get("category", "")),
            str(entry.get("level", "")),
            str(entry.get("description", "")),
            str(entry.get("content_type", "")),
            " ".join(str(tag) for tag in entry.get("tags", []) or []),
        ]
    )


def search_catalog(query: str = "") -> List[Dict]:
    entries = load_catalog()
    query_n = normalizar_texto(query or "")
    if not query_n:
        return entries
    return [entry for entry in entries if query_n in normalizar_texto(_searchable_text(entry))]


def list_installed(query: str = "") -> List[Dict]:
    state = load_state()
    catalog_by_id = {entry["id"]: entry for entry in load_catalog()}
    items = []
    for course_id, installed in state.get("installed", {}).items():
        path = Path(installed.get("path", ""))
        if not path.exists():
            continue
        entry = dict(catalog_by_id.get(course_id, {}))
        entry.update(installed)
        entry["id"] = course_id
        progress = state.get("progress", {}).get(course_id, {})
        entry["status"] = str(installed.get("status", "listo"))
        entry["favorite"] = course_id in set(state.get("favorites", []))
        entry["progress_percent"] = float(progress.get("percent", 0.0) or 0.0)
        entry["completed_lessons"] = len(progress.get("completed_lessons", []))
        entry["last_lesson"] = progress.get("last_lesson", "")
        entry["last_opened"] = progress.get("last_opened", "")
        items.append(entry)
    query_n = normalizar_texto(query or "")
    if not query_n:
        return sorted(items, key=lambda item: (not item.get("favorite", False), str(item.get("name", ""))))
    return [item for item in items if query_n in normalizar_texto(_searchable_text(item))]


def set_favorite(course_id: str, favorito: bool) -> Dict:
    state = load_state()
    favorites = set(state.get("favorites", []))
    if favorito:
        favorites.add(course_id)
    else:
        favorites.discard(course_id)
    state["favorites"] = sorted(favorites)
    save_state(state)
    return {"ok": True, "favorites": state["favorites"]}


def _update_download_state(course_id: str, **payload) -> None:
    state = load_state()
    state.setdefault("downloads", {}).setdefault(course_id, {})
    state["downloads"][course_id].update(payload)
    save_state(state)


def _course_lessons(course_entry: Dict) -> List[Dict]:
    lessons: List[Dict] = []
    for module in course_entry.get("modules", []) or []:
        for lesson in module.get("lessons", []) or []:
            lesson_copy = dict(lesson)
            lesson_copy["module_id"] = module.get("id", "")
            lesson_copy["module_title"] = module.get("title", "")
            lessons.append(lesson_copy)
    return lessons


def _mediawiki_api_url(source_url: str) -> str:
    parsed = urllib.parse.urlparse(source_url)
    path = parsed.path or ""
    marker = "/wiki/"
    if marker not in path:
        raise ValueError(f"URL no compatible con MediaWiki: {source_url}")
    page_title = urllib.parse.unquote(path.split(marker, 1)[1])
    query = urllib.parse.urlencode(
        {
            "action": "parse",
            "page": page_title,
            "prop": "text|displaytitle|sections",
            "format": "json",
            "formatversion": 2,
            "redirects": 1,
            "disablelimitreport": 1,
            "disableeditsection": 1,
        }
    )
    return f"{parsed.scheme}://{parsed.netloc}/w/api.php?{query}"


def _http_get_json(url: str) -> Dict:
    req = urllib.request.Request(url, headers={"User-Agent": "TLAMATINI/6 Aprendizaje"})
    with urllib.request.urlopen(req, timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))


def _lesson_from_mediawiki(lesson: Dict) -> Dict:
    source_url = str(lesson.get("source_url", "") or "")
    api_url = _mediawiki_api_url(source_url)
    payload = _http_get_json(api_url)
    parse = payload.get("parse")
    if not parse:
        raise ValueError(f"Respuesta inválida al descargar la lección desde {source_url}")
    html_body = str(parse.get("text") or "")
    extractor = _TextExtractor()
    extractor.feed(html_body)
    text_body = _clean_extracted_text(extractor.get_text())
    sections = [
        {
            "index": section.get("index"),
            "line": section.get("line", ""),
            "level": section.get("level", ""),
        }
        for section in parse.get("sections", []) or []
        if isinstance(section, dict)
    ]
    return {
        "id": lesson.get("id", ""),
        "title": lesson.get("title") or parse.get("displaytitle") or lesson.get("id", ""),
        "module_id": lesson.get("module_id", ""),
        "module_title": lesson.get("module_title", ""),
        "source_url": source_url,
        "downloaded_at": _now_label(),
        "html": html_body,
        "text": text_body,
        "sections": sections,
        "word_count": len(text_body.split()),
    }


def _download_lesson(lesson: Dict) -> Dict:
    source_type = str(lesson.get("source_type", "mediawiki") or "mediawiki")
    if source_type == "mediawiki":
        return _lesson_from_mediawiki(lesson)
    if source_type == "embedded":
        text_body = str(lesson.get("text", "") or "").strip()
        if not text_body:
            raise ValueError("La lección incluida no tiene contenido.")
        return {
            "id": lesson.get("id", ""),
            "title": lesson.get("title", lesson.get("id", "")),
            "module_id": lesson.get("module_id", ""),
            "module_title": lesson.get("module_title", ""),
            "source_url": lesson.get("source_url", ""),
            "downloaded_at": _now_label(),
            "html": "",
            "text": text_body,
            "sections": lesson.get("sections", []) or [],
            "word_count": len(text_body.split()),
            "included_offline": True,
            "safety": lesson.get("safety", ""),
            "sources": lesson.get("sources", []) or [],
        }
    raise ValueError(f"Tipo de lección no soportado: {source_type}")


def download_course(
    course_id: str,
    progress_callback: Optional[ProgressCallback] = None,
    cancel_event: Optional[threading.Event] = None,
) -> Dict:
    entry = get_course_entry(course_id)
    if not entry:
        raise ValueError("Curso no encontrado en catálogo.")

    lessons = _course_lessons(entry)
    if not lessons:
        raise ValueError("El curso no tiene lecciones configuradas.")

    final_dir = _course_dir(course_id)
    if final_dir.exists():
        return verify_installed_course(course_id)

    temp_dir = _temp_dir(course_id)
    (temp_dir / "lessons").mkdir(parents=True, exist_ok=True)

    def report(status: str, progress: float, message: str, **extra):
        payload = {"status": status, "progress": max(0.0, min(100.0, progress)), "message": message, **extra}
        _update_download_state(course_id, **payload)
        if progress_callback:
            progress_callback({"course_id": course_id, **payload})

    def ensure_not_cancelled():
        if cancel_event and cancel_event.is_set():
            report(
                "cancelado",
                (downloaded_lessons / total_lessons) * 100.0 if total_lessons else 0.0,
                "Descarga cancelada por cierre de ventana.",
                phase="cancelado",
                downloaded_lessons=downloaded_lessons,
                total_lessons=total_lessons,
                downloaded_bytes=total_bytes,
                total_bytes=total_bytes,
                activity="La descarga se detuvo antes de finalizar.",
                error="cancelado_por_usuario",
            )
            raise DownloadCancelledError("La descarga fue cancelada por el usuario.")

    report("en_cola", 0.0, "Preparando descarga del curso.", phase="preparando")

    downloaded_lessons = 0
    total_lessons = len(lessons)
    total_bytes = 0
    ensure_not_cancelled()
    for index, lesson in enumerate(lessons, start=1):
        ensure_not_cancelled()
        lesson_path = _lesson_path(course_id, lesson["id"], temp=True)
        if lesson_path.exists():
            existing = _load_json(lesson_path, {})
            text = str(existing.get("text", "") or "")
            total_bytes += len(text.encode("utf-8"))
            downloaded_lessons += 1
            report(
                "descargando",
                (downloaded_lessons / total_lessons) * 100.0,
                f"Reanudando curso: {downloaded_lessons}/{total_lessons} lecciones listas.",
                phase="reanudando",
                lesson_id=lesson["id"],
                downloaded_lessons=downloaded_lessons,
                total_lessons=total_lessons,
                downloaded_bytes=total_bytes,
                activity="Verificando datos parciales",
            )
            continue

        try:
            lesson_payload = _download_lesson(lesson)
        except Exception as exc:
            report(
                "error",
                ((index - 1) / total_lessons) * 100.0,
                f"Error en {lesson.get('title', lesson.get('id', ''))}: {exc}",
                phase="error",
                error=str(exc),
                downloaded_lessons=downloaded_lessons,
                total_lessons=total_lessons,
                downloaded_bytes=total_bytes,
            )
            registrar_log("aprendizaje", f"Fallo al descargar {course_id}/{lesson.get('id')}: {exc}", "aprendizaje")
            raise

        lesson_path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write_json(lesson_path, lesson_payload)
        total_bytes += len(str(lesson_payload.get("text", "")).encode("utf-8"))
        downloaded_lessons += 1
        report(
            "descargando",
            (downloaded_lessons / total_lessons) * 100.0,
            f"Descargando lección {downloaded_lessons}/{total_lessons}: {lesson_payload.get('title', lesson['id'])}",
            phase="descargando",
            lesson_id=lesson["id"],
            downloaded_lessons=downloaded_lessons,
            total_lessons=total_lessons,
            downloaded_bytes=total_bytes,
            activity=f"Procesando {lesson_payload.get('word_count', 0)} palabras",
        )

    ensure_not_cancelled()
    report(
        "instalando",
        100.0,
        "Instalando curso.",
        phase="instalando",
        downloaded_lessons=downloaded_lessons,
        total_lessons=total_lessons,
        downloaded_bytes=total_bytes,
        total_bytes=total_bytes,
    )
    manifest = {
        "id": course_id,
        "name": entry.get("name", course_id),
        "language": entry.get("language", ""),
        "category": entry.get("category", ""),
        "level": entry.get("level", ""),
        "description": entry.get("description", ""),
        "format": entry.get("format", ""),
        "version": entry.get("version", ""),
        "source": entry.get("source", ""),
        "source_url": entry.get("source_url", ""),
        "modules": entry.get("modules", []),
        "lesson_count": total_lessons,
        "downloaded_at": _now_label(),
        "approx_text_bytes": total_bytes,
    }
    _atomic_write_json(_manifest_path(course_id, temp=True), manifest)
    final_dir.parent.mkdir(parents=True, exist_ok=True)
    if final_dir.exists():
        shutil.rmtree(final_dir)
    os.replace(temp_dir, final_dir)

    state = load_state()
    state.setdefault("installed", {})[course_id] = {
        "id": course_id,
        "name": entry.get("name", course_id),
        "path": str(final_dir),
        "status": "listo",
        "format": entry.get("format", ""),
        "installed_at": _now_label(),
        "lesson_count": total_lessons,
        "size_bytes": total_bytes,
    }
    state.setdefault("downloads", {}).pop(course_id, None)
    state.setdefault("progress", {}).setdefault(
        course_id,
        {
            "completed_lessons": [],
            "last_lesson": "",
            "percent": 0.0,
            "updated_at": "",
        },
    )
    save_state(state)
    registrar_log("aprendizaje", f"Curso instalado: {course_id}", "aprendizaje")
    return verify_installed_course(course_id)


def verify_installed_course(course_id: str) -> Dict:
    entry = get_course_entry(course_id)
    state = load_state()
    installed = state.get("installed", {}).get(course_id)
    if not entry or not installed:
        raise ValueError("Curso no instalado.")

    course_dir = Path(installed.get("path", ""))
    manifest = _load_json(_manifest_path(course_id), {})
    if not course_dir.exists() or not manifest:
        raise ValueError("El curso instalado no tiene manifiesto válido.")

    lessons = _course_lessons(entry)
    missing = [lesson["id"] for lesson in lessons if not _lesson_path(course_id, lesson["id"]).exists()]
    if missing:
        raise ValueError(f"Faltan lecciones descargadas: {', '.join(missing[:5])}")

    installed["status"] = "listo"
    installed["lesson_count"] = len(lessons)
    installed["verified_at"] = _now_label()
    save_state(state)
    registrar_log("aprendizaje", f"Curso verificado: {course_id}", "aprendizaje")
    return {
        "ok": True,
        "course_id": course_id,
        "lesson_count": len(lessons),
        "path": str(course_dir),
    }


def delete_course(course_id: str) -> Dict:
    course_dir = _course_dir(course_id)
    if course_dir.exists():
        shutil.rmtree(course_dir)
    temp_dir = _temp_dir(course_id)
    if temp_dir.exists():
        shutil.rmtree(temp_dir)

    state = load_state()
    state.get("installed", {}).pop(course_id, None)
    state.get("downloads", {}).pop(course_id, None)
    state.get("progress", {}).pop(course_id, None)
    state["favorites"] = [item for item in state.get("favorites", []) if item != course_id]
    if state.get("last_course") == course_id:
        state["last_course"] = ""
        state["last_lesson"] = ""
    save_state(state)
    registrar_log("aprendizaje", f"Curso eliminado: {course_id}", "aprendizaje")
    return {"ok": True}


def load_course(course_id: str) -> Dict:
    course_dir = _course_dir(course_id)
    manifest = _load_json(_manifest_path(course_id), {})
    if not course_dir.exists() or not manifest:
        raise ValueError("Curso no instalado o manifiesto no encontrado.")
    state = load_state()
    progress = state.get("progress", {}).get(course_id, {})
    manifest["progress"] = progress
    return manifest


def get_lesson(course_id: str, lesson_id: str) -> Dict:
    payload = _load_json(_lesson_path(course_id, lesson_id), {})
    if not payload:
        raise ValueError("Lección no encontrada.")
    return payload


def _lesson_count_for_course(manifest: Dict) -> int:
    count = 0
    for module in manifest.get("modules", []) or []:
        count += len(module.get("lessons", []) or [])
    return count


def update_progress(course_id: str, lesson_id: str, completed: Optional[bool] = None) -> Dict:
    manifest = load_course(course_id)
    state = load_state()
    progress = state.setdefault("progress", {}).setdefault(
        course_id,
        {
            "completed_lessons": [],
            "last_lesson": "",
            "percent": 0.0,
            "updated_at": "",
            "last_opened": "",
            "reading_positions": {},
        },
    )
    completed_lessons = set(progress.get("completed_lessons", []))
    if completed is True:
        completed_lessons.add(lesson_id)
    elif completed is False:
        completed_lessons.discard(lesson_id)
    progress["completed_lessons"] = sorted(completed_lessons)
    progress["last_lesson"] = lesson_id
    progress["last_opened"] = _now_label()
    total_lessons = max(1, _lesson_count_for_course(manifest))
    progress["percent"] = round((len(completed_lessons) / total_lessons) * 100.0, 1)
    progress["updated_at"] = _now_label()
    state["last_course"] = course_id
    state["last_lesson"] = lesson_id
    save_state(state)
    registrar_log("aprendizaje", f"Progreso actualizado: {course_id}/{lesson_id} ({progress['percent']}%)", "aprendizaje")
    return {
        "ok": True,
        "course_id": course_id,
        "lesson_id": lesson_id,
        "completed_lessons": progress["completed_lessons"],
        "percent": progress["percent"],
        "last_opened": progress["last_opened"],
    }


def save_reading_position(course_id: str, lesson_id: str, position: float) -> Dict:
    state = load_state()
    progress = state.setdefault("progress", {}).setdefault(
        course_id,
        {
            "completed_lessons": [],
            "last_lesson": "",
            "percent": 0.0,
            "updated_at": "",
            "last_opened": "",
            "reading_positions": {},
        },
    )
    reading_positions = progress.setdefault("reading_positions", {})
    safe_position = round(max(0.0, min(1.0, float(position))), 4)
    reading_positions[lesson_id] = {
        "fraction": safe_position,
        "updated_at": _now_label(),
    }
    progress["last_lesson"] = lesson_id
    progress["last_opened"] = _now_label()
    progress["updated_at"] = _now_label()
    state["last_course"] = course_id
    state["last_lesson"] = lesson_id
    save_state(state)
    return {"ok": True, "course_id": course_id, "lesson_id": lesson_id, "fraction": safe_position}


def get_reading_position(course_id: str, lesson_id: str) -> float:
    state = load_state()
    progress = state.get("progress", {}).get(course_id, {})
    reading_positions = progress.get("reading_positions", {}) or {}
    lesson_position = reading_positions.get(lesson_id, {}) or {}
    try:
        return max(0.0, min(1.0, float(lesson_position.get("fraction", 0.0) or 0.0)))
    except Exception:
        return 0.0


def continue_course(course_id: str) -> str:
    manifest = load_course(course_id)
    state = load_state()
    progress = state.get("progress", {}).get(course_id, {})
    last_lesson = str(progress.get("last_lesson", "") or "")
    if last_lesson:
        return last_lesson
    for module in manifest.get("modules", []) or []:
        lessons = module.get("lessons", []) or []
        if lessons:
            return str(lessons[0].get("id", ""))
    return ""
