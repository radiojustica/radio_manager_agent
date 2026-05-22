"""
Script para criar um atalho de Área de Trabalho (Desktop) para o Omni Core V2.
Usa PowerShell nativo para evitar dependência de bibliotecas externas adicionais.
"""
import os
import subprocess
from pathlib import Path

def main():
    try:
        # Pega o caminho absoluto da pasta raiz do projeto e do START_OMNI.bat
        base_path = Path(__file__).resolve().parent.parent
        bat_path = base_path / "START_OMNI.bat"
        
        # Garante que o arquivo BAT existe
        if not bat_path.exists():
            print(f"[ERRO] Nao foi possivel encontrar {bat_path}")
            return
            
        # Comando PowerShell para gerar o atalho no Desktop do usuário
        ps_command = f"""
        $WshShell = New-Object -ComObject WScript.Shell
        $Shortcut = $WshShell.CreateShortcut("$Home\\Desktop\\Omni Core V2.lnk")
        $Shortcut.TargetPath = "{bat_path}"
        $Shortcut.WorkingDirectory = "{base_path}"
        $Shortcut.IconLocation = "shell32.dll,135" # Ícone de globo/web moderno
        $Shortcut.Description = "Inicializa ou foca o Dashboard do Omni Core V2"
        $Shortcut.Save()
        """
        
        # Executa o comando via PowerShell do Windows
        subprocess.run(["powershell", "-Command", ps_command], check=True)
        print("[OK] Atalho 'Omni Core V2' criado com sucesso na Area de Trabalho!")
    except Exception as e:
        print(f"[ERRO] Erro inesperado ao criar o atalho: {e}")

if __name__ == "__main__":
    main()
