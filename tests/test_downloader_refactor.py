#!/usr/bin/env python
"""
Script de teste da refatoração do sistema de downloads.
Valida sintaxe, imports, e comportamento básico.
"""
import sys
import logging

# Configurar logging
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TestDownloader")

def test_imports():
    """Testa se todos os módulos podem ser importados."""
    logger.info("=" * 60)
    logger.info("TESTE 1: Validando imports")
    logger.info("=" * 60)
    
    try:
        from services.youtube_dl_manager import YoutubeDLManager
        logger.info("✓ YoutubeDLManager importado")
    except Exception as e:
        logger.error(f"✗ Erro ao importar YoutubeDLManager: {e}")
        return False
    
    try:
        from services.downloader_service import DownloaderService
        logger.info("✓ DownloaderService importado")
    except Exception as e:
        logger.error(f"✗ Erro ao importar DownloaderService: {e}")
        return False
    
    try:
        from workers.downloader_worker import DownloaderWorker
        logger.info("✓ DownloaderWorker importado")
    except Exception as e:
        logger.error(f"✗ Erro ao importar DownloaderWorker: {e}")
        return False
    
    return True


def test_ydl_manager():
    """Testa a classe YoutubeDLManager."""
    logger.info("\n" + "=" * 60)
    logger.info("TESTE 2: YoutubeDLManager")
    logger.info("=" * 60)
    
    try:
        from services.youtube_dl_manager import YoutubeDLManager
        
        manager = YoutubeDLManager()
        logger.info(f"✓ YoutubeDLManager instanciado")
        
        # Testar método get_base_options
        opts = manager.get_base_options()
        assert isinstance(opts, dict), "get_base_options deve retornar dict"
        assert "format" in opts, "Opcões deve incluir 'format'"
        assert opts["socket_timeout"] == 300, "Timeout padrão deve ser 300"
        logger.info(f"✓ get_base_options(): {len(opts)} opções")
        
        # Testar clean_filename
        dirty = "Song (Official Video) [Remix] <Banned>"
        clean = YoutubeDLManager.clean_filename(dirty)
        logger.info(f"✓ clean_filename('{dirty}') = '{clean}'")
        
        # Testar generate_task_id
        task_id = YoutubeDLManager.generate_task_id("test query")
        assert len(task_id) == 36, "UUID deve ter 36 caracteres"  # UUID v4
        logger.info(f"✓ generate_task_id() = {task_id}")
        
        return True
    except Exception as e:
        logger.error(f"✗ Erro em YoutubeDLManager: {e}", exc_info=True)
        return False


def test_downloader_service():
    """Testa a classe DownloaderService."""
    logger.info("\n" + "=" * 60)
    logger.info("TESTE 3: DownloaderService")
    logger.info("=" * 60)
    
    try:
        from services.downloader_service import DownloaderService
        
        service = DownloaderService()
        logger.info(f"✓ DownloaderService instanciado")
        logger.info(f"  Target dir: {service.target_dir}")
        
        # Testar clean_filename (delegado ao manager)
        dirty = "Artista - Música (Lyrics)"
        clean = service.clean_filename(dirty)
        logger.info(f"✓ clean_filename('{dirty}') = '{clean}'")
        
        # Testar estrutura de progress
        assert isinstance(service.active_progress, dict), "active_progress deve ser dict"
        logger.info(f"✓ active_progress inicializado")
        
        return True
    except Exception as e:
        logger.error(f"✗ Erro em DownloaderService: {e}", exc_info=True)
        return False


def test_downloader_worker():
    """Testa a classe DownloaderWorker."""
    logger.info("\n" + "=" * 60)
    logger.info("TESTE 4: DownloaderWorker")
    logger.info("=" * 60)
    
    try:
        from workers.downloader_worker import DownloaderWorker
        
        worker = DownloaderWorker()
        logger.info(f"✓ DownloaderWorker instanciado")
        logger.info(f"  Proactive limit: {worker.proactive_limit}")
        
        # Testar run_cycle com queries vazias (deve retornar idle)
        result = worker.run_cycle(queries=[], estilo="test")
        logger.info(f"✓ run_cycle([]) retornou status: {result.status}")
        
        return True
    except Exception as e:
        logger.error(f"✗ Erro em DownloaderWorker: {e}", exc_info=True)
        return False


def main():
    """Executa todos os testes."""
    logger.info("\n🔍 Iniciando testes de refatoração do sistema de downloads\n")
    
    results = {
        "Imports": test_imports(),
        "YoutubeDLManager": test_ydl_manager(),
        "DownloaderService": test_downloader_service(),
        "DownloaderWorker": test_downloader_worker(),
    }
    
    logger.info("\n" + "=" * 60)
    logger.info("RESUMO DOS TESTES")
    logger.info("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✓ PASSOU" if result else "✗ FALHOU"
        logger.info(f"{status}: {name}")
    
    logger.info(f"\nResultado: {passed}/{total} testes passaram")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
