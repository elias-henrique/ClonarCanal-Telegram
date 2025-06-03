"""Manipuladores otimizados para opções do menu principal."""

import asyncio
from typing import Optional

from .telegram_client import TCloneClient
from .cloner import ChannelCloner
from .colors import RED, GREEN, BLUE, YELLOW, CYAN, MAGENTA, RESET


class MenuHandlers:
    """Gerenciador de handlers do menu principal."""
    
    def __init__(self, client: TCloneClient) -> None:
        self.client = client
        self.cloner = ChannelCloner(client.client)
    
    async def handle_connect(self) -> bool:
        """Handler para conectar e listar canais disponíveis."""
        print(GREEN + f"Conectando ao Telegram com API ID: {self.client.api_id}")
        
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
            target_input = input(YELLOW + "Digite o username ou ID do usuário: ")
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
                YELLOW + f"Selecione o canal/grupo (0-{len(channels_and_groups)-1}): "
            ))
            
            if choice < 0 or choice >= len(channels_and_groups):
                print(RED + "Opção inválida!")
                return False
            
            source_dialog = channels_and_groups[choice]
            print(GREEN + f"Canal/Grupo selecionado: {source_dialog.name}")
            
            clone_config = self._get_clone_configuration(source_dialog.name)
            
            new_channel = await self.cloner.clone_channel(
                source_dialog, 
                clone_config['title'], 
                clone_config['about'],
                clone_config['is_public'], 
                clone_config['username'], 
                clone_config['copy_messages'], 
                clone_config['message_limit']
            )
            
            return self._handle_clone_result(new_channel, clone_config)
            
        except ValueError:
            print(RED + "Por favor, digite um número válido!")
            return False
    
    def _get_clone_configuration(self, source_name: str) -> dict:
        """Obtém configurações para clonagem."""
        new_title = input(
            YELLOW + f"Nome do novo canal (padrão: 'Clone de {source_name}'): "
        ) or f"Clone de {source_name}"
        
        new_about = input(YELLOW + "Descrição do novo canal: ")
        
        is_public = input(YELLOW + "Canal público? (s/n): ").lower().startswith('s')
        username = ""
        if is_public:
            username = input(YELLOW + "Username do canal (sem @): ")
        
        copy_messages_input = input(YELLOW + "Copiar mensagens? (s/n, padrão: s): ").lower()
        copy_messages = not copy_messages_input or copy_messages_input.startswith('s')
        
        message_limit = 100
        if copy_messages:
            try:
                message_limit = int(
                    input(YELLOW + "Quantas mensagens copiar? (padrão: 100): ") or "100"
                )
            except ValueError:
                message_limit = 100
        
        return {
            'title': new_title,
            'about': new_about,
            'is_public': is_public,
            'username': username,
            'copy_messages': copy_messages,
            'message_limit': message_limit
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
    
    async def handle_advanced_clone(self) -> bool:
        """Handler para clonagem avançada com configurações especiais."""
        print(GREEN + "Clonagem Avançada - Em desenvolvimento")
        print(YELLOW + "Esta funcionalidade será implementada em versões futuras")
        return True
    
    async def handle_supergroup_clone(self) -> bool:
        """Handler para clonagem completa de supergrupo."""
        print(GREEN + "🚀 Clonagem Completa de Supergrupo")
        print(YELLOW + "Clona supergrupo e todos os canais relacionados")
        
        try:
            supergroups = await self.cloner.list_supergroups_only()
            
            if not supergroups:
                print(RED + "Nenhum supergrupo encontrado!")
                return False
            
            return await self._process_supergroup_cloning(supergroups)
            
        except Exception as e:
            print(RED + f"Erro durante a clonagem: {e}")
            return False
    
    async def _process_supergroup_cloning(self, supergroups) -> bool:
        """Processa clonagem completa de supergrupo."""
        try:
            choice = int(input(
                YELLOW + f"Selecione o supergrupo (0-{len(supergroups)-1}): "
            ))
            
            if choice < 0 or choice >= len(supergroups):
                print(RED + "Opção inválida!")
                return False
            
            source_dialog = supergroups[choice]
            print(GREEN + f"Supergrupo selecionado: {source_dialog.name}")
            
            if not self._confirm_supergroup_operation():
                return False
            
            new_base_title = input(
                YELLOW + f"Nome base (padrão: 'Clone de {source_dialog.name}'): "
            ) or f"Clone de {source_dialog.name}"
            
            return await self._execute_supergroup_cloning(source_dialog, new_base_title)
            
        except ValueError:
            print(RED + "Por favor, digite um número válido!")
            return False
    
    def _confirm_supergroup_operation(self) -> bool:
        """Confirma operação de clonagem de supergrupo."""
        print(YELLOW + "⚠️  ATENÇÃO: Esta operação irá:")
        print(YELLOW + "   • Clonar o supergrupo principal")
        print(YELLOW + "   • Buscar e clonar todos os canais relacionados")
        print(YELLOW + "   • Copiar mensagens de todos os canais")
        print(YELLOW + "   • Pode demorar vários minutos")
        
        confirm = input(YELLOW + "Continuar? (s/n): ").lower()
        
        if not confirm.startswith('s'):
            print(CYAN + "Operação cancelada pelo usuário")
            return False
        
        return True
    
    async def _execute_supergroup_cloning(
        self, source_dialog, new_base_title: str
    ) -> bool:
        """Executa clonagem completa e exibe resultados."""
        print(CYAN + "🔄 Iniciando clonagem completa...")
        print(CYAN + "Este processo pode demorar vários minutos...")
        
        results = await self.cloner.clone_supergroup_with_channels(
            source_dialog, new_base_title
        )
        
        self._display_cloning_results(results)
        
        return bool(results['main_group'] or results['channels'])
    
    def _display_cloning_results(self, results: dict) -> None:
        """Exibe relatório detalhado dos resultados."""
        print(GREEN + "\n" + "="*50)
        print(GREEN + "✅ RELATÓRIO DE CLONAGEM COMPLETA")
        print(GREEN + "="*50)
        
        if results['main_group']:
            print(GREEN + f"✅ Supergrupo principal: {results['main_group'].title}")
        else:
            print(RED + "❌ Falha ao clonar supergrupo principal")
        
        if results['channels']:
            print(GREEN + f"✅ Canais clonados: {len(results['channels'])}")
            for i, channel in enumerate(results['channels'], 1):
                print(CYAN + f"   {i}. {channel.title}")
        else:
            print(YELLOW + "⚠️  Nenhum canal foi clonado")
        
        if results['errors']:
            print(RED + f"❌ Erros encontrados: {len(results['errors'])}")
            for error in results['errors']:
                print(RED + f"   • {error}")
        
        print(GREEN + "="*50)
        
        if results['main_group'] or results['channels']:
            print(GREEN + "🎉 Clonagem completa finalizada!")
        else:
            print(RED + "❌ Nenhum item foi clonado com sucesso")
