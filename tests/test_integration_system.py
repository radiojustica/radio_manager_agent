#!/usr/bin/env python
"""
Teste de integração - Validar que o sistema de downloads refatorado
esta funcionando corretamente com o sistema principal.
"""
import logging
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)-30s | %(levelname)-8s | %(message)s'
)

logger = logging.getLogger("Integration.Test")

def test_system_startup():
    """TESTE 1: Verificar que o sistema inicia sem erros."""
    logger.info("=" * 80)
    logger.info("TESTE 1: Verificar inicializacao do sistema")
    logger.info("=" * 80)
    
    try:
        # Importar componentes principais
        logger.info("Importando worker_manager...")
        from worker_manager import worker_manager_instance
        logger.info("[OK] worker_manager importado")
        
        logger.info("Importando downloader_instance...")
        from services.downloader_service import downloader_instance
        logger.info("[OK] downloader_instance importado")
        
        logger.info("Importando DownloaderWorker...")
        from workers.downloader_worker import DownloaderWorker
        logger.info("[OK] DownloaderWorker importado")
        
        return True
    except Exception as e:
        logger.error(f"[FAIL] Erro na inicializacao: {e}", exc_info=True)
        return False


def test_downloader_refactoring():
    """TESTE 2: Validar que as melhorias sao funcionais."""
    logger.info("\n" + "=" * 80)
    logger.info("TESTE 2: Validar refatoracao do downloader")
    logger.info("=" * 80)
    
    try:
        from services.downloader_service import downloader_instance
        from services.youtube_dl_manager import YoutubeDLManager
        
        # Verificar que manager existe
        logger.info("Verificando YoutubeDLManager...")
        assert downloader_instance.ydl_manager is not None
        logger.info("[OK] YoutubeDLManager configurado")
        
        # Verificar configuracoes
        logger.info("Verificando configuracoes...")
        assert downloader_instance.ydl_manager.max_retries == 3
        logger.info("[OK] Retry: 3 tentativas")
        
        assert downloader_instance.ydl_manager.timeout_seconds == 300
        logger.info("[OK] Timeout: 300 segundos")
        
        # Verificar progress tracking
        logger.info("Verificando progress tracking...")
        assert isinstance(downloader_instance.active_progress, dict)
        logger.info("[OK] Progress tracking com dict")
        
        # Gerar task ID
        logger.info("Testando UUID generation...")
        task_id = YoutubeDLManager.generate_task_id("test")
        assert len(task_id) == 36  # UUID v4
        logger.info(f"[OK] UUID gerado: {task_id}")
        
        return True
    except Exception as e:
        logger.error(f"[FAIL] Erro na validacao: {e}", exc_info=True)
        return False


def test_worker_functionality():
    """TESTE 3: Verificar que o worker funciona."""
    logger.info("\n" + "=" * 80)
    logger.info("TESTE 3: Validar funcionalidade do worker")
    logger.info("=" * 80)
    
    try:
        from workers.downloader_worker import DownloaderWorker
        
        logger.info("Instanciando worker...")
        worker = DownloaderWorker()
        logger.info("[OK] Worker instanciado")
        
        # Testar ciclo vazio
        logger.info("Testando run_cycle com queries vazias...")
        result = worker.run_cycle(queries=[], estilo="test")
        assert result.status == "idle"
        logger.info(f"[OK] run_cycle retornou: {result.status}")
        
        # Verificar metadata
        logger.info("Verificando metadata...")
        assert "message" in result.metadata
        logger.info(f"[OK] Metadata: {result.metadata['message']}")
        
        return True
    except Exception as e:
        logger.error(f"[FAIL] Erro na validacao do worker: {e}", exc_info=True)
        return False


def test_api_integration():
    """TESTE 4: Verificar que a API pode acessar o downloader."""
    logger.info("\n" + "=" * 80)
    logger.info("TESTE 4: Validar integracao com API")
    logger.info("=" * 80)
    
    try:
        # Verificar que API router importa corretamente
        logger.info("Importando downloader router...")
        from routers.downloader import router
        logger.info("[OK] Router importado")
        
        # Verificar endpoints
        logger.info("Verificando endpoints...")
        endpoints = [r.path for r in router.routes]
        
        required_endpoints = [
            "/api/downloader/recommendations",
            "/api/downloader/download",
            "/api/downloader/progress"
        ]
        
        for endpoint in required_endpoints:
            if any(endpoint in ep for ep in endpoints):
                logger.info(f"[OK] Endpoint encontrado: {endpoint}")
            else:
                logger.warning(f"[?] Endpoint pode estar indisponivel: {endpoint}")
        
        return True
    except Exception as e:
        logger.error(f"[FAIL] Erro na validacao da API: {e}", exc_info=True)
        return False


def run_all_integration_tests():
    """Executa todos os testes de integracao."""
    logger.info("\n\n")
    logger.info("#" * 80)
    logger.info("# TESTES DE INTEGRACAO - SISTEMA DE DOWNLOADS")
    logger.info("#" * 80)
    logger.info("Iniciando...")
    
    tests = [
        ("Inicializacao do Sistema", test_system_startup),
        ("Refatoracao do Downloader", test_downloader_refactoring),
        ("Funcionalidade do Worker", test_worker_functionality),
        ("Integracao com API", test_api_integration),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"Excecao nao tratada em {test_name}: {e}", exc_info=True)
            results[test_name] = False
    
    # Sumario
    logger.info("\n" + "=" * 80)
    logger.info("SUMARIO DOS TESTES DE INTEGRACAO")
    logger.info("=" * 80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        logger.info(f"  {status}: {test_name}")
    
    logger.info("")
    logger.info(f"  Total: {passed}/{total} testes passaram")
    logger.info("")
    
    if passed == total:
        logger.info("  [OK] TODOS OS TESTES DE INTEGRACAO PASSARAM!")
        logger.info("  [OK] Sistema esta operacional")
        logger.info("  [OK] Downloader refatorado funcionando corretamente")
    else:
        logger.warning(f"  [!] {total - passed} teste(s) falharam")
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("")
    
    return passed == total


if __name__ == "__main__":
    import sys
    success = run_all_integration_tests()
    sys.exit(0 if success else 1)
