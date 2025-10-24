"""Downloader de mídias (fotos e vídeos) do Telegram.

Fornece utilitários para baixar fotos e vídeos de um ou mais chats/canais
para pastas locais organizadas por conversa.
"""

import asyncio
import json
from pathlib import Path
from typing import Iterable, List, Optional

from .colors import RED, GREEN, YELLOW, CYAN, MAGENTA, RESET


def _sanitize(name: str) -> str:
    """Remove caracteres problemáticos para nome de pastas/arquivos."""
    keep = "-_.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    cleaned = "".join(c if c in keep else "_" for c in name or "chat")
    return "_".join(cleaned.split())[:120]


class MediaDownloader:
    """Baixa fotos e vídeos usando um cliente Telethon já autenticado."""

    def __init__(self, client, download_root: str) -> None:
        self.client = client
        self.base_dir = Path(download_root)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def download_dialog_media(
        self,
        dialog,
        media_types: Iterable[str] = ("image", "video"),
        limit: Optional[int] = None,
    ):
        """Baixa mídias de um único diálogo.

        Args:
            dialog: diálogo retornado por client.get_dialogs()
            media_types: 'image', 'video' ou ambos
            limit: máximo de mensagens a inspecionar (mais antigas inclusive)

        Returns:
            dict com estatísticas do download
        """
        entity = dialog.entity
        title = getattr(dialog, "name", None) or getattr(
            entity, "title", None) or str(getattr(entity, "id", "chat"))
        folder = self.base_dir / _sanitize(title)
        folder.mkdir(parents=True, exist_ok=True)

        count_total = 0
        count_downloaded = 0
        count_skipped = 0
        count_errors = 0

        want_images = any(t.lower().startswith("image") for t in media_types)
        want_videos = any(t.lower().startswith("video") for t in media_types)

        print(CYAN + f"📥 Baixando mídias de: {title}")

        progress_path = folder / ".progress.json"
        last_id = 0
        if progress_path.exists():
            try:
                data = json.loads(progress_path.read_text(encoding="utf-8"))
                last_id = int(data.get("last_id", 0))
                if last_id > 0:
                    print(
                        YELLOW + f"↻ Retomando a partir da mensagem ID {last_id}")
            except Exception:
                last_id = 0

        processed_since_save = 0
        async for msg in self.client.iter_messages(entity, limit=limit, reverse=True, min_id=last_id):
            try:
                media = msg.media
                if not media:

                    last_id = max(last_id, getattr(msg, "id", last_id))
                    processed_since_save += 1
                    if processed_since_save >= 50:
                        self._save_progress(progress_path, last_id)
                        processed_since_save = 0
                    continue

                is_image = bool(getattr(msg, "photo", None))

                is_video = False
                if getattr(msg, "video", None):
                    is_video = True
                elif getattr(msg, "document", None) and getattr(msg.document, "mime_type", "").startswith("video/"):
                    is_video = True

                if (is_image and not want_images) or (is_video and not want_videos):
                    continue
                if not is_image and not is_video:

                    continue

                count_total += 1

                result_path = await self.client.download_media(msg, file=str(folder))
                if result_path:
                    print(GREEN + f"✔ Baixado: {Path(result_path).name}")
                    count_downloaded += 1
                else:
                    print(YELLOW + "⚠️  Ignorado (já existe ou sem dados)")
                    count_skipped += 1

                last_id = max(last_id, getattr(msg, "id", last_id))
                processed_since_save += 1
                if processed_since_save >= 50:
                    self._save_progress(progress_path, last_id)
                    processed_since_save = 0

            except asyncio.CancelledError:
                raise
            except Exception as e:
                print(RED + f"❌ Erro ao baixar: {e}")
                count_errors += 1

                last_id = max(last_id, getattr(msg, "id", last_id))
                processed_since_save += 1
                if processed_since_save >= 50:
                    self._save_progress(progress_path, last_id)
                    processed_since_save = 0

        self._save_progress(progress_path, last_id)

        print(
            MAGENTA + f"Resumo '{title}': baixados={count_downloaded}, ignorados={count_skipped}, erros={count_errors}")
        return {
            "title": title,
            "downloaded": count_downloaded,
            "skipped": count_skipped,
            "errors": count_errors,
            "inspected": count_total,
            "folder": str(folder),
        }

    async def download_from_dialogs(
        self,
        dialogs: List,
        media_types: Iterable[str] = ("image", "video"),
        limit: Optional[int] = None,
    ):
        """Baixa mídias de uma lista de diálogos e retorna estatísticas por diálogo."""
        results = []
        for d in dialogs:
            res = await self.download_dialog_media(d, media_types=media_types, limit=limit)
            results.append(res)
        return results

    def _save_progress(self, progress_path: Path, last_id: int) -> None:
        try:
            progress_path.write_text(json.dumps(
                {"last_id": int(last_id)}), encoding="utf-8")
        except Exception:

            pass
