import os
import subprocess
import sys
import logging
from pathlib import Path

# Configuração de Log para o Build
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("build_process.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("OmniCore.Build")

def build_frontend():
    """
    Executa a compilação do frontend React/Vite usando 'npm run build' na pasta 'frontend'.
    """
    logger.info("Iniciando compilação do frontend React (Vite)...")
    frontend_dir = Path(__file__).resolve().parent / "frontend"
    
    # Verifica se package.json existe no frontend
    if not (frontend_dir / "package.json").exists():
        logger.warning("Diretório do frontend ou 'package.json' não encontrado. Pulando build do frontend.")
        return True
        
    try:
        # Primeiro, executa npm install se node_modules não existir
        if not (frontend_dir / "node_modules").exists():
            logger.info("Pasta 'node_modules' não encontrada no frontend. Executando 'npm install'...")
            subprocess.run(["npm", "install"], cwd=str(frontend_dir), shell=True, check=True)
            logger.info("✓ Dependências do frontend instaladas com sucesso.")

        # Executa o build
        logger.info("Executando 'npm run build' no frontend...")
        subprocess.run(["npm", "run", "build"], cwd=str(frontend_dir), shell=True, check=True)
        logger.info("✅ Frontend compilado com sucesso!")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Erro ao compilar o frontend: {e}")
        # Se a pasta 'dist' já existe de builds anteriores, podemos emitir um aviso e prosseguir
        dist_dir = frontend_dir / "dist"
        if dist_dir.exists():
            logger.warning("⚠️ Usando o build do frontend existente em 'frontend/dist' (anterior).")
            return True
        return False
    except FileNotFoundError:
        logger.error("❌ Node.js/npm não está instalado ou não foi encontrado no PATH do sistema!")
        dist_dir = frontend_dir / "dist"
        if dist_dir.exists():
            logger.warning("⚠️ Usando o build do frontend existente em 'frontend/dist' (anterior).")
            return True
        return False
    except Exception as e:
        logger.error(f"🚨 Erro inesperado durante o build do frontend: {e}")
        return False

def build():
    """
    Constrói o executável do Omni Core V2 usando PyInstaller.
    Inclui tratamento de erros detalhado e logs de saída.
    """
    logger.info("Iniciando processo de build do Omni Core V2...")
    
    # Compila o frontend primeiro para garantir que os arquivos estáticos estejam atualizados
    if not build_frontend():
        logger.error("Falha crítica na compilação do frontend e nenhum build anterior foi encontrado. Abortando build.")
        return False
        
    # Caminho do ponto de entrada
    entry_point = "main.py"
    if not os.path.exists(entry_point):
        logger.error(f"Ponto de entrada '{entry_point}' não encontrado!")
        return False

    # Comando do PyInstaller
    # --onefile: gera um único executável
    # --noconsole: não abre janela de console (útil para GUI/Tray)
    # --hidden-import: garante que dependências dinâmicas sejam incluídas
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--noconsole", # Oculta a janela de terminal do console no executável de produção
        "--name", "omni_core",
        "--clean",
        "--add-data", "config;config",
        "--add-data", "core;core",
        "--add-data", "frontend/dist;frontend/dist",
        entry_point
    ]

    try:
        logger.info(f"Executando comando: {' '.join(cmd)}")
        
        # Executa o subprocesso capturando stdout e stderr
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            universal_newlines=True
        )

        # Loga a saída em tempo real
        if process.stdout:
            for line in process.stdout:
                line = line.strip()
                if line:
                    logger.info(f"[PyInstaller] {line}")

        process.wait()

        if process.returncode == 0:
            logger.info("✅ Build concluído com sucesso!")
            
            # Pós-build: copia as configurações necessárias para rodar o executável
            try:
                import shutil
                dist_dir = Path(__file__).resolve().parent / "dist"
                src_env = Path(__file__).resolve().parent / ".env"
                src_config = Path(__file__).resolve().parent / "config"
                
                if src_env.exists():
                    shutil.copy(src_env, dist_dir / ".env")
                    logger.info("✓ Copiado .env para a pasta dist/ de forma bem-sucedida")
                    
                if src_config.exists():
                    dist_config = dist_dir / "config"
                    dist_config.mkdir(parents=True, exist_ok=True)
                    for f_name in ["settings.json", "settings.example.json"]:
                        src_f = src_config / f_name
                        if src_f.exists():
                            shutil.copy(src_f, dist_config / f_name)
                            logger.info(f"✓ Copiado config/{f_name} para dist/config/ de forma bem-sucedida")
            except Exception as ce:
                logger.warning(f"⚠️ Erro ao copiar configurações pós-build para dist/: {ce}")
                
            return True
        else:
            logger.error(f"❌ PyInstaller encerrou com código de erro: {process.returncode}")
            return False

    except subprocess.SubprocessError as se:
        logger.critical(f"💥 Erro de Subprocesso durante o build: {se}")
        return False
    except Exception as e:
        logger.critical(f"🚨 Erro inesperado durante o build: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = build()
    sys.exit(0 if success else 1)
