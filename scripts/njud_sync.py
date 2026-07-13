import os
import shutil
import logging
import json
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("OmniCore.NjudSync")

DAY_MAP = {
    0: "SEGUNDA", 1: "TERCA", 2: "QUARTA", 3: "QUINTA", 4: "SEXTA", 5: "SABADO", 6: "DOMINGO"
}

class NjudSync:
    def __init__(self, source_dir=None, target_dir=None):
        config = self._load_config()
        self.source_drive_dir = source_dir or config.get("grade", {}).get("pasta_drive_njud", r"D:\SERVIDOR\DRIVE\RADIO TJRN CONTEÚDO\NOT JUDICIARIO (5 MIN)")
        self.target_local_dir = target_dir or config.get("grade", {}).get("pasta_njud_raiz", r"D:\SERVIDOR\PROGRAMAS\JORNAL")
        
        os.makedirs(self.target_local_dir, exist_ok=True)
        for day in ["SEGUNDA", "TERCA", "QUARTA", "QUINTA", "SEXTA"]:
            os.makedirs(os.path.join(self.target_local_dir, day), exist_ok=True)

    def _load_config(self):
        config_path = Path(__file__).resolve().parent.parent / "config" / "settings.json"
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Erro ao carregar settings.json no NjudSync: {e}")
        return {}

    def parse_njud_info(self, filepath):
        """Filtra arquivos indesejados e extrai dados do arquivo."""
        filename = os.path.basename(filepath)
        
        # Ignora arquivos parciais (OFFs de locução, spots parciais de Notas ou bruto)
        for skip_word in ["OFF", "BRUTO", "PILOTO", "COPIA", "CÓPIA", "ROTEIRO", "APRESENTA", "GRAVAÇÃO", "GRAVACAO"]:
            if skip_word in filename.upper():
                return None
                
        if not filename.lower().endswith(".mp3"):
            return None
            
        # Padrão 1: njud...DD_MM[_YYYY]
        import re
        match = re.search(r"njud[-_\s]+\d+[-_\s]+(\d{2})[-_\s](\d{2})(?:[-_\s](\d{4}))?", filename.lower())
        if match:
            day_str, month_str, year_str = match.groups()
            try:
                mtime = os.path.getmtime(filepath)
                mtime_dt = datetime.fromtimestamp(mtime)
                year = int(year_str) if year_str else mtime_dt.year
                dt = datetime(year, int(month_str), int(day_str))
                return {
                    "date": dt,
                    "filename": filename,
                    "filepath": filepath,
                    "day_name": DAY_MAP[dt.weekday()]
                }
            except: pass

        # Padrão 2: NJUD {num} {DD-MM}.mp3
        match2 = re.search(r"njud\s+\d+\s+(\d{2})-(\d{2})", filename.lower())
        if match2:
            day_str, month_str = match2.groups()
            try:
                mtime = os.path.getmtime(filepath)
                mtime_dt = datetime.fromtimestamp(mtime)
                dt = datetime(mtime_dt.year, int(month_str), int(day_str))
                return {
                    "date": dt,
                    "filename": filename,
                    "filepath": filepath,
                    "day_name": DAY_MAP[dt.weekday()]
                }
            except: pass

        return None

    def sync(self) -> dict:
        """Sincroniza as Notícias do Judiciário (NJUD) do Drive para as pastas locais por dia da semana."""
        logger.info(f"Iniciando espelhamento de jornais (NJUD): {self.source_drive_dir} -> {self.target_local_dir}")
        
        if not os.path.exists(self.source_drive_dir):
            return {"success": False, "error": f"Pasta de origem do NJUD não encontrada: {self.source_drive_dir}"}

        try:
            # 1. Varre recursivamente e encontra o arquivo mais recente para cada dia da semana
            newest_files_by_day = {}
            total_scanned = 0
            total_matched = 0
            
            for root, dirs, files in os.walk(self.source_drive_dir):
                for f in files:
                    total_scanned += 1
                    filepath = os.path.join(root, f)
                    info = self.parse_njud_info(filepath)
                    if not info:
                        continue
                        
                    total_matched += 1
                    day = info["day_name"]
                    
                    # Queremos apenas dias úteis para a programação
                    if day not in ["SEGUNDA", "TERCA", "QUARTA", "QUINTA", "SEXTA"]:
                        continue
                        
                    # Se não houver arquivo para o dia, ou se este for mais recente do que o já mapeado
                    if day not in newest_files_by_day or info["date"] > newest_files_by_day[day]["date"]:
                        newest_files_by_day[day] = info

            logger.info(f"Varredura NJUD concluída. Arquivos escaneados: {total_scanned}, Válidos: {total_matched}")
            
            updated_days = []
            
            # 2. Substituição atômica local
            for day, info in newest_files_by_day.items():
                target_dir = os.path.join(self.target_local_dir, day)
                target_file = os.path.join(target_dir, "JORNAL_NJUD.mp3")
                meta_file = os.path.join(target_dir, "JORNAL_NJUD.json")
                
                # Verifica se o arquivo final e o JSON de metadados já existem no destino
                if os.path.exists(target_file) and os.path.exists(meta_file):
                    try:
                        with open(meta_file, "r", encoding="utf-8") as f_meta:
                            meta_data = json.load(f_meta)
                            if meta_data.get("filename") == info["filename"]:
                                # Já está sincronizado com esta exata versão do arquivo do Drive
                                continue
                    except:
                        pass
                
                logger.info(f"🔄 Atualizando NJUD {day}: copiando {info['filename']}...")
                
                # Limpa destino antes de copiar para garantir apenas 1 arquivo de jornal por dia
                for f in os.listdir(target_dir):
                    if f.lower().endswith(('.gdoc', '.docx', '.doc', '.pdf', '.txt', '.xlsx', '.gsheet')):
                        logger.info(f"Protegendo documento: {f}")
                        continue
                    try:
                        os.remove(os.path.join(target_dir, f))
                    except OSError as oe:
                        logger.warning(f"Não foi possível remover arquivo antigo {f}: {oe}")
                
                # Copia o novo arquivo e cria o arquivo JSON de metadados
                shutil.copy2(info["filepath"], target_file)
                
                with open(meta_file, "w", encoding="utf-8") as f_meta:
                    json.dump({
                        "filename": info["filename"],
                        "date": info["date"].strftime("%d/%m/%Y"),
                        "synced_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    }, f_meta, ensure_ascii=False, indent=2)
                    
                updated_days.append(f"{day} ({info['filename']})")
                
            msg = f"Sincronia NJUD finalizada. Dias atualizados: {', '.join(updated_days) if updated_days else 'Tudo em dia'}."
            logger.info(msg)
            return {
                "success": True,
                "message": msg,
                "updated": len(updated_days),
                "total_scanned": total_scanned,
                "total_matched": total_matched
            }
            
        except Exception as e:
            logger.error(f"Erro no espelhamento do NJUD: {e}")
            return {"success": False, "error": str(e)}

    def get_status(self):
        status = {}
        for day in ["SEGUNDA", "TERCA", "QUARTA", "QUINTA", "SEXTA"]:
            day_path = os.path.join(self.target_local_dir, day)
            if not os.path.exists(day_path):
                status[day] = {"count": 0, "dates": []}
                continue
            
            mp3_files = [f for f in os.listdir(day_path) if f.lower().endswith(".mp3")]
            dates = set()
            
            # Tenta ler a data real dos metadados
            meta_file = os.path.join(day_path, "JORNAL_NJUD.json")
            if os.path.exists(meta_file):
                try:
                    with open(meta_file, "r", encoding="utf-8") as f_meta:
                        meta_data = json.load(f_meta)
                        if "date" in meta_data:
                            dates.add(meta_data["date"])
                except:
                    pass
            
            # Fallback para mtime se não houver JSON
            if not dates and mp3_files:
                for f in mp3_files:
                    filepath = os.path.join(day_path, f)
                    info = self.parse_njud_info(filepath)
                    if info:
                        dates.add(info["date"].strftime("%d/%m/%Y"))
                    else:
                        try:
                            mtime = os.path.getmtime(filepath)
                            dt = datetime.fromtimestamp(mtime)
                            dates.add(dt.strftime("%d/%m/%Y"))
                        except:
                            pass
                        
            status[day] = {"count": len(mp3_files), "dates": sorted(list(dates), reverse=True)}
        return status
