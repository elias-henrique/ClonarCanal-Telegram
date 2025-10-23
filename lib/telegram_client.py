"""Cliente otimizado para operações do Telegram."""

import asyncio
from typing import Optional, List, Dict, Any

from telethon import TelegramClient

from .colors import RED, GREEN, BLUE, YELLOW, CYAN, MAGENTA, RESET


class TCloneClient:
    """Cliente principal para operações do Telegram."""

    def __init__(self, session_name: str, api_id: int, api_hash: str) -> None:
        self.session_name = session_name
        self.api_id = api_id
        self.api_hash = api_hash
        self.client = TelegramClient(session_name, api_id, api_hash)

    async def get_session_info(self) -> Optional[Dict[str, Any]]:
        """Obtém informações da sessão atual."""
        try:
            await self.client.start()
            me = await self.client.get_me()
            session_info = {
                'user_id': me.id if me else None,
                'username': me.username if me else None,
                'phone': me.phone if me else None,
                'first_name': me.first_name if me else None,
                'last_name': me.last_name if me else None,
            }
            await self.client.disconnect()
            return session_info
        except Exception as e:
            print(RED + f"Erro ao conectar: {e}")
            return None

    async def connect_and_list_dialogs(self, limit: int = 20) -> int:
        """Conecta e lista diálogos disponíveis."""
        try:
            await self.client.start()
            print(GREEN + "Conectado com sucesso!")

            dialogs = await self.client.get_dialogs()
            print(YELLOW + "Chats Disponíveis:")

            count = 0
            for dialog in dialogs:
                try:
                    entity = dialog.entity
                    entity_type = self._get_entity_type(entity)
                    print(f"{CYAN}{count}{BLUE}. {dialog.name} "
                          f"{entity_type}{BLUE} ID: {MAGENTA}{entity.id}")
                    count += 1

                    if count >= limit:
                        break
                except Exception:
                    continue

            await self.client.disconnect()
            return count

        except Exception as e:
            print(RED + f"Falha na conexão: {e}")
            return 0

    async def send_message(self, target: str, message: str) -> bool:
        """Envia mensagem para usuário ou chat especificado."""
        try:
            await self.client.start()

            entity = await self._get_entity_by_identifier(target)
            await self.client.send_message(entity, message)

            entity_name = getattr(
                entity, 'first_name',
                getattr(entity, 'title', 'Usuário')
            )
            print(GREEN + f"Mensagem enviada com sucesso para {entity_name}!")

            await self.client.disconnect()
            return True

        except Exception as e:
            print(RED + f"Erro ao enviar mensagem: {e}")
            await self.client.disconnect()
            return False

    async def _get_entity_by_identifier(self, target: str):
        """Obtém entidade por username, ID ou nome."""
        if target.startswith('@'):
            return await self.client.get_entity(target)
        elif target.isdigit():
            return await self.client.get_entity(int(target))
        else:
            return await self.client.get_entity(target)

    def _get_entity_type(self, entity) -> str:
        """Determina tipo da entidade para exibição."""
        if hasattr(entity, 'bot') and entity.bot:
            return RED + "(Bot)"
        elif hasattr(entity, 'broadcast') and entity.broadcast:
            return RED + "(Canal)"
        elif hasattr(entity, 'megagroup') and entity.megagroup:
            return GREEN + "(Supergrupo)"
        elif hasattr(entity, 'username'):
            return MAGENTA + "(User)"
        else:
            return GREEN + "(Chat)"

    async def disconnect(self) -> None:
        """Desconecta cliente se conectado."""
        if self.client.is_connected():
            await self.client.disconnect()
