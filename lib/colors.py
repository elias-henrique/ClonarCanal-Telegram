"""Módulo de cores e interface para terminal."""

import colorama
from colorama import Fore, Style

colorama.init()

RED = Fore.RED
GREEN = Fore.GREEN
BLUE = Fore.BLUE
YELLOW = Fore.YELLOW
CYAN = Fore.CYAN
MAGENTA = Fore.MAGENTA
WHITE = Fore.WHITE
RESET = Style.RESET_ALL


def print_banner() -> None:
    """Exibe banner principal da aplicação."""
    print(RED + "=" * 50)
    print(RED + "=" * 15 + BLUE + " TClone Messenger " + RED + "=" * 15)
    print(RED + "=" * 50)
    print(CYAN + "Welcome to TClone Messenger")
    print(GREEN + "Sistema de Clonagem de Canais Telegram")
    print(MAGENTA + "Versão 2.0 - Otimizada")
    print(RED + "=" * 50)
    print(RESET)


def print_menu() -> None:
    """Exibe menu principal de opções."""
    print(MAGENTA + "Opções:")
    print(GREEN + "1. Conectar ao Telegram")
    print(YELLOW + "2. Enviar Mensagem")
    print(CYAN + "3. Clonar Canal/Chat Individual")
    print(BLUE + "4. Clonagem Avançada (com configurações)")
    print(MAGENTA + "5. 🚀 Clonar Supergrupo COMPLETO")
    print(CYAN + "6. 📥 Baixar mídias (fotos e vídeos)")
    print(WHITE + "0. Sair")
    print("")
