
import sys
import unittest
from unittest.mock import patch, MagicMock

# Adiciona o diretório atual ao sys.path para garantir que os módulos locais sejam encontrados
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

class TestHeadlessExecution(unittest.TestCase):
    def test_launcher_import_without_gui_libs(self):
        """Testa se o core.launcher pode ser importado mesmo sem tkinter/pystray."""
        # Mocking sys.modules to simulate missing libraries
        with patch.dict('sys.modules', {'tkinter': None, 'pystray': None, 'gui.console': None, 'gui.tray': None}):
            try:
                # Se o import falhar aqui, nossa refatoração falhou
                import core.launcher
                # Recarrega para garantir que os mocks sejam aplicados se já foi importado
                import importlib
                importlib.reload(core.launcher)
                print("[OK] core.launcher importado com sucesso sem bibliotecas de GUI.")
            except ImportError as e:
                self.fail(f"Falha ao importar core.launcher sem bibliotecas de GUI: {e}")

    @patch('director.orchestrator.system_orchestrator')
    def test_run_app_fallback_to_headless(self, mock_orchestrator):
        """Testa se run_app cai para modo headless quando as libs de GUI falham."""
        # Não vamos usar importlib.reload aqui para evitar problemas com numpy
        # Em vez disso, vamos apenas mockar o tkinter ANTES de chamar run_app
        import core.launcher
        
        with patch.dict('sys.modules', {'tkinter': None}):
            # Executa run_app
            core.launcher.run_app()
            
            # Verifica se os métodos do orquestrador foram chamados
            mock_orchestrator.bootstrap.assert_called_once()
            mock_orchestrator.start_core.assert_called_once()
            mock_orchestrator.run_headless.assert_called_once()
            print("[OK] run_app redirecionou corretamente para modo headless na ausência de Tkinter.")

if __name__ == "__main__":
    unittest.main()
