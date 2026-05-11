"""
Script de build para gerar EXE do Omni Core V2 com PyInstaller.
Cria um executável único com todos os recursos necessários.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

BASE_PATH = Path(__file__).resolve().parent
DIST_PATH = BASE_PATH / "dist"
BUILD_PATH = BASE_PATH / "build"

def clean_build():
    """Remove builds anteriores."""
    for path in [DIST_PATH, BUILD_PATH, BASE_PATH / "omni_core.spec"]:
        if path.exists():
            shutil.rmtree(path) if path.is_dir() else path.unlink()
    print("✓ Limpeza de builds anteriores concluída")

def build_exe():
    """Gera o EXE usando PyInstaller em subprocesso."""
    args = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(BASE_PATH / "main.py"),
        "--name=omni_core",
        "--onefile",
        "--console",
        "--add-data=" + str(BASE_PATH / "config") + os.pathsep + "config",
        "--add-data=" + str(BASE_PATH / "resources") + os.pathsep + "resources",
        "--hidden-import=win32gui",
        "--hidden-import=win32process",
        "--hidden-import=win32con",
        "--hidden-import=pystray",
        "--hidden-import=librosa",
        "--distpath=" + str(DIST_PATH),
        "--workpath=" + str(BUILD_PATH),
        "--clean",
    ]

    icon_path = BASE_PATH / "resources" / "icon.ico"
    if icon_path.exists():
        args.insert(6, "--icon=" + str(icon_path))

    result = subprocess.run(args, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError("PyInstaller build failed")

    print("✓ EXE gerado em dist/omni_core.exe")

def create_version_file():
    """Cria arquivo de versão para atualização."""
    version_file = DIST_PATH / "VERSION"
    version_file.write_text("1.0.0\n")
    
    # Cria hash do executável
    import hashlib
    exe_path = DIST_PATH / "omni_core.exe"
    if exe_path.exists():
        with open(exe_path, 'rb') as f:
            hash_value = hashlib.md5(f.read()).hexdigest()
        (DIST_PATH / "omni_core.md5").write_text(hash_value)
    
    print("✓ Arquivo de versão criado")

def main():
    """Executa o build completo."""
    print("=== BUILD OMNI CORE V2 ===\n")
    clean_build()
    build_exe()
    create_version_file()
    print("\n✓ Build concluído com sucesso!")
    print(f"   Executável: {DIST_PATH / 'omni_core.exe'}")

if __name__ == "__main__":
    main()
