"""
Omni Core V2 - Inicializador Principal
Suporta modo Headless via argumento --headless.
"""

import sys
import logging
from pathlib import Path
from director.orchestrator import system_orchestrator

def main():
    # Detecta modo de operação
    args = sys.argv[1:]
    is_headless = "--headless" in args

    try:
        if is_headless:
            # Inicializa apenas o backend (Headless)
            system_orchestrator.bootstrap()
            system_orchestrator.start_core()
            system_orchestrator.run_headless()
        else:
            # Inicializa com interface gráfica (Padrão)
            from core.launcher import run_app
            run_app()

    except KeyboardInterrupt:
        print("\n[Main] Encerrando sistema...")
        sys.exit(0)
    except Exception as e:
        import traceback
        print(f"\n[Main] ERRO CRÍTICO: {e}")
        traceback.print_exc()
        input("\nPressione Enter para sair...")
        sys.exit(1)

if __name__ == "__main__":
    main()
