"""Módulo de configuração do sistema TClone."""

import json
import os
from typing import Optional


class Config:
    """Gerenciador de configurações da aplicação."""
    
    def __init__(self, config_file: str = 'config.json') -> None:
        self.config_file = config_file
        self.phone: str = ""
        self.max_file_size: int = 50 * 1024 * 1024  # 50MB default
        self.temp_dir: str = "temp"
        self.allow_all_extensions: bool = True
        
        self.load_config()
    
    def load_config(self) -> None:
        """Carrega configurações do arquivo JSON."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    
                self.phone = config_data.get('phone', "")
                self.max_file_size = config_data.get('max_file_size', 50 * 1024 * 1024)
                self.temp_dir = config_data.get('temp_dir', "temp")
                self.allow_all_extensions = config_data.get('allow_all_extensions', True)
                
        except (json.JSONDecodeError, FileNotFoundError, KeyError, ValueError) as e:
            print(f"Erro ao carregar config.json: {e}")
    
    def save_config(self) -> None:
        """Salva configurações no arquivo JSON."""
        config_data = {
            'phone': self.phone,
            'max_file_size': self.max_file_size,
            'temp_dir': self.temp_dir,
            'allow_all_extensions': self.allow_all_extensions
        }
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Erro ao salvar configuração: {e}")
