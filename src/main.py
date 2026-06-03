"""
SongVault - Suno Music Backup & Downloader
===========================================
Apify Actor para descargar todas tus canciones de Suno AI
con metadatos completos, organizadas por workspaces.
"""

import re
import json
import time
import logging
from pathlib import Path
from typing import Optional

import requests
from apify import Actor
from mutagen.id3 import ID3, TIT2, TPE1, TDRC, APIC, TCON, ID3NoHeaderError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("songvault")

BASE_API = "https://studio-api.prod.suno.com/api"
PAGE_SIZE = 20
MAX_RETRIES = 5
MAX_BACKOFF = 60
DELAY_BETWEEN = 3.0
DELAY_FILES = 1.5

_api = requests.Session()
_adapter = requests.adapters.HTTPAdapter(pool_connections=1, pool_maxsize=1, max_retries=0)
_api.mount("https://", _adapter)


def sanitize(name: str) -> str:
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    return name.strip(". ")[:100] or "untitled"


def headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "SongVault/1.0",
        "Referer": "https://suno.com/",
    }


def api_post(url: str, token: str, payload: dict) -> Optional[dict]:
    for attempt in range(MAX_RETRIES):
        try:
            r = _api.post(url, headers=headers(token), json=payload, timeout=30)
            if r.status_code in (401, 403):
                logger.error("Token invalido o expirado (HTTP %s)", r.status_code)
                return None
            if r.status_code == 429:
                wait = min(2 ** attempt, MAX_BACKOFF)
                time.sleep(wait + 2)
                continue
            if r.status_code >= 500:
                time.sleep(min(2 ** attempt, MAX_BACKOFF))
                continue
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.warning("API error (intento %d): %s", attempt + 1, e)
            time.sleep(min(2 ** attempt, MAX_BACKOFF))
    return None


def api_get(url: str, token: str, params: dict = None) -> Optional[dict]:
    for attempt in range(MAX_RETRIES):
        try:
            r = _api.get(url, headers=headers(token), params=params, timeout=30)
            if r.status_code in (401, 403):
                logger.error("Token invalido o expirado (HTTP %s)", r.status_code)
                return None
            if r.status_code == 429:
                time.sleep(min(2 ** attempt, MAX_BACKOFF) + 2)
                continue
            if r.status_code >= 500:
                time.sleep(min(2 ** attempt, MAX_BACKOFF))
                continue
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.warning("API error (intento %d): %s", attempt + 1, e)
            time.sleep(min(2 ** attempt, MAX_BACKOFF))
    return None


def fetch_feed(token: str, project_id: str = None, max_songs: int = None) -> list:
    clips, cursor = [], None
    while True:
        payload = {
            "cursor": cursor,
            "limit": PAGE_SIZE,
            "filters": {"disliked": "False", "trashed": "False", "stem": {"presence": "False"}},
        }
        if project_id:
            payload["filters"]["workspace"] = {"presence": "True", "workspaceId": project_id}
        else:
            payload["filters"]["fromStudioProject"] = {"presence": "False"}
        data = api_post(f"{BASE_API}/feed/v3", token, payload)
        if not data:
            break
        batch = data.get("clips", [])
        if not batch:
            break
        clips.extend(batch)
        if max_songs and len(clips) >= max_songs:
            return clips[:max_songs]
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
        if not cursor:
            break
    return clips


def get_workspaces(token: str) -> list:
    projects, page = [], 1
    while True:
        data = api_get(f"{BASE_API}/project/me", token, {
            "page": page, "sort": "max_created_at_last_updated_clip",
            "show_trashed": "false", "exclude_shared": "false",
        })
        if not data:
            break
        batch = data.get("projects", [])
        if not batch:
            break
        projects.extend(batch)
        if not data.get("has_more"):
            break
        page += 1
    return projects


def download_file(url: str, dest: Path) -> bool:
    if dest.exists() and dest.stat().st_size > 0:
        return True
    for attempt in range(MAX_RETRIES):
        try:
            r = _api.get(url, headers={
                "User-Agent": "SongVault/1.0", "Referer": "https://suno.com/",
            }, timeout=120, stream=True)
            r.raise_for_status()
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_suffix(dest.suffix + ".tmp")
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(65536):
                    f.write(chunk)
            tmp.rename(dest)
            return True
        except Exception as e:
            logger.warning("Download error (intento %d): %s", attempt + 1, e)
            time.sleep(min(2 ** attempt, 30))
    return False


def embed_tags(mp3_path: Path, clip: dict, img_path: Path = None):
    try:
        try:
            tags = ID3(str(mp3_path))
        except ID3NoHeaderError:
            tags = ID3()
        title = clip.get("title") or "Unknown"
        artist = clip.get("display_name") or "Suno AI"
        created = (clip.get("created_at") or "")[:4]
        meta = clip.get("metadata") or {}
        genre = clip.get("display_tags") or meta.get("tags") or ""
        tags["TIT2"] = TIT2(encoding=3, text=title)
        tags["TPE1"] = TPE1(encoding=3, text=artist)
        if created:
            tags["TDRC"] = TDRC(encoding=3, text=created)
        if genre:
            tags["TCON"] = TCON(encoding=3, text=genre[:50])
        if img_path and img_path.exists():
            mime = "image/jpeg" if img_path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
            with open(img_path, "rb") as f:
                tags["APIC"] = APIC(encoding=3, mime=mime, type=3, desc="Cover", data=f.read())
        tags.save(str(mp3_path), v2_version=3)
    except Exception as e:
        logger.warning("Tags error: %s", e)


def save_clip(clip: dict, folder: Path, fmt: str, meta: bool, token: str = "") -> dict:
    cid = clip.get("id", "unknown")
    title = clip.get("title") or "untitled"
    base = f"{sanitize(title)}__{cid[:8]}"
    folder.mkdir(parents=True, exist_ok=True)
    result = {"id": cid, "title": title, "audio": False, "cover": False, "txt": False, "json": False}

    if meta:
        txt_path = folder / f"{base}.txt"
        if not txt_path.exists():
            m = clip.get("metadata") or {}
            lyrics = m.get("prompt") or clip.get("lyrics") or ""
            style = m.get("tags") or clip.get("style") or ""
            gpt = m.get("gpt_description_prompt") or ""
            tags = clip.get("display_tags") or ""
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(f"TITULO:  {title}\nID:      {cid}\n")
                f.write(f"MODELO:  {clip.get('model_name','')}\nCREADO:  {clip.get('created_at','')}\n")
                if tags: f.write(f"TAGS:    {tags}\n")
                f.write("\n")
                if gpt: f.write(f"-- PROMPT --\n{gpt}\n\n")
                if style: f.write(f"-- ESTILO --\n{style}\n\n")
                if lyrics: f.write(f"-- LETRA --\n{lyrics}\n")
        result["txt"] = True

        json_path = folder / f"{base}.json"
        if not json_path.exists():
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(clip, f, ensure_ascii=False, indent=2)
        result["json"] = True

    ext = ".wav" if fmt == "wav" else ".mp3"
    audio_key = "wav" if fmt == "wav" else "mp3"
    audio_url = clip.get("audio_url") or clip.get("audio_url_proxy") or ""

    if fmt == "wav":
        wav_path = folder / f"{base}.wav"
        if not (wav_path.exists() and wav_path.stat().st_size > 0):
            logger.info("Convirtiendo a WAV: %s...", title[:40])
            resp = api_post(f"{BASE_API}/gen/{cid}/convert_wav/", token, {})
            if resp is not None:
                for _ in range(60):
                    r = _api.get(f"{BASE_API}/gen/{cid}/wav_file/", headers=headers(token), timeout=30)
                    if r.status_code == 200:
                        wav_url = r.json().get("wav_file_url")
                        if wav_url:
                            result[audio_key] = download_file(wav_url, wav_path)
                            break
                    time.sleep(5)
            if not result.get(audio_key):
                logger.info("WAV no disponible, usando MP3 como fallback")
                if audio_url:
                    result[audio_key] = download_file(audio_url, folder / f"{base}.mp3")
    else:
        if audio_url:
            time.sleep(DELAY_FILES)
            result[audio_key] = download_file(audio_url, folder / f"{base}.mp3")

    img_url = clip.get("image_large_url") or clip.get("image_url") or ""
    img_path = None
    if img_url:
        ext_img = Path(img_url.split("?")[0]).suffix or ".jpg"
        img_path = folder / f"{base}{ext_img}"
        if not (img_path.exists() and img_path.stat().st_size > 0):
            time.sleep(DELAY_FILES)
            result["cover"] = download_file(img_url, img_path)

    if fmt == "mp3" and result.get("mp3"):
        embed_tags(folder / f"{base}.mp3", clip, img_path)

    return result


async def main():
    async with Actor:
        actor_input = await Actor.get_input() or {}
        token = actor_input.get("sunoToken", "")
        fmt = actor_input.get("format", "mp3")
        mode = actor_input.get("mode", "all")
        ws_name = actor_input.get("workspaceName", "")
        include_meta = actor_input.get("includeMetadata", True)
        delete_after = actor_input.get("deleteAfterDownload", False)

        if not token:
            logger.error("Token de Suno no proporcionado")
            await Actor.fail("Se requiere el token de Suno")
            return

        logger.info("SongVault iniciado - Formato: %s", fmt)
        await Actor.push_data({"event": "start", "format": fmt})

        workspaces = get_workspaces(token)
        all_clips = []

        if mode == "workspace" and ws_name:
            for ws in workspaces:
                name = ws.get("name") or ws.get("title") or ""
                if name.lower() == ws_name.lower():
                    clips = fetch_feed(token, project_id=ws.get("id"))
                    all_clips = [(c, sanitize(name)) for c in clips]
                    break
            if not all_clips:
                logger.warning("Workspace '%s' no encontrado", ws_name)
                names = [ws.get("name","?") for ws in workspaces]
                logger.info("Disponibles: %s", ", ".join(names))
        else:
            max_s = 5 if mode == "debug" else None
            for ws in workspaces:
                name = sanitize(ws.get("name") or ws.get("title") or ws.get("id",""))
                clips = fetch_feed(token, project_id=ws.get("id"), max_songs=max_s)
                all_clips.extend((c, name) for c in clips)
            if mode == "all":
                lib = fetch_feed(token, max_songs=max_s)
                all_clips.extend((c, "_library_all") for c in lib)

        logger.info("Total canciones: %d", len(all_clips))

        downloaded, failed = 0, 0
        for clip, ws_folder in all_clips:
            folder = Path("/storage/key_value_store") / ws_folder
            result = save_clip(clip, folder, fmt, include_meta, token)
            key = "wav" if fmt == "wav" else "mp3"
            if result.get(key) or result.get("json"):
                downloaded += 1
            else:
                failed += 1
            await Actor.push_data({
                "title": result["title"],
                "id": result["id"],
                "status": "ok" if result.get(key) else "fallback" if result.get("json") else "fail",
                "workspace": ws_folder,
            })
            if not result.get(key):
                logger.warning("Fallo: %s", result["title"][:50])
            time.sleep(DELAY_BETWEEN)

        if delete_after:
            logger.info("Eliminando canciones de Suno...")
            all_ids = [c[0].get("id") for c in all_clips if c[0].get("id")]
            for i in range(0, len(all_ids), 20):
                batch = all_ids[i:i+20]
                api_post(f"{BASE_API}/feed/trash", token, {"ids": batch})
                time.sleep(1)
            logger.info("Eliminadas %d canciones de suno.com", len(all_ids))

        logger.info("SongVault completado - %d descargadas, %d fallos", downloaded, failed)
        await Actor.push_data({"event": "complete", "downloaded": downloaded, "failed": failed})


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
