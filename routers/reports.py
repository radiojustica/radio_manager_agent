from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os
import glob
from worker_manager import worker_manager_instance

router = APIRouter(prefix="/api/reports", tags=["Relatórios"])

REPORTS_DIR = "reports"

@router.get("/list")
def list_reports():
    """Lista todos os relatórios disponíveis no diretório de reports."""
    if not os.path.exists(REPORTS_DIR):
        return []
    
    files = glob.glob(os.path.join(REPORTS_DIR, "*.*"))
    report_list = []
    for f in files:
        stat = os.stat(f)
        report_list.append({
            "filename": os.path.basename(f),
            "size_kb": round(stat.st_size / 1024, 2),
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat()
        })
    
    # Ordenar por data (mais recentes primeiro)
    return sorted(report_list, key=lambda x: x["created_at"], reverse=True)

@router.get("/download/{filename}")
def download_report(filename: str):
    """Faz o download de um arquivo de relatório específico."""
    path = os.path.join(REPORTS_DIR, filename)
    # Segurança básica para evitar path traversal
    if not os.path.abspath(path).startswith(os.path.abspath(REPORTS_DIR)):
        raise HTTPException(status_code=403, detail="Acesso negado.")
    
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Relatório não encontrado.")
    
    return FileResponse(path, filename=filename)

@router.post("/generate")
def trigger_report_generation():
    """Dispara manualmente o ReportWorker para gerar novos relatórios agora."""
    worker = worker_manager_instance.get_worker("ReportWorker")
    if not worker:
        raise HTTPException(status_code=404, detail="ReportWorker não registrado.")
    
    result = worker_manager_instance.run_cycle("ReportWorker")
    return result

from datetime import datetime # Necessário para o list_reports
