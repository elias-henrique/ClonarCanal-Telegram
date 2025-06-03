"""TClone Messenger - Sistema de clonagem de canais Telegram otimizado."""

import asyncio
import glob
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Optional

sys.path.append(str(Path(__file__).parent / 'lib'))

from lib.config import Config
from lib.colors import (
    print_banner, print_menu, RED, GREEN, YELLOW, CYAN, RESET
)
from lib.telegram_client import TCloneClient
from lib.menu_handlers import MenuHandlers


class TCloneMessenger:
    """Sistema principal para clonagem de canais do Telegram."""
    
    DEFAULT_API_HASH = "ea2ad87dd4e60b4e7c24b52a8dc41b9a"
    API_ID_MAP = {1: 27858, 2: 27858, 3: 27858, 4: 27858, 5: 27858}
    
    def __init__(self):
        self.config = Config()
        self.client: Optional[TCloneClient] = None
        self.menu_handlers: Optional[MenuHandlers] = None
    
    def get_session_files(self) -> List[str]:
        """Retorna lista de arquivos de sessão disponíveis."""
        return glob.glob("*.session")
    
    def extract_credentials_from_session(
        self, session_file: str
    ) -> Dict[str, Optional[int]]:
        """Extrai credenciais API do arquivo de sessão SQLite."""
        try:
            with sqlite3.connect(session_file) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [row[0] for row in cursor.fetchall()]
                
                if 'sessions' in tables:
                    cursor.execute("SELECT dc_id FROM sessions LIMIT 1;")
                    result = cursor.fetchone()
                    if result:
                        dc_id = result[0]
                        return {'api_id': self.API_ID_MAP.get(dc_id, 27858)}
                        
            return {'api_id': None}
            
        except Exception as e:
            print(f"{RED}Erro ao ler arquivo de sessão: {e}")
            return {'api_id': None}
    
    def initialize(self) -> bool:
        """Inicializa aplicação com sessão existente ou nova configuração."""
        print_banner()
        
        session_files = self.get_session_files()
        if session_files:
            return self._initialize_with_existing_session(session_files[0])
        
        return self._initialize_with_new_credentials()
    
    def _initialize_with_existing_session(self, session_file: str) -> bool:
        """Inicializa com sessão existente."""
        session_name = session_file.replace('.session', '')
        print(GREEN + f"Arquivo de sessão encontrado: {session_file}")
        print(YELLOW + "Usando sessão existente...")
        
        session_info = self.extract_credentials_from_session(session_file)
        
        if session_info['api_id']:
            api_id = session_info['api_id']
            print(GREEN + f"Usando API ID: {api_id}")
            api_hash = self.DEFAULT_API_HASH
            
            self.client = TCloneClient(session_name, api_id, api_hash)
            self.menu_handlers = MenuHandlers(self.client)
            return True
        
        return False
    
    def _initialize_with_new_credentials(self) -> bool:
        """Inicializa com novas credenciais da API."""
        print(YELLOW + "Nenhuma sessão válida encontrada.")
        print(YELLOW + "Configure as credenciais da API do Telegram:")
        
        try:
            api_id = input("API ID: ").strip()
            api_hash = input("API Hash: ").strip()
            
            if not api_id or not api_hash:
                print(RED + "API ID e Hash são obrigatórios!")
                input("Pressione Enter para sair...")
                return False
            
            api_id = int(api_id)
            
        except ValueError:
            print(RED + "API ID deve ser um número!")
            input("Pressione Enter para sair...")
            return False
        except KeyboardInterrupt:
            print(YELLOW + "\nOperação cancelada")
            return False
        
        session_name = 'session'
        print(YELLOW + "Criando nova sessão...")
        
        self.client = TCloneClient(session_name, api_id, api_hash)
        self.menu_handlers = MenuHandlers(self.client)
        
        return True
    
    async def get_session_info(self) -> None:
        """Obtém e exibe informações da sessão ativa."""
        try:
            session_data = await self.client.get_session_info()
            if session_data:
                first_name = session_data.get('first_name', 'Usuário')
                username = session_data.get('username', 'N/A')
                phone = session_data.get('phone', 'N/A')
                user_id = session_data.get('user_id', 'N/A')
                
                print(GREEN + f"Conectado como: {first_name} (@{username})")
                print(CYAN + f"Telefone: {phone}")
                print(CYAN + f"ID do usuário: {user_id}")
            else:
                print(RED + "Falha ao obter informações da sessão")
        except Exception as e:
            print(RED + f"Erro na conexão: {e}")
    
    def get_user_choice(self) -> str:
        """Obtém e retorna escolha do usuário do menu."""
        print_menu()
        return input(YELLOW + "Escolha uma opção: ").strip()
    
    async def handle_menu_choice(self, choice: str) -> bool:
        """Processa escolha do menu e executa ação correspondente."""
        try:
            if choice == "0":
                print(CYAN + "Saindo...")
                return False
            elif choice == "1":
                await self.menu_handlers.handle_connect()
            elif choice == "2":
                await self.menu_handlers.handle_send_message()
            elif choice == "3":
                await self.menu_handlers.handle_clone_channel()
            elif choice == "4":
                await self.menu_handlers.handle_advanced_clone()
            else:
                print(RED + "Opção inválida!")
            
            input("\nPressione Enter para continuar...")
            return True
            
        except Exception as e:
            print(RED + f"Erro ao processar opção: {e}")
            input("Pressione Enter para continuar...")
            return True
    
    async def run(self) -> None:
        """Executa loop principal da aplicação."""
        if not self.initialize():
            return
        
        await self.get_session_info()
        
        while True:
            try:
                choice = self.get_user_choice()
                
                if not await self.handle_menu_choice(choice):
                    break
                    
            except KeyboardInterrupt:
                print(YELLOW + "\nInterrompido pelo usuário")
                break
            except Exception as e:
                print(RED + f"Erro inesperado: {e}")
                input("Pressione Enter para continuar...")
        
        if self.client:
            await self.client.disconnect()
        
        print(CYAN + "Programa finalizado.")


def main() -> None:
    """Função principal do sistema."""
    app = TCloneMessenger()
    
    try:
        asyncio.run(app.run())
    except KeyboardInterrupt:
        print(YELLOW + "\nPrograma interrompido")
    except Exception as e:
        print(RED + f"Erro crítico: {e}")


if __name__ == "__main__":
    main()
