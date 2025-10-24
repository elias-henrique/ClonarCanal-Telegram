"""
Módulo de clonagem de canais e grupos do Telegram.

Fornece funcionalidades para clonar canais, grupos e supergrupos
incluindo suas mensagens e mídias.
"""

import asyncio
import time
import os
from typing import List, Dict, Any, Optional, Tuple
from telethon.tl import functions

from .colors import RED, GREEN, BLUE, YELLOW, CYAN, MAGENTA, RESET


class ChannelCloner:
    """Classe para clonagem de canais e grupos do Telegram."""

    def __init__(self, client) -> None:
        """
        Inicializa o clonador de canais.

        Args:
            client: Cliente do Telegram para operações
        """
        self.client = client

    async def list_channels_and_groups(self, limit: int = 30) -> List[Any]:
        """
        Lista canais e grupos disponíveis.

        Args:
            limit: Número máximo de canais/grupos a listar

        Returns:
            Lista de diálogos de canais e grupos
        """
        await self.client.start()
        dialogs = await self.client.get_dialogs()

        channels_and_groups = []
        print(f"{YELLOW}Canais e Grupos Disponíveis:")
        count = 0

        for dialog in dialogs:
            try:
                entity = dialog.entity
                if (hasattr(entity, 'megagroup') or
                    hasattr(entity, 'broadcast') or
                        hasattr(entity, 'gigagroup')):

                    channels_and_groups.append(dialog)
                    entity_type = self._get_channel_type(entity)

                    print(f"{CYAN}{count}{BLUE}. {dialog.name} "
                          f"{entity_type}{BLUE} ID: {MAGENTA}{entity.id}")
                    count += 1

                    if count >= limit:
                        break
            except Exception:
                continue

        return channels_and_groups

    async def list_supergroups_only(self, limit: int = 30) -> List[Any]:
        """
        Lista apenas supergrupos disponíveis.

        Args:
            limit: Número máximo de supergrupos a listar

        Returns:
            Lista de diálogos de supergrupos
        """
        await self.client.start()
        dialogs = await self.client.get_dialogs()

        supergroups = []
        print(f"{YELLOW}Supergrupos Disponíveis:")
        count = 0

        for dialog in dialogs:
            try:
                entity = dialog.entity
                if hasattr(entity, 'megagroup') and entity.megagroup:
                    supergroups.append(dialog)
                    print(f"{CYAN}{count}{BLUE}. {dialog.name} "
                          f"{GREEN}(Supergrupo){BLUE} ID: {MAGENTA}{entity.id}")
                    count += 1

                    if count >= limit:
                        break
            except Exception:
                continue

        return supergroups

    async def clone_supergroup_with_channels(
        self,
        source_dialog,
        new_base_title: str
    ) -> Dict[str, Any]:
        """
        Clona um supergrupo e todos os canais relacionados.

        Args:
            source_dialog: Diálogo do supergrupo original
            new_base_title: Título base para o novo supergrupo

        Returns:
            Dicionário com resultados da clonagem
        """
        results = {
            'main_group': None,
            'channels': [],
            'errors': []
        }

        try:
            source_entity = source_dialog.entity

            print(
                f"{CYAN}Iniciando clonagem completa do supergrupo: {source_dialog.name}")

            main_group = await self._clone_main_supergroup(source_dialog, new_base_title)
            if not main_group:
                return results

            results['main_group'] = main_group

            related_channels = await self._find_related_channels(
                source_entity,
                source_dialog.name
            )

            if related_channels:
                await self._clone_related_channels(
                    related_channels,
                    new_base_title,
                    source_dialog.name,
                    results
                )
            else:
                print(f"{YELLOW}Nenhum canal relacionado encontrado")

            await self._link_cloned_channels(results)

            return results

        except Exception as e:
            print(f"{RED}Erro durante a clonagem completa: {e}")
            results['errors'].append(str(e))
            return results

    async def _clone_main_supergroup(self, source_dialog, new_base_title: str) -> Optional[Any]:
        """Clona o supergrupo principal."""
        print(f"{CYAN}Clonando supergrupo principal...")

        main_group = await self.clone_channel(
            source_dialog,
            new_base_title,
            copy_messages=True,
            message_limit=200
        )

        if main_group:
            print(f"{GREEN}Supergrupo principal clonado: {main_group.title}")
        else:
            print(f"{RED}Falha ao clonar supergrupo principal")

        return main_group

    async def _clone_related_channels(
        self,
        related_channels: List[Any],
        new_base_title: str,
        original_name: str,
        results: Dict[str, Any]
    ) -> None:
        """Clona canais relacionados ao supergrupo."""
        print(f"{CYAN}Encontrados {len(related_channels)} canais relacionados")

        for i, channel_dialog in enumerate(related_channels):
            try:
                channel_name = self._generate_channel_name(
                    channel_dialog,
                    new_base_title,
                    original_name,
                    i
                )

                print(
                    f"{CYAN}Clonando canal: {channel_dialog.name} -> {channel_name}")

                cloned_channel = await self.clone_channel(
                    channel_dialog,
                    channel_name,
                    copy_messages=True,
                    message_limit=100
                )

                if cloned_channel:
                    results['channels'].append(cloned_channel)
                    print(f"{GREEN}Canal clonado: {cloned_channel.title}")
                else:
                    results['errors'].append(
                        f"Falha ao clonar canal: {channel_dialog.name}")

                await asyncio.sleep(2)

            except Exception as e:
                error_msg = f"Erro ao clonar canal {channel_dialog.name}: {e}"
                print(f"{RED}{error_msg}")
                results['errors'].append(error_msg)

    def _generate_channel_name(
        self,
        channel_dialog,
        new_base_title: str,
        original_name: str,
        index: int
    ) -> str:
        """Gera nome para canal clonado."""
        if not channel_dialog.name:
            return f"{new_base_title} - Canal {index + 1}"

        original_channel_name = channel_dialog.name

        if "canal" in original_channel_name.lower():
            return original_channel_name.replace(original_name, new_base_title)
        else:
            return f"{new_base_title} - {original_channel_name}"

    async def _find_related_channels(self, source_entity, base_name: str) -> List[Any]:
        """
        Encontra canais relacionados ao supergrupo.

        Args:
            source_entity: Entidade do supergrupo original
            base_name: Nome base para busca

        Returns:
            Lista de canais relacionados
        """
        try:
            print(f"{CYAN}Buscando canais relacionados...")

            related_channels = []
            dialogs = await self.client.get_dialogs()
            base_words = base_name.lower().split()

            for dialog in dialogs:
                try:
                    entity = dialog.entity

                    if hasattr(entity, 'broadcast') and entity.broadcast:
                        if self._is_channel_related(dialog.name, base_words):
                            related_channels.append(dialog)
                            print(
                                f"{BLUE}Canal relacionado encontrado: {dialog.name}")

                        elif await self._is_channel_linked_to_group(source_entity, entity):
                            related_channels.append(dialog)
                            print(
                                f"{BLUE}Canal linkado encontrado: {dialog.name}")

                except Exception:
                    continue

            return related_channels

        except Exception as e:
            print(f"{RED}Erro ao buscar canais relacionados: {e}")
            return []

    def _is_channel_related(self, channel_name: str, base_words: List[str]) -> bool:
        """Verifica se canal está relacionado baseado no nome."""
        channel_name_lower = channel_name.lower()
        name_similarity = sum(
            1 for word in base_words if word in channel_name_lower)
        return name_similarity >= 1

    async def _is_channel_linked_to_group(self, group_entity, channel_entity) -> bool:
        """
        Verifica se um canal está linkado ao grupo.

        Args:
            group_entity: Entidade do grupo
            channel_entity: Entidade do canal

        Returns:
            True se o canal estiver linkado ao grupo
        """
        try:
            full_info = await self.client(
                functions.channels.GetFullChannelRequest(group_entity)
            )

            if hasattr(full_info.full_chat, 'linked_chat_id'):
                return full_info.full_chat.linked_chat_id == channel_entity.id

            return False

        except Exception:
            return False

    async def _link_cloned_channels(self, results: Dict[str, Any]) -> None:
        """
        Tenta criar links entre os canais clonados.

        Args:
            results: Dicionário com resultados da clonagem
        """
        try:
            if not results['main_group'] or not results['channels']:
                return

            print(f"{CYAN}Criando links entre canais clonados...")

            for channel in results['channels']:
                try:
                    await self._announce_linked_channel(results['main_group'], channel)
                except Exception as e:
                    print(
                        f"{YELLOW}Aviso: Não foi possível linkar canal {channel.title}: {e}")

        except Exception as e:
            print(f"{RED}Erro ao criar links: {e}")

    async def _announce_linked_channel(self, main_group, channel) -> None:
        """
        Anuncia canal relacionado no grupo principal.

        Args:
            main_group: Grupo principal
            channel: Canal a ser anunciado
        """
        try:
            if hasattr(channel, 'username') and channel.username:
                link_message = f"📢 Canal relacionado: @{channel.username}"
            else:
                link_message = f"📢 Canal relacionado: {channel.title}"

            await self.client.send_message(main_group, link_message)
            print(f"{GREEN}Canal anunciado no grupo: {channel.title}")

        except Exception as e:
            print(f"{YELLOW}Não foi possível anunciar canal: {e}")

    async def clone_channel(
        self,
        source_dialog,
        new_title: str,
        new_about: str = "",
        is_public: bool = False,
        username: str = "",
        copy_messages: bool = True,
        message_limit: int = 100
    ) -> Optional[Any]:
        """
        Clona um canal ou grupo.

        Args:
            source_dialog: Diálogo do canal/grupo original
            new_title: Título do novo canal/grupo
            new_about: Descrição do novo canal/grupo
            is_public: Se o canal deve ser público
            username: Username para canal público
            copy_messages: Se deve copiar mensagens
            message_limit: Limite de mensagens a copiar

        Returns:
            Canal/grupo clonado ou None se falhar
        """
        try:
            source_entity = source_dialog.entity

            full_info = await self.client(
                functions.channels.GetFullChannelRequest(source_entity)
            )

            is_broadcast = hasattr(
                source_entity, 'broadcast') and source_entity.broadcast

            print(f"{CYAN}Criando novo canal...")
            new_channel = await self._create_channel(
                new_title,
                new_about,
                full_info,
                is_broadcast
            )

            print(
                f"{GREEN}Novo canal criado: {new_channel.title} (ID: {new_channel.id})")

            if is_public and username:
                await self._set_channel_username(new_channel, username)

            await self._copy_channel_photo(source_entity, new_channel)

            if copy_messages:
                await self._copy_messages(source_entity, new_channel, message_limit)

            return new_channel

        except Exception as e:
            print(f"{RED}Erro durante a clonagem: {e}")
            return None

    async def _create_channel(
        self,
        title: str,
        about: str,
        full_info,
        is_broadcast: bool
    ) -> Any:
        """Cria novo canal/grupo."""
        result = await self.client(functions.channels.CreateChannelRequest(
            title=title,
            about=about or (
                full_info.full_chat.about if full_info.full_chat.about else ""),
            broadcast=is_broadcast,
            megagroup=not is_broadcast
        ))

        return result.chats[0]

    async def _set_channel_username(self, channel, username: str) -> None:
        """
        Define username do canal.

        Args:
            channel: Canal a configurar
            username: Username desejado
        """
        try:
            await self.client(functions.channels.UpdateUsernameRequest(
                channel=channel,
                username=username
            ))
            print(f"{GREEN}Username configurado: @{username}")
        except Exception as e:
            print(f"{RED}Erro ao configurar username: {e}")

    async def _copy_channel_photo(self, source_entity, target_channel) -> None:
        """
        Copia foto do canal.

        Args:
            source_entity: Canal original
            target_channel: Canal de destino
        """
        try:
            if hasattr(source_entity, 'photo') and source_entity.photo:
                print(f"{CYAN}Copiando foto do canal...")
                photo = await self.client.download_profile_photo(source_entity)
                if photo:
                    await self.client(functions.channels.EditPhotoRequest(
                        channel=target_channel,
                        photo=await self.client.upload_file(photo)
                    ))
                    os.remove(photo)
                    print(f"{GREEN}Foto do canal copiada!")
        except Exception as e:
            print(f"{RED}Erro ao copiar foto: {e}")

    async def _copy_messages(self, source_entity, target_channel, limit: int) -> None:
        """
        Copia mensagens do canal original.

        Args:
            source_entity: Canal original
            target_channel: Canal de destino  
            limit: Limite de mensagens
        """
        try:
            print(f"{CYAN}Copiando mensagens...")

            is_protected = await self._check_content_protection(source_entity)
            if is_protected:
                print(f"{YELLOW}⚠️  Canal com proteção de conteúdo detectado")
                print(
                    f"{YELLOW}Apenas texto será copiado, mídia será substituída por descrição")

            messages = await self._collect_messages(source_entity, limit)
            copied_count, skipped_media = await self._process_messages(
                messages, target_channel, is_protected
            )

            print(f"{GREEN}Total de mensagens copiadas: {copied_count}")
            if skipped_media > 0:
                print(
                    f"{YELLOW}Total de mídia protegida substituída: {skipped_media}")

        except Exception as e:
            print(f"{RED}Erro ao copiar mensagens: {e}")

    async def _collect_messages(self, source_entity, limit: int) -> List[Any]:
        """Coleta mensagens do canal original."""
        messages = []
        async for message in self.client.iter_messages(source_entity, limit=limit):
            if message.text or message.media:
                messages.append(message)

        messages.reverse()
        return messages

    async def _process_messages(
        self,
        messages: List[Any],
        target_channel,
        is_protected: bool
    ) -> Tuple[int, int]:
        """Processa e envia mensagens para o canal de destino."""
        copied_count = 0
        skipped_media = 0

        for message in messages:
            try:
                result = await self._send_single_message(
                    message, target_channel, is_protected
                )

                if result['sent']:
                    copied_count += 1
                    if result['media_skipped']:
                        skipped_media += 1

                if copied_count % 10 == 0:
                    print(f"{CYAN}Copiadas {copied_count} mensagens...")
                    if skipped_media > 0:
                        print(
                            f"{YELLOW}Mídia protegida substituída: {skipped_media}")
                    time.sleep(1)

            except Exception as e:
                fallback_result = await self._handle_message_error(
                    message, target_channel, e
                )

                if fallback_result['sent']:
                    copied_count += 1
                    if fallback_result['media_skipped']:
                        skipped_media += 1

        return copied_count, skipped_media

    async def _send_single_message(
        self,
        message,
        target_channel,
        is_protected: bool
    ) -> Dict[str, bool]:
        """Envia uma mensagem individual para o canal de destino."""
        result = {'sent': False, 'media_skipped': False}

        try:
            if message.media and not is_protected:
                if hasattr(message.media, 'webpage'):
                    webpage_text = self._format_webpage_message(message)
                    await self.client.send_message(target_channel, webpage_text)
                    result['sent'] = True
                else:
                    await self.client.send_file(
                        target_channel,
                        message.media,
                        caption=message.text or ""
                    )
                    result['sent'] = True

            elif message.media and is_protected:
                if hasattr(message.media, 'webpage'):
                    webpage_text = self._format_webpage_message(message)
                    await self.client.send_message(target_channel, webpage_text)
                else:
                    media_description = self._get_media_description(message)
                    text_content = f"{message.text or ''}\n\n[📎 Mídia protegida: {media_description}]"
                    await self.client.send_message(target_channel, text_content)
                    result['media_skipped'] = True
                result['sent'] = True

            elif message.text:
                await self.client.send_message(target_channel, message.text)
                result['sent'] = True

        except Exception as e:
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in
                   ["protected chat", "cannot use", "file reference expired",
                    "upload", "download", "timeout", "flood wait"]):

                text_content = self._create_fallback_text(message, str(e))
                await self.client.send_message(target_channel, text_content)
                result['sent'] = True
                result['media_skipped'] = True
            else:
                raise e

        return result

    def _create_fallback_text(self, message, error: str) -> str:
        """Cria texto de fallback para mensagens com erro."""
        media_description = self._get_media_description(message)
        return (f"{message.text or ''}\n\n"
                f"[📎 Arquivo não pode ser copiado: {media_description}]\n"
                f"[ℹ️ Motivo: {error[:100]}...]")

    async def _handle_message_error(
        self,
        message,
        target_channel,
        error: Exception
    ) -> Dict[str, bool]:
        """Trata erros no processamento de mensagens."""
        result = {'sent': False, 'media_skipped': False}
        error_msg = str(error).lower()

        try:
            if any(keyword in error_msg for keyword in
                   ["protected chat", "flood wait", "timeout", "network"]):

                if message.text:
                    await self.client.send_message(target_channel, message.text)
                    result['sent'] = True
                    result['media_skipped'] = bool(message.media)
                elif message.media:
                    media_description = self._get_media_description(message)
                    fallback_text = (f"[📎 Conteúdo não pode ser copiado: {media_description}]\n"
                                     f"[⚠️ Erro: {str(error)[:100]}...]")
                    await self.client.send_message(target_channel, fallback_text)
                    result['sent'] = True
                    result['media_skipped'] = True
            else:
                if message.text or message.media:
                    content = message.text or f"[📎 {self._get_media_description(message)}]"
                    await self.client.send_message(target_channel, content)
                    result['sent'] = True
                    if message.media:
                        result['media_skipped'] = True

        except Exception as fallback_error:
            print(
                f"{RED}Erro crítico ao processar mensagem (pulando): {fallback_error}")

        return result

    async def _check_content_protection(self, entity) -> bool:
        """
        Verifica se o canal/grupo tem proteção de conteúdo.

        Args:
            entity: Entidade do canal/grupo

        Returns:
            True se o canal tiver proteção de conteúdo
        """
        try:
            full_info = await self.client(functions.channels.GetFullChannelRequest(entity))
            if hasattr(full_info.full_chat, 'noforwards'):
                return full_info.full_chat.noforwards
            return False
        except Exception:
            return False

    def _get_media_description(self, message) -> str:
        """
        Gera descrição do tipo de mídia.

        Args:
            message: Mensagem com mídia

        Returns:
            Descrição do tipo de mídia
        """
        if not message.media:
            return "Conteúdo desconhecido"

        media_type = type(message.media).__name__

        if hasattr(message.media, 'photo'):
            return "Foto"
        elif hasattr(message.media, 'document'):
            if hasattr(message.media.document, 'mime_type'):
                mime = message.media.document.mime_type
                if 'video' in mime:
                    return "Vídeo"
                elif 'audio' in mime:
                    return "Áudio"
                elif 'image' in mime:
                    return "Imagem"
                else:
                    return f"Documento ({mime})"
            return "Documento"
        elif 'sticker' in media_type.lower():
            return "Sticker"
        elif 'voice' in media_type.lower():
            return "Mensagem de voz"
        elif 'video' in media_type.lower():
            return "Vídeo"
        else:
            return f"Mídia ({media_type})"

    def _get_channel_type(self, entity) -> str:
        """
        Determina o tipo de canal.

        Args:
            entity: Entidade do canal/grupo

        Returns:
            String com o tipo e cor formatada
        """
        if hasattr(entity, 'broadcast') and entity.broadcast:
            return f"{RED}(Canal)"
        elif hasattr(entity, 'megagroup') and entity.megagroup:
            return f"{GREEN}(Supergrupo)"
        elif hasattr(entity, 'gigagroup') and entity.gigagroup:
            return f"{MAGENTA}(Gigagrupo)"
        else:
            return f"{BLUE}(Grupo)"

    def _format_webpage_message(self, message) -> str:
        """
        Formatar mensagem de webpage.

        Args:
            message: Mensagem com webpage

        Returns:
            Texto formatado da webpage
        """
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

    async def clone_channel_complete(
        self,
        source_dialog,
        new_title: str,
        new_about: str = "",
        is_public: bool = False,
        username: str = "",
        copy_messages: bool = True,
        message_limit: Optional[int] = None,
        download_media: bool = True,
        resume_enabled: bool = True
    ) -> Optional[Any]:
        """
        Clonagem COMPLETA de canal/grupo com todas as mídias e funcionalidade de resume.

        Args:
            source_dialog: Diálogo do canal/grupo original
            new_title: Título do novo canal/grupo
            new_about: Descrição do novo canal/grupo
            is_public: Se o canal deve ser público
            username: Username para canal público
            copy_messages: Se deve copiar mensagens
            message_limit: Limite de mensagens (None = todas)
            download_media: Se deve baixar todas as mídias
            resume_enabled: Se deve salvar progresso para continuar depois

        Returns:
            Canal/grupo clonado ou None se falhar
        """
        try:
            print(GREEN + "🚀 CLONAGEM COMPLETA INICIADA")
            print(CYAN + "Funcionalidades ativas:")
            print(CYAN + "✅ Cópia de mensagens e texto")
            print(CYAN + "✅ Download de todas as mídias (fotos, vídeos, documentos)")
            print(CYAN + "✅ Cópia da foto do perfil")
            print(CYAN + "✅ Preservação da formatação")
            if resume_enabled:
                print(CYAN + "✅ Sistema de resume (continuar de onde parou)")
            print()

            source_entity = source_dialog.entity

            # Carrega checkpoint se resume estiver ativo
            checkpoint_file = f"checkpoint_{source_entity.id}_{new_title.replace(' ', '_')}.json"
            checkpoint_data = {}

            if resume_enabled and os.path.exists(checkpoint_file):
                print(YELLOW + f"📂 Checkpoint encontrado: {checkpoint_file}")
                resume_choice = input(
                    YELLOW + "Continuar de onde parou? (s/n): ").lower()
                if resume_choice.startswith('s'):
                    import json
                    try:
                        with open(checkpoint_file, 'r', encoding='utf-8') as f:
                            checkpoint_data = json.load(f)
                        print(
                            GREEN + f"✅ Resumindo do checkpoint: {checkpoint_data.get('messages_processed', 0)} mensagens processadas")
                    except Exception as e:
                        print(RED + f"Erro ao carregar checkpoint: {e}")
                        checkpoint_data = {}

            # Se não há canal salvo no checkpoint, cria um novo
            if 'channel_id' not in checkpoint_data:
                print(f"{CYAN}Obtendo informações do canal original...")
                full_info = await self.client(
                    functions.channels.GetFullChannelRequest(source_entity)
                )

                is_broadcast = hasattr(
                    source_entity, 'broadcast') and source_entity.broadcast

                print(f"{CYAN}Criando novo canal...")
                new_channel = await self._create_channel(
                    new_title,
                    new_about,
                    full_info,
                    is_broadcast
                )

                print(
                    f"{GREEN}✅ Novo canal criado: {new_channel.title} (ID: {new_channel.id})")

                if is_public and username:
                    await self._set_channel_username(new_channel, username)

                await self._copy_channel_photo(source_entity, new_channel)

                # Salva no checkpoint
                checkpoint_data['channel_id'] = new_channel.id
                checkpoint_data['channel_title'] = new_channel.title
                checkpoint_data['messages_processed'] = 0

            else:
                print(
                    f"{YELLOW}📂 Usando canal do checkpoint: {checkpoint_data['channel_title']}")
                # Busca o canal existente
                new_channel = await self.client.get_entity(checkpoint_data['channel_id'])

            # Copia mensagens com download de mídia e sistema de checkpoint
            if copy_messages:
                await self._copy_messages_complete(
                    source_entity,
                    new_channel,
                    message_limit,
                    download_media,
                    checkpoint_file if resume_enabled else None,
                    checkpoint_data
                )

            # Remove checkpoint se completou com sucesso
            if resume_enabled and os.path.exists(checkpoint_file):
                try:
                    os.remove(checkpoint_file)
                    print(GREEN + "✅ Clonagem completa! Checkpoint removido.")
                except:
                    pass

            print(GREEN + "🎉 CLONAGEM COMPLETA FINALIZADA COM SUCESSO!")
            return new_channel

        except Exception as e:
            print(RED + f"❌ Erro durante a clonagem completa: {e}")
            return None

    async def _copy_messages_complete(
        self,
        source_entity,
        target_channel,
        limit: Optional[int],
        download_media: bool = True,
        checkpoint_file: Optional[str] = None,
        checkpoint_data: Dict[str, Any] = None
    ) -> None:
        """
        Copia mensagens com download completo de mídia e sistema de checkpoint.
        """
        import json
        if checkpoint_data is None:
            checkpoint_data = {}

        try:
            print(f"{CYAN}📋 Coletando mensagens do canal original...")

            is_protected = await self._check_content_protection(source_entity)
            if is_protected:
                print(f"{YELLOW}⚠️  Canal com proteção de conteúdo detectado")
                print(f"{YELLOW}Estratégia: Download direto + descrições detalhadas")

            # Coleta mensagens
            messages = []
            total_messages = 0
            async for message in self.client.iter_messages(source_entity, limit=limit):
                if message.text or message.media:
                    messages.append(message)
                total_messages += 1

            messages.reverse()  # Processa na ordem cronológica

            print(f"{GREEN}📊 Total de mensagens coletadas: {len(messages)}")

            # Processa mensagens a partir do checkpoint
            start_index = checkpoint_data.get('messages_processed', 0)
            copied_count = start_index
            skipped_media = 0
            downloaded_media = 0

            print(
                f"{CYAN}🔄 Processando mensagens (iniciando do índice {start_index})...")

            for i, message in enumerate(messages[start_index:], start_index):
                try:
                    result = await self._send_message_with_media_download(
                        message,
                        target_channel,
                        is_protected,
                        download_media
                    )

                    if result['sent']:
                        copied_count += 1
                        if result['media_downloaded']:
                            downloaded_media += 1
                        elif result['media_skipped']:
                            skipped_media += 1

                    # Salva checkpoint a cada 10 mensagens
                    if checkpoint_file and copied_count % 10 == 0:
                        checkpoint_data['messages_processed'] = i + 1
                        with open(checkpoint_file, 'w', encoding='utf-8') as f:
                            json.dump(checkpoint_data, f,
                                      ensure_ascii=False, indent=2)

                    # Progresso
                    if copied_count % 25 == 0:
                        print(
                            f"{CYAN}📈 Progresso: {copied_count}/{len(messages)} mensagens")
                        if downloaded_media > 0:
                            print(
                                f"{GREEN}📥 Mídias baixadas: {downloaded_media}")
                        if skipped_media > 0:
                            print(
                                f"{YELLOW}⏭️  Mídias protegidas: {skipped_media}")

                    # Pequena pausa para evitar rate limiting
                    if copied_count % 5 == 0:
                        await asyncio.sleep(0.5)

                except Exception as e:
                    print(f"{RED}❌ Erro na mensagem {i}: {e}")
                    continue

            print(f"{GREEN}✅ Processamento completo!")
            print(f"{GREEN}📊 Estatísticas finais:")
            print(f"{GREEN}  • Mensagens copiadas: {copied_count}")
            print(f"{GREEN}  • Mídias baixadas: {downloaded_media}")
            if skipped_media > 0:
                print(f"{YELLOW}  • Mídias protegidas substituídas: {skipped_media}")

        except Exception as e:
            print(f"{RED}❌ Erro ao copiar mensagens completas: {e}")

    async def _send_message_with_media_download(
        self,
        message,
        target_channel,
        is_protected: bool,
        download_media: bool = True
    ) -> Dict[str, bool]:
        """
        Envia mensagem com download completo de mídia quando possível.
        """
        result = {'sent': False, 'media_downloaded': False,
                  'media_skipped': False}

        try:
            if message.media and download_media:
                # Tenta baixar e reenviar a mídia
                try:
                    if not is_protected:
                        # Para canais sem proteção, baixa a mídia diretamente
                        media_file = await message.download_media()
                        if media_file:
                            await self.client.send_file(
                                target_channel,
                                media_file,
                                caption=message.text or ""
                            )
                            # Remove arquivo temporário
                            if os.path.exists(media_file):
                                os.remove(media_file)
                            result['media_downloaded'] = True
                        else:
                            # Fallback: envia como texto com descrição
                            await self._send_media_as_text(message, target_channel)
                            result['media_skipped'] = True
                    else:
                        # Para canais protegidos, envia descrição detalhada
                        await self._send_protected_media_description(message, target_channel)
                        result['media_skipped'] = True

                    result['sent'] = True

                except Exception as media_error:
                    print(f"{YELLOW}⚠️  Erro no download de mídia: {media_error}")
                    # Fallback: envia como texto
                    await self._send_media_as_text(message, target_channel)
                    result['sent'] = True
                    result['media_skipped'] = True

            elif message.text:
                # Mensagem apenas de texto
                await self.client.send_message(target_channel, message.text)
                result['sent'] = True

            return result

        except Exception as e:
            print(f"{RED}❌ Erro ao enviar mensagem: {e}")
            return result

    async def _send_media_as_text(self, message, target_channel) -> None:
        """Envia mídia como descrição textual."""
        try:
            media_type = "Mídia"
            if hasattr(message.media, 'photo'):
                media_type = "📸 Foto"
            elif hasattr(message.media, 'document'):
                if hasattr(message.media.document, 'mime_type'):
                    if 'video' in message.media.document.mime_type:
                        media_type = "🎥 Vídeo"
                    elif 'audio' in message.media.document.mime_type:
                        media_type = "🎵 Áudio"
                    else:
                        media_type = "📄 Documento"

            text = f"{media_type}"
            if message.text:
                text += f"\n\n{message.text}"

            await self.client.send_message(target_channel, text)

        except Exception as e:
            print(f"{RED}Erro ao enviar mídia como texto: {e}")

    async def _send_protected_media_description(self, message, target_channel) -> None:
        """Envia descrição detalhada para mídia protegida."""
        try:
            description = "🔒 CONTEÚDO PROTEGIDO (não é possível baixar)\n"

            if hasattr(message.media, 'photo'):
                description += "📸 Tipo: Imagem/Foto"
            elif hasattr(message.media, 'document'):
                doc = message.media.document
                if hasattr(doc, 'mime_type'):
                    if 'video' in doc.mime_type:
                        description += "🎥 Tipo: Vídeo"
                        if hasattr(doc, 'attributes'):
                            for attr in doc.attributes:
                                if hasattr(attr, 'duration'):
                                    duration_min = attr.duration // 60
                                    duration_sec = attr.duration % 60
                                    description += f"\n⏱️ Duração: {duration_min}:{duration_sec:02d}"
                    elif 'audio' in doc.mime_type:
                        description += "🎵 Tipo: Áudio"
                    else:
                        description += "📄 Tipo: Documento"

                if hasattr(doc, 'size'):
                    size_mb = doc.size / (1024 * 1024)
                    description += f"\n📊 Tamanho: {size_mb:.1f} MB"

            if message.text:
                description += f"\n\n💬 Legenda/Texto:\n{message.text}"

            await self.client.send_message(target_channel, description)

        except Exception as e:
            print(f"{RED}Erro ao enviar descrição de mídia protegida: {e}")
