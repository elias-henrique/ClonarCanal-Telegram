"""Módulo de cores e interface para terminal.

Melhora o visual do banner e do menu inicial.
"""

import os
import re
import shutil

import colorama
from colorama import Fore, Style
try:
  
    from wcwidth import wcswidth as _wcswidth
except Exception:
    def _wcswidth(s: str) -> int:
        return len(s)

colorama.init(autoreset=True)

RED = Fore.RED
GREEN = Fore.GREEN
BLUE = Fore.BLUE
YELLOW = Fore.YELLOW
CYAN = Fore.CYAN
MAGENTA = Fore.MAGENTA
WHITE = Fore.WHITE

RESET = Style.RESET_ALL
BRIGHT = Style.BRIGHT
DIM = Style.DIM

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(s: str) -> str:
    return _ANSI_RE.sub("", s)


def _visible_width(s: str) -> int:
    """Calcula a largura visível (desconsidera ANSI e considera unicode).

    Usa wcwidth para contabilizar caracteres de largura dupla.
    """
    try:
        return max(0, _wcswidth(_strip_ansi(s)))
    except Exception:
        return len(_strip_ansi(s))


def _truncate_visible(s: str, max_cols: int) -> str:
    """Corta a string para caber em max_cols colunas, preservando ANSI.

    Percorre caractere a caractere; quando encontra uma sequência ANSI, copia
    inteira sem impactar a largura visível.
    """
    if max_cols <= 0:
        return ""

    out: list[str] = []
    cols = 0
    i = 0
    n = len(s)
    while i < n:
        if s[i] == "\x1b":
            m = _ANSI_RE.match(s, i)
            if m:
                out.append(m.group(0))
                i = m.end()
                continue
        ch = s[i]
        w = _wcswidth(ch)
      
        if w < 0:
            w = 0
        if cols + w > max_cols:
            break
        out.append(ch)
        cols += w
        i += 1
    return "".join(out)


def _term_width(min_w: int = 60, max_w: int = 100) -> int:
    """Obtém a largura do terminal, com limites sensatos."""
    try:
        width = shutil.get_terminal_size(fallback=(80, 20)).columns
    except Exception:
        width = 80
    return max(min_w, min(max_w, width))


def _frame_line(width: int) -> str:
    return f"┌{'─' * (width - 2)}┐"


def _frame_bottom(width: int) -> str:
    return f"└{'─' * (width - 2)}┘"


def _frame_row(text: str, width: int) -> str:
  
    inner_w = width - 2
    content = _truncate_visible(text, inner_w)
    padding = max(0, inner_w - _visible_width(content))
    return f"│{content}{' ' * padding}│"


def _gradient_text(text: str) -> str:
    """Aplica um leve 'degradê' alternando CYAN/BLUE nos caracteres."""
    if not text:
        return ""
    colors = [CYAN, BLUE]
    out = []
    idx = 0
    for ch in text:
        if ch == " ":
            out.append(ch)
        else:
            out.append(colors[idx % len(colors)] + BRIGHT + ch)
            idx += 1
    return "".join(out) + RESET


def clear_screen() -> None:
    """Limpa a tela do terminal."""
    os.system("cls" if os.name == "nt" else "clear")


def print_banner() -> None:
    """Exibe banner principal da aplicação (estilizado)."""

    clear_screen()
    width = _term_width()

    title = "Telegrabber"
    subtitle = "Sistema de Clonagem de Canais Telegram"
    help_line = "Pegue seu API ID e Hash em: https://my.telegram.org/"

  
    print(MAGENTA + _frame_line(width) + RESET)

  
    centered_title = title.center(width - 2)
    print(MAGENTA + "│" + RESET +
          _gradient_text(centered_title) + MAGENTA + "│" + RESET)

  
    print(MAGENTA + _frame_row("".center(width - 2, " "), width) + RESET)

  
    print(MAGENTA + "│" + RESET + BRIGHT + GREEN +
          subtitle.center(width - 2) + RESET + MAGENTA + "│" + RESET)

  
    print(MAGENTA + "│" + RESET + DIM + WHITE +
          help_line.center(width - 2) + RESET + MAGENTA + "│" + RESET)

  
    print(MAGENTA + _frame_bottom(width) + RESET)
    print("")


def print_menu() -> None:
    """Exibe menu principal de opções (com moldura e alinhamento)."""

    width = _term_width()

    options = [
        ("1", GREEN, "Conectar ao Telegram", "🔌"),
        ("2", YELLOW, "Enviar Mensagem", "✉️ "),
        ("3", CYAN, "Clonar Canal/Chat Individual (Completo + Resume)", "�"),
        ("4", RED, "Baixar mídias (fotos e vídeos)", "📥"),
        ("0", WHITE, "Sair", "⏻"),
    ]

    header = "Opções"
    print(MAGENTA + _frame_line(width) + RESET)
    print(MAGENTA + "│" + RESET + BRIGHT + WHITE +
          header.center(width - 2) + RESET + MAGENTA + "│" + RESET)
    print(MAGENTA + _frame_row("".center(width - 2, " "), width) + RESET)

    for key, color, label, icon in options:
      
        line_text = f" {BRIGHT}{color}[{key}]{RESET}{color} • {label}"
      
        inner_w = width - 2
        content = _truncate_visible(line_text, inner_w)
        pad = max(0, inner_w - _visible_width(content))
        print(MAGENTA + "│" + RESET + content +
              (" " * pad) + MAGENTA + "│" + RESET)

    print(MAGENTA + _frame_bottom(width) + RESET)
    print("")
