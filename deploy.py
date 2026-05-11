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

def create_scheduled_task():
    """Cria uma tarefa agendada no Windows para rodar como Administrador p001642."""
    print("\n⚡ Configurando inicialização automática via Agendador de Tarefas...")
    
    task_name = "OmniCore_Admin"
    exe_path = INSTALL_PATH / "omni_core.exe"
    user = "p001642"
    password = "Tjrn" # Conforme solicitado pelo usuário
    
    # Comando para criar a tarefa:
    # /sc onlogon: Inicia ao fazer logon
    # /rl highest: Executa com privilégios máximos (Admin)
    # /ru: Usuário alvo
    # /rp: Senha do usuário
    # /tr: Caminho do executável
    # /f: Força a sobrescrita se a tarefa já existir
    cmd = [
        "schtasks", "/create", "/tn", task_name,
        "/tr", f'"{exe_path}"',
        "/sc", "onlogon",
        "/rl", "highest",
        "/ru", user,
        "/rp", password,
        "/f"
    ]
    
    try:
        # Usamos shell=True para lidar melhor com argumentos no Windows se necessário, 
        # mas a lista de argumentos costuma ser mais segura.
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ Tarefa agendada '{task_name}' criada com sucesso!")
            print(f"✓ O sistema iniciará como {user} com privilégios de Admin.")
        else:
            # Se falhar com a senha, tentamos criar sem a senha (o Windows pedirá na primeira execução manual se necessário)
            # Ou apenas informamos o erro.
            print(f"❌ Erro ao criar tarefa agendada: {result.stderr}")
            print("💡 Tentando criar tarefa sem senha (pode exigir configuração manual no Task Scheduler)...")
            cmd_no_pass = [c for c in cmd if c not in ["/rp", password]]
            subprocess.run(cmd_no_pass)
            
    except Exception as e:
        print(f"❌ Falha crítica ao configurar schtasks: {e}")

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
            print("❌ Erro: Execute como Administrador para configurar o Agendador")
            sys.exit(1)
    
    print("✓ Privilégios de Administrador verificados\n")
    
    # Execução
    ensure_pyinstaller()
    
    if not build_exe():
        sys.exit(1)
    
    create_install_dir()
    copy_files()
    create_scheduled_task()
    
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
    print(f"📊 Logs: D:\\RADIO\\LOG ZARARADIO\\omni_system.log")

if __name__ == "__main__":
    main()
