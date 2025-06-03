"""
Módulo de manipulação de mídia para clonagem de canais do Telegram.

Fornece funcionalidades para download, upload e processamento de diferentes
tipos de mídia durante o processo de clonagem.
"""

import asyncio
import os
import time
import hashlib
import mimetypes
from typing import Optional, Dict, Any, Callable, List, Tuple
from pathlib import Path
import aiofiles

from telethon.tl import types
from telethon.errors import FloodWaitError, FileReferenceExpiredError

from .colors import RED, GREEN, BLUE, YELLOW, CYAN, MAGENTA, RESET


class MediaHandler:
    """Classe para manipular downloads e uploads de mídia."""

    def __init__(self, client, config) -> None:
        """
        Inicializa o manipulador de mídia.

        Args:
            client: Cliente do Telegram
            config: Configurações do sistema
        """
        self.client = client
        self.config = config
        self.temp_dir = Path(config.temp_dir)
        self.temp_dir.mkdir(exist_ok=True)

        self.total_downloaded = 0
        self.total_uploaded = 0
        self.failed_downloads = 0
        self.skipped_files = 0

    async def download_and_send_media(
        self,
        message,
        target_channel,
        progress_callback: Optional[Callable] = None
    ) -> bool:
        """
        Download e envia mídia com suporte para arquivos grandes.

        Args:
            message: Mensagem contendo mídia
            target_channel: Canal de destino
            progress_callback: Callback para progresso

        Returns:
            True se sucesso, False caso contrário
        """
        try:
            if not message.media:
                return False

            if hasattr(message.media, 'webpage'):
                await self._send_webpage_message(message, target_channel)
                return True

            file_info = await self._get_file_info(message.media)
            if not file_info:
                return False

            print(f"{CYAN}Processando: {file_info['name']} "
                  f"({self._format_size(file_info['size'])})")

            if not await self._validate_file(file_info, message, target_channel):
                return False

            file_path = await self._download_media_with_retry(
                message.media,
                file_info,
                progress_callback
            )

            if not file_path:
                self.failed_downloads += 1
                return False

            try:
                success = await self._upload_media_with_retry(
                    file_path,
                    target_channel,
                    message.text or "",
                    progress_callback
                )

                if success:
                    self.total_uploaded += 1
                    print(f"{GREEN}✅ Mídia enviada: {file_info['name']}")
                else:
                    self.failed_downloads += 1
                    print(f"{RED}❌ Falha ao enviar: {file_info['name']}")

                return success

            finally:
                await self._cleanup_temp_file(file_path)

        except Exception as e:
            print(f"{RED}Erro ao processar mídia: {e}")
            self.failed_downloads += 1
            return False

    async def _validate_file(
        self,
        file_info: Dict[str, Any],
        message,
        target_channel
    ) -> bool:
        """Valida se o arquivo deve ser processado."""
        if file_info['size'] > self.config.max_file_size:
            print(f"{YELLOW}⚠️  Arquivo muito grande: "
                  f"{self._format_size(file_info['size'])}")
            await self._send_large_file_notice(message, target_channel, file_info)
            self.skipped_files += 1
            return False

        if (hasattr(self.config, 'allow_all_extensions') and
            not self.config.allow_all_extensions and
                not self._is_supported_format(file_info['extension'])):

            print(
                f"{YELLOW}⚠️  Formato não suportado: {file_info['extension']}")
            await self._send_unsupported_format_notice(message, target_channel, file_info)
            self.skipped_files += 1
            return False

        return True

    async def _get_file_info(self, media) -> Optional[Dict[str, Any]]:
        """Obter informações do arquivo de mídia"""
        try:
            file_info = {
                'name': 'unknown',
                'size': 0,
                'extension': '',
                'mime_type': '',
                'type': 'unknown'
            }

            if hasattr(media, 'photo'):

                file_info.update({
                    'name': f"photo_{int(time.time())}.jpg",
                    'size': getattr(media.photo, 'size', 0),
                    'extension': 'jpg',
                    'mime_type': 'image/jpeg',
                    'type': 'photo'
                })

            elif hasattr(media, 'document'):
                doc = media.document
                file_info.update({
                    'size': doc.size,
                    'mime_type': doc.mime_type or 'application/octet-stream'
                })

                for attr in doc.attributes:
                    if hasattr(attr, 'file_name') and attr.file_name:
                        file_info['name'] = attr.file_name
                        break
                else:
                    ext = mimetypes.guess_extension(doc.mime_type) or '.bin'
                    file_info['name'] = f"file_{doc.id}{ext}"

                file_info['extension'] = Path(
                    file_info['name']).suffix.lower().lstrip('.')

                if 'video' in doc.mime_type:
                    file_info['type'] = 'video'
                elif 'audio' in doc.mime_type:
                    file_info['type'] = 'audio'
                elif 'image' in doc.mime_type:
                    file_info['type'] = 'image'
                else:
                    file_info['type'] = 'document'

            return file_info

        except Exception as e:
            print(RED + f"Erro ao obter informações do arquivo: {e}")
            return None

    async def _download_media_with_retry(
        self,
        media,
        file_info: Dict[str, Any],
        progress_callback: Optional[Callable] = None
    ) -> Optional[Path]:
        """Download de mídia com retry e progresso"""

        file_path = self.temp_dir / file_info['name']

        for attempt in range(self.config.max_retries):
            try:
                print(
                    CYAN + f"Baixando ({attempt + 1}/{self.config.max_retries}): {file_info['name']}")

                async def progress(current, total):
                    if self.config.enable_progress and total > 0:
                        percent = (current / total) * 100
                        print(
                            f"\r{BLUE}Progresso: {percent:.1f}% ({self._format_size(current)}/{self._format_size(total)})", end="")

                    if progress_callback:
                        await progress_callback(current, total, 'download')

                downloaded_file = await asyncio.wait_for(
                    self.client.download_media(
                        media,
                        file=str(file_path),
                        progress_callback=progress if self.config.enable_progress else None
                    ),
                    timeout=self.config.download_timeout
                )

                if downloaded_file:
                    self.total_downloaded += 1
                    print(
                        f"\n{GREEN}✅ Download concluído: {file_info['name']}")

                    if await self._verify_file_integrity(file_path, file_info['size']):
                        return file_path
                    else:
                        print(
                            YELLOW + "⚠️  Arquivo corrompido, tentando novamente...")
                        continue
                else:
                    print(
                        RED + f"❌ Falha no download (tentativa {attempt + 1})")

            except FloodWaitError as e:
                wait_time = e.seconds
                print(
                    YELLOW + f"⏱️  Rate limit atingido, aguardando {wait_time}s...")
                await asyncio.sleep(wait_time)
                continue

            except FileReferenceExpiredError:
                print(
                    YELLOW + "⚠️  Referência do arquivo expirada, tentando atualizar...")

                await asyncio.sleep(self.config.retry_delay)
                continue

            except asyncio.TimeoutError:
                print(
                    RED + f"⏱️  Timeout no download (tentativa {attempt + 1})")

            except Exception as e:
                print(
                    RED + f"❌ Erro no download (tentativa {attempt + 1}): {e}")

            if attempt < self.config.max_retries - 1:
                await asyncio.sleep(self.config.retry_delay)

        print(
            RED + f"❌ Falha ao baixar após {self.config.max_retries} tentativas: {file_info['name']}")
        return None

    async def _upload_media_with_retry(
        self,
        file_path: Path,
        target_channel,
        caption: str = "",
        progress_callback: Optional[Callable] = None
    ) -> bool:
        """Upload de mídia com retry"""

        for attempt in range(self.config.max_retries):
            try:
                print(
                    CYAN + f"Enviando ({attempt + 1}/{self.config.max_retries}): {file_path.name}")

                async def upload_progress(current, total):
                    if self.config.enable_progress and total > 0:
                        percent = (current / total) * 100
                        print(
                            f"\r{BLUE}Upload: {percent:.1f}% ({self._format_size(current)}/{self._format_size(total)})", end="")

                    if progress_callback:
                        await progress_callback(current, total, 'upload')

                await self.client.send_file(
                    target_channel,
                    str(file_path),
                    caption=caption,
                    progress_callback=upload_progress if self.config.enable_progress else None
                )

                print(f"\n{GREEN}✅ Upload concluído: {file_path.name}")

                if self.config.enable_rate_limit:
                    await asyncio.sleep(self.config.rate_limit_delay)

                return True

            except FloodWaitError as e:
                wait_time = e.seconds
                print(
                    YELLOW + f"⏱️  Rate limit no upload, aguardando {wait_time}s...")
                await asyncio.sleep(wait_time)
                continue

            except Exception as e:
                print(RED + f"❌ Erro no upload (tentativa {attempt + 1}): {e}")

                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay)

        print(
            RED + f"❌ Falha no upload após {self.config.max_retries} tentativas: {file_path.name}")
        return False

    async def _verify_file_integrity(self, file_path: Path, expected_size: int) -> bool:
        """Verificar integridade do arquivo baixado"""
        try:
            if not file_path.exists():
                return False

            actual_size = file_path.stat().st_size
            if actual_size != expected_size:
                print(
                    YELLOW + f"⚠️  Tamanho incorreto: esperado {expected_size}, obtido {actual_size}")
                return False

            return True

        except Exception as e:
            print(RED + f"Erro ao verificar integridade: {e}")
            return False

    async def _cleanup_temp_file(self, file_path: Path):
        """Limpar arquivo temporário"""
        try:
            if file_path and file_path.exists():
                file_path.unlink()
        except Exception as e:
            print(RED + f"Erro ao limpar arquivo temporário: {e}")

    def _is_supported_format(self, extension: str) -> bool:
        """Verificar se o formato é suportado"""
        if not extension:
            return True

        if extension.lower() in [ext.lower() for ext in self.config.blocked_extensions]:
            print(YELLOW + f"⚠️  Formato bloqueado: .{extension}")
            return False

        if hasattr(self.config, 'allow_all_extensions') and self.config.allow_all_extensions:
            return True

        return (extension in self.config.supported_video_formats or
                extension in self.config.supported_audio_formats or
                extension in self.config.supported_image_formats or
                extension in self.config.supported_document_formats)

    def _format_size(self, size_bytes: int) -> str:
        """Formatar tamanho em bytes para formato legível"""
        if size_bytes == 0:
            return "0 B"

        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        size = size_bytes

        while size >= 1024 and i < len(size_names) - 1:
            size /= 1024
            i += 1

        return f"{size:.1f} {size_names[i]}"

    async def _send_webpage_message(self, message, target_channel):
        """Enviar mensagem de webpage formatada"""
        try:
            webpage_text = self._format_webpage_message(message)
            await self.client.send_message(target_channel, webpage_text)
        except Exception as e:
            print(RED + f"Erro ao enviar webpage: {e}")

    def _format_webpage_message(self, message) -> str:
        """Formatar mensagem de webpage"""
        return self.format_webpage_message(message)

    @staticmethod
    def format_webpage_message(message) -> str:
        """Formatar mensagem de webpage - método estático para uso externo"""
        try:
            text = message.text or ""

            if hasattr(message.media, 'webpage') and message.media.webpage:
                webpage = message.media.webpage

                title = getattr(webpage, 'title', '')

                description = getattr(webpage, 'description', '')

                url = getattr(webpage, 'url', '')

                formatted_text = text
                if title or description or url:
                    formatted_text += "\n\n🔗 Link:"
                    if title:
                        formatted_text += f"\n📄 {title}"
                    if description:
                        formatted_text += f"\n📋 {description}"
                    if url:
                        formatted_text += f"\n🌐 {url}"

                return formatted_text

            return text

        except Exception as e:
            print(f"Erro ao formatar webpage: {e}")
            return message.text or "[Erro ao processar webpage]"

    async def _send_large_file_notice(self, message, target_channel, file_info: Dict[str, Any]):
        """Enviar aviso sobre arquivo muito grande"""
        try:
            notice = f"{message.text or ''}\n\n"
            notice += f"📎 Arquivo muito grande para cópia:\n"
            notice += f"📄 Nome: {file_info['name']}\n"
            notice += f"📏 Tamanho: {self._format_size(file_info['size'])}\n"
            notice += f"🎯 Tipo: {file_info['type']}\n"
            notice += f"⚠️ Limite máximo: {self._format_size(self.config.max_file_size)}"

            await self.client.send_message(target_channel, notice)
        except Exception as e:
            print(RED + f"Erro ao enviar aviso de arquivo grande: {e}")

    async def _send_unsupported_format_notice(self, message, target_channel, file_info: Dict[str, Any]):
        """Enviar aviso sobre formato não suportado"""
        try:
            notice = f"{message.text or ''}\n\n"
            notice += f"📎 Formato de arquivo não suportado:\n"
            notice += f"📄 Nome: {file_info['name']}\n"
            notice += f"🎯 Tipo: {file_info['extension']}\n"
            notice += f"⚠️ Apenas texto copiado"

            await self.client.send_message(target_channel, notice)
        except Exception as e:
            print(RED + f"Erro ao enviar aviso de formato não suportado: {e}")

    def get_stats(self) -> Dict[str, int]:
        """Obter estatísticas de download/upload"""
        return {
            'downloaded': self.total_downloaded,
            'uploaded': self.total_uploaded,
            'failed': self.failed_downloads,
            'skipped': self.skipped_files
        }

    def reset_stats(self):
        """Resetar estatísticas"""
        self.total_downloaded = 0
        self.total_uploaded = 0
        self.failed_downloads = 0
        self.skipped_files = 0

    async def cleanup_temp_dir(self):
        """Limpar diretório temporário"""
        try:
            if self.temp_dir.exists():
                for file in self.temp_dir.iterdir():
                    if file.is_file():
                        file.unlink()
                print(GREEN + "🧹 Diretório temporário limpo")
        except Exception as e:
            print(RED + f"Erro ao limpar diretório temporário: {e}")
