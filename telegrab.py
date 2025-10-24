"""Telegrabber - Sistema de clonagem de canais Telegram otimizado."""

from lib.menu_handlers import MenuHandlers
from lib.telegram_client import TelegrabberClient
from lib.colors import (
    print_banner, print_menu, RED, GREEN, YELLOW, CYAN
)
from lib.config import Config
import asyncio
import glob
import sys
from pathlib import Path
from typing import List, Optional

sys.path.append(str(Path(__file__).parent / 'lib'))


class TelegrabberMessenger:
    """Sistema principal para clonagem de canais do Telegram."""

    DEFAULT_API_HASH = "ea2ad87dd4e60b4e7c24b52a8dc41b9a"
    API_ID_MAP = {1: 27858, 2: 27858, 3: 27858, 4: 27858, 5: 27858}

    def __init__(self):
        self.config = Config()
        self.client: Optional[TelegrabberClient] = None
        self.menu_handlers: Optional[MenuHandlers] = None

    def get_session_files(self) -> List[str]:
        """Retorna lista de arquivos de sessão disponíveis."""
        return glob.glob("*.session")

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

        # Usa API ID e HASH padrão; não é necessário ler o .session via SQLite
        api_id = 27858
        print(GREEN + f"Usando API ID: {api_id}")
        api_hash = self.DEFAULT_API_HASH

        self.client = TelegrabberClient(session_name, api_id, api_hash)
        self.menu_handlers = MenuHandlers(self.client, self.config)
        return True

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
        self.client = TelegrabberClient(session_name, api_id, api_hash)
        self.menu_handlers = MenuHandlers(self.client, self.config)

        return True

    # Removido: exibição de informações da sessão ativa por não ser necessária

    def get_user_choice(self) -> str:
        """Obtém e retorna escolha do usuário do menu."""
        print_menu()
        return input(YELLOW + "Escolha uma opção: ").strip()

    async def handle_menu_choice(self, choice: str) -> bool:
        """Processa escolha do menu e executa ação correspondente."""
        try:
            if not self.menu_handlers:
                print(RED + "Menu não inicializado.")
                return True
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
                await self.menu_handlers.handle_download_media()
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
    app = TelegrabberMessenger()

    try:
        asyncio.run(app.run())
    except KeyboardInterrupt:
        print(YELLOW + "\nPrograma interrompido")
    except Exception as e:
        print(RED + f"Erro crítico: {e}")


if __name__ == "__main__":
    main()
