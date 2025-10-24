"""Manipuladores otimizados para opções do menu principal."""

import asyncio
from typing import Optional

from .telegram_client import TCloneClient
from .cloner import ChannelCloner
from .config import Config
from .downloader import MediaDownloader
from .colors import RED, GREEN, BLUE, YELLOW, CYAN, MAGENTA, RESET


class MenuHandlers:
    """Gerenciador de handlers do menu principal."""

    def __init__(self, client: TCloneClient, config: Config) -> None:
        self.client = client
        self.config = config
        self.cloner = ChannelCloner(client.client)

    async def handle_connect(self) -> bool:
        """Handler para conectar e listar canais disponíveis."""
        print(
            GREEN + f"Conectando ao Telegram com API ID: {self.client.api_id}")

        try:
            chat_count = await self.client.connect_and_list_dialogs()
            if chat_count > 0:
                print(YELLOW + f"Selecionar chat (0-{chat_count-1}):")
            return True
        except Exception as e:
            print(RED + f"Erro: {e}")
            return False

    async def handle_send_message(self) -> bool:
        """Handler para envio de mensagens."""
        print(GREEN + "Função de envio de mensagem")

        try:
            target_input = input(
                YELLOW + "Digite o username ou ID do usuário: ")
            message_text = input(YELLOW + "Digite a mensagem: ")

            if not target_input or not message_text:
                print(RED + "Username/ID e mensagem são obrigatórios!")
                return False

            return await self.client.send_message(target_input, message_text)

        except Exception as e:
            print(RED + f"Erro: {e}")
            return False

    async def handle_clone_channel(self) -> bool:
        """Handler para clonagem de canal/chat individual."""
        print(GREEN + "Função de clonagem de Canal/Chat")

        try:
            channels_and_groups = await self.cloner.list_channels_and_groups()

            if not channels_and_groups:
                print(RED + "Nenhum canal ou grupo encontrado!")
                return False

            return await self._process_channel_cloning(channels_and_groups)

        except Exception as e:
            print(RED + f"Erro: {e}")
            return False

    async def _process_channel_cloning(self, channels_and_groups) -> bool:
        """Processa seleção e clonagem de canal."""
        try:
            choice = int(input(
                YELLOW +
                f"Selecione o canal/grupo (0-{len(channels_and_groups)-1}): "
            ))

            if choice < 0 or choice >= len(channels_and_groups):
                print(RED + "Opção inválida!")
                return False

            source_dialog = channels_and_groups[choice]
            print(GREEN + f"Canal/Grupo selecionado: {source_dialog.name}")

            clone_config = self._get_clone_configuration(source_dialog.name)

            new_channel = await self.cloner.clone_channel_complete(
                source_dialog,
                clone_config['title'],
                clone_config['about'],
                clone_config['is_public'],
                clone_config['username'],
                clone_config['copy_messages'],
                clone_config['message_limit'],
                clone_config['download_media'],
                clone_config['resume_enabled']
            )

            return self._handle_clone_result(new_channel, clone_config)

        except ValueError:
            print(RED + "Por favor, digite um número válido!")
            return False

    def _get_clone_configuration(self, source_name: str) -> dict:
        """Obtém configurações para clonagem completa com resume."""
        print(GREEN + "🔧 Configuração de Clonagem Completa")
        print(CYAN + "Esta opção clona TUDO: mensagens, mídias, fotos, vídeos, documentos")
        print(CYAN + "Inclui funcionalidade de continuar de onde parou (resume)")
        print()

        new_title = input(
            YELLOW + f"Nome do novo canal (padrão: 'Clone de {source_name}'): "
        ) or f"Clone de {source_name}"

        new_about = input(YELLOW + "Descrição do novo canal: ")

        is_public = input(
            YELLOW + "Canal público? (s/n): ").lower().startswith('s')
        username = ""
        if is_public:
            username = input(YELLOW + "Username do canal (sem @): ")

        # Sempre copia mensagens na versão completa
        print(GREEN + "✅ Copiar mensagens: ATIVADO (clonagem completa)")

        # Limite de mensagens mais alto por padrão
        try:
            message_limit = int(
                input(
                    YELLOW + "Quantas mensagens copiar? (padrão: TODAS - digite 0): ") or "0"
            )
            if message_limit == 0:
                message_limit = None  # Sem limite = todas as mensagens
        except ValueError:
            message_limit = None

        # Configurações de mídia
        print(GREEN + "✅ Baixar todas as mídias: ATIVADO")

        # Funcionalidade de resume
        resume_enabled = input(
            YELLOW +
            "Ativar modo resume (continuar de onde parou)? (s/n, padrão: s): "
        ).lower()
        resume_enabled = not resume_enabled or resume_enabled.startswith('s')

        return {
            'title': new_title,
            'about': new_about,
            'is_public': is_public,
            'username': username,
            'copy_messages': True,  # Sempre True na versão completa
            'message_limit': message_limit,
            'download_media': True,  # Nova opção
            'resume_enabled': resume_enabled  # Nova opção
        }

    def _handle_clone_result(self, new_channel, config: dict) -> bool:
        """Processa resultado da clonagem."""
        if new_channel:
            print(GREEN + "Clonagem concluída com sucesso!")
            print(CYAN + f"Novo canal: {new_channel.title}")
            if config['is_public'] and config['username']:
                print(CYAN + f"Link: https://t.me/{config['username']}")
            return True

        return False

    async def handle_download_media(self) -> bool:
        """Baixa fotos e vídeos de um ou mais chats/canais."""
        print(GREEN + "📥 Download de mídias (fotos e vídeos)")

        try:
            await self.client.client.start()

            dialogs = await self.client.client.get_dialogs()
            if not dialogs:
                print(RED + "Nenhum chat/canal encontrado")
                return False

            # Listagem resumida
            print(YELLOW + "Chats/Canais disponíveis:")
            for idx, d in enumerate(dialogs):
                name = getattr(d, 'name', None) or getattr(
                    d.entity, 'title', None) or str(getattr(d.entity, 'id', 'chat'))
                print(CYAN + f"{idx}. {name}")

            sel = input(
                YELLOW + "Selecione o índice (ou * para todos): ").strip()
            if sel == "*":
                selected = list(dialogs)
            else:
                try:
                    i = int(sel)
                    if i < 0 or i >= len(dialogs):
                        print(RED + "Índice inválido")
                        return False
                    selected = [dialogs[i]]
                except ValueError:
                    print(RED + "Entrada inválida")
                    return False

            # Tipos de mídia
            print(YELLOW + "Tipos: 1) Imagens  2) Vídeos  3) Ambos (padrão)")
            tsel = input(YELLOW + "Escolha (1/2/3): ").strip()
            if tsel == "1":
                media_types = ("image",)
            elif tsel == "2":
                media_types = ("video",)
            else:
                media_types = ("image", "video")

            # Limite de mensagens a inspecionar
            lraw = input(
                YELLOW + "Limite de mensagens a verificar (Enter = sem limite): ").strip()
            limit = None
            if lraw:
                try:
                    limit = int(lraw)
                except ValueError:
                    print(RED + "Limite inválido, usando sem limite")

            # Diretório de download
            base_dir = input(
                YELLOW + f"Diretório base (padrão: {self.config.download_dir}): ").strip() or self.config.download_dir

            downloader = MediaDownloader(self.client.client, base_dir)
            results = await downloader.download_from_dialogs(selected, media_types=media_types, limit=limit)

            # Resumo geral
            total_downloaded = sum(r["downloaded"] for r in results)
            total_errors = sum(r["errors"] for r in results)
            print(
                GREEN + f"\n✅ Concluído. Arquivos baixados: {total_downloaded}")
            if total_errors:
                print(RED + f"❌ Erros: {total_errors}")
            print(CYAN + f"Diretório base: {base_dir}")
            return True

        except Exception as e:
            print(RED + f"Erro no download: {e}")
            return False
