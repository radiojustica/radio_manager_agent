import os
import sys
from datetime import datetime

# Adiciona o diretório base ao sys.path para importar os módulos locais
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from director.auditor import ProgrammingAuditor

def run_historical_audit():
    auditor = ProgrammingAuditor()
    hoje = datetime.now().strftime("%Y-%m-%d")
    log_path = f"D:\\RADIO\\LOG ZARARADIO\\{hoje}.log"
    
    print(f"[{datetime.now()}] Iniciando Auditoria Histórica de Execução...")
    print(f"Analisando log real: {log_path}")
    
    violations = auditor.audit_execution_log(log_path)
    
    if not violations:
        print("\n✅ SUCESSO ARTÍSTICO: O que tocou hoje respeitou todas as regras de rodízio!")
    elif "error" in violations[0]:
        print(f"\n❌ ERRO: {violations[0]['error']}")
    else:
        print(f"\n⚠️ FORAM DETECTADAS {len(violations)} VIOLAÇÕES DE RODÍZIO NO AR HOJE:")
        # Agrupa por artista para facilitar a leitura
        resumo = {}
        for v in violations:
            resumo[v['artista']] = resumo.get(v['artista'], 0) + 1
            print(f"  - {v['msg']} ({v['musica']})")
        
        print("\n--- RESUMO DE REPETIÇÕES INDEVIDAS ---")
        for art, qtd in resumo.items():
            print(f"  {art}: {qtd} vezes acima do permitido")

if __name__ == "__main__":
    run_historical_audit()


