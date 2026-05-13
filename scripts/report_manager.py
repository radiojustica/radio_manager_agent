import os
import csv
import logging
from datetime import datetime, timedelta
from pathlib import Path
from core.reward import RewardStore

logger = logging.getLogger("OmniCore.ReportManager")

class ReportManager:
    def __init__(self, output_dir: str = "reports"):
        self.output_dir = output_dir
        self.reward_store = RewardStore()
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_worker_audit_csv(self, days: int = 7) -> str:
        """Gera um CSV detalhado de todas as execuções de workers no período."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        filename = f"Worker_Audit_{end_date.strftime('%Y%m%d')}.csv"
        path = os.path.join(self.output_dir, filename)
        
        history = self.reward_store.history(limit=2000) # Pega um histórico razoável
        
        # Filtrar por data
        filtered_history = []
        for entry in history:
            try:
                ts = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                # Remover timezone para comparação se necessário, ou manter isoformat
                if ts.replace(tzinfo=None) >= start_date:
                    filtered_history.append(entry)
            except:
                filtered_history.append(entry)

        keys = ["timestamp", "worker", "score", "status", "violations", "message"]
        
        try:
            with open(path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=keys, delimiter=';')
                writer.writeheader()
                
                for entry in reversed(filtered_history):
                    status = "FAIL" if entry.get("violations") else "OK"
                    message = entry.get("metadata", {}).get("message", "")
                    if not message and entry.get("metadata", {}).get("error"):
                        message = entry["metadata"]["error"]
                    
                    writer.writerow({
                        "timestamp": entry["timestamp"],
                        "worker": entry["worker"],
                        "score": entry["score"],
                        "status": status,
                        "violations": "|".join(entry.get("violations", [])),
                        "message": message
                    })
            return path
        except Exception as e:
            logger.error(f"Erro ao gerar CSV de auditoria: {e}")
            return ""

    def generate_worker_performance_csv(self) -> str:
        """Gera um CSV de resumo de performance por worker (Ranking)."""
        filename = f"Worker_Performance_Summary_{datetime.now().strftime('%Y%m%d')}.csv"
        path = os.path.join(self.output_dir, filename)
        
        workers_data = self.reward_store.summary()
        keys = ["worker", "score_total", "cycles", "avg_efficiency", "last_run"]
        
        try:
            with open(path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=keys, delimiter=';')
                writer.writeheader()
                
                for name, data in workers_data.items():
                    cycles = data.get("cycles", 0)
                    score = data.get("score_total", 0)
                    avg = score / cycles if cycles > 0 else 0
                    last = data.get("last_result", {}).get("timestamp", "N/A")
                    
                    writer.writerow({
                        "worker": name,
                        "score_total": score,
                        "cycles": cycles,
                        "avg_efficiency": f"{avg:.2f}",
                        "last_run": last
                    })
            return path
        except Exception as e:
            logger.error(f"Erro ao gerar CSV de performance: {e}")
            return ""

    def run_weekly_pipeline(self):
        """Executa a geração de todos os relatórios semanais."""
        logger.info("Iniciando pipeline de relatórios semanais...")
        audit_path = self.generate_worker_audit_csv(7)
        perf_path = self.generate_worker_performance_csv()
        
        # Tenta integrar com o gerador de logs da rádio se ele existir
        try:
            from scripts.weekly_csv_generator import WeeklyCSVGenerator
            # Assumindo caminhos padrão do sistema
            gen = WeeklyCSVGenerator(r"D:\RADIO\LOG ZARARADIO", self.output_dir)
            music_path = gen.generate_report(7)
            logger.info(f"Relatório de música gerado: {music_path}")
        except Exception as e:
            logger.warning(f"Não foi possível gerar relatório de música (ZaraRadio): {e}")

        return {
            "audit": audit_path,
            "performance": perf_path,
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    mgr = ReportManager()
    print(mgr.run_weekly_pipeline())
