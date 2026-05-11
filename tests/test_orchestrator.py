import sys
import os
from pathlib import Path

# Adiciona o diretório raiz ao sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from worker_manager import worker_manager_instance

def test_orchestrator_initialization():
    print("Iniciando teste do Orquestrador...")
    wm = worker_manager_instance
    
    # Inicia o orquestrador
    wm.start_orchestrator()
    
    if wm.scheduler.running:
        print("✅ Scheduler está rodando.")
    else:
        print("❌ Scheduler NÃO está rodando.")
        return
    
    jobs = wm.scheduler.get_jobs()
    print(f"Total de jobs agendados: {len(jobs)}")
    
    expected_jobs = [
        'worker_guardian_watchdog',
        'worker_guardian_high_freq',
        'worker_curadoria',
        'worker_weather',
        'worker_sync',
        'worker_audit',
        'worker_daily_playlist',
        'butt_reconnect',
        'reboot_block_daily'
    ]
    
    found_jobs = [job.id for job in jobs]
    for ej in expected_jobs:
        if ej in found_jobs:
            print(f"  ✅ Job encontrado: {ej}")
        else:
            print(f"  ❌ Job ausente: {ej}")
            
    # Para o orquestrador
    wm.stop_orchestrator()
    if not wm.scheduler.running:
        print("✅ Scheduler parado com sucesso.")
    else:
        print("❌ Scheduler falhou ao parar.")

if __name__ == "__main__":
    test_orchestrator_initialization()
