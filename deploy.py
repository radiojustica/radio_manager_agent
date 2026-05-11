"""
Deploy Script - Instala e configura Omni Core V2 para execução automática.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
import winreg

BASE_PATH = Path(__file__).resolve().parent
DIST_PATH = BASE_PATH / "dist"
INSTALL_PATH = Path("C:\\Program Files\\OmniCore")
SHORTCUT_PATH = Path(os.getenv('APPDATA')) / "Microsoft\\Windows\\Start Menu\\Programs\\Startup"

def ensure_pyinstaller():
    """Instala PyInstaller se não estiver disponível."""
    try:
        import PyInstaller
        print("✓ PyInstaller já instalado")
    except ImportError:
        print("📦 Instalando PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        print("✓ PyInstaller instalado")

def build_exe():
    """Constrói o EXE."""
    print("\n🔨 Compilando EXE...")
    result = subprocess.run([sys.executable, str(BASE_PATH / "build.py")], cwd=str(BASE_PATH))
    if result.returncode != 0:
        print("❌ Build falhou")
        return False
    print("✓ EXE compilado com sucesso")
    return True

def create_install_dir():
    """Cria diretório de instalação."""
    print(f"\n📁 Criando diretório {INSTALL_PATH}...")
    INSTALL_PATH.mkdir(parents=True, exist_ok=True)
    print(f"✓ Diretório criado")

def copy_files():
    """Copia arquivos para diretório de instalação."""
    print("\n📋 Copiando arquivos...")
    
    files_to_copy = [
        ("dist/omni_core.exe", "omni_core.exe"),
        ("dist/VERSION", "VERSION"),
        ("dist/code.md5", "code.md5"),
        ("config", "config"),
    ]
    
    for src, dst in files_to_copy:
        src_path = BASE_PATH / src
        dst_path = INSTALL_PATH / dst
        
        if src_path.is_file():
            shutil.copy2(src_path, dst_path)
            print(f"  ✓ {dst}")
        elif src_path.is_dir():
            if dst_path.exists():
                shutil.rmtree(dst_path)
            shutil.copytree(src_path, dst_path)
            print(f"  ✓ {dst}/")

def create_startup_shortcut():
    """Cria atalho na pasta de Startup para iniciar automaticamente."""
    print("\n⚡ Configurando inicialização automática...")
    
    shortcut_path = SHORTCUT_PATH / "OmniCore.bat"
    exe_path = INSTALL_PATH / "omni_core.exe"
    
    bat_content = f"""@echo off
REM Omni Core V2 Startup
cd /d "{INSTALL_PATH}"
"{exe_path}" %*
"""
    
    shortcut_path.write_text(bat_content)
    print(f"✓ Atalho criado: {shortcut_path}")

def add_registry_entry():
    """Adiciona entrada no Registro para fácil desinstalação."""
    print("\n🔐 Registrando aplicação...")
    
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\OmniCore"
        reg_key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, key_path)
        
        exe_path = INSTALL_PATH / "omni_core.exe"
        winreg.SetValueEx(reg_key, "DisplayName", 0, winreg.REG_SZ, "Omni Core V2")
        winreg.SetValueEx(reg_key, "DisplayVersion", 0, winreg.REG_SZ, "1.0.0")
        winreg.SetValueEx(reg_key, "InstallLocation", 0, winreg.REG_SZ, str(INSTALL_PATH))
        winreg.SetValueEx(reg_key, "UninstallString", 0, winreg.REG_SZ, str(exe_path))
        winreg.CloseKey(reg_key)
        
        print("✓ Aplicação registrada")
    except Exception as e:
        print(f"⚠️  Erro ao registrar: {e} (continuando...)")

def main():
    """Executa o deploy completo."""
    print("""
    ╔══════════════════════════════════════╗
    ║  DEPLOY OMNI CORE V2                 ║
    ║  Build + Instalação Automática       ║
    ╚══════════════════════════════════════╝
    """)
    
    # Verificar privilégios de admin
    if os.name == 'nt':
        import ctypes
        if not ctypes.windll.shell32.IsUserAnAdmin():
            print("❌ Erro: Execute como Administrador")
            sys.exit(1)
    
    print("✓ Privilégios de Administrador verificados\n")
    
    # Execução
    ensure_pyinstaller()
    
    if not build_exe():
        sys.exit(1)
    
    create_install_dir()
    copy_files()
    create_startup_shortcut()
    
    try:
        add_registry_entry()
    except:
        pass
    
    print("\n" + "="*40)
    print("✅ DEPLOY CONCLUÍDO COM SUCESSO!")
    print("="*40)
    print(f"\n📍 Instalado em: {INSTALL_PATH}")
    print(f"🚀 Inicie com: {INSTALL_PATH / 'omni_core.exe'}")
    print(f"⚙️  Auto-início configurado via Startup")
    print(f"\n💡 Atualizações automáticas: A cada 1 hora")
    print(f"📊 Logs: D:\\RADIO\\LOG ZAZAZADIO\\omni_system.log")

if __name__ == "__main__":
    main()
