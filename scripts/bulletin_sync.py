import os
import re
import shutil
import logging
import json
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("OmniCore.BulletinSync")

DAY_MAP = {
    0: "SEGUNDA", 1: "TERCA", 2: "QUARTA", 3: "QUINTA", 4: "SEXTA", 5: "SABADO", 6: "DOMINGO"
}

class BulletinSync:
    def __init__(self, source_dir=None, target_dir=None):
        # Carregar configurações
        config = self._load_config()
        
        # Prioridade: 1. Argumentos passados, 2. settings.json, 3. Defaults hardcoded
        self.source_drive_dir = source_dir or config.get("grade", {}).get("pasta_drive_boletins", r"D:\SERVIDOR\DRIVE\RADIO TJRN CONTEÚDO\EDIÇÃO\BOLETINS")
        self.target_local_dir = target_dir or config.get("grade", {}).get("pasta_boletins_raiz", r"D:\SERVIDOR\BOLETINS")
        
        os.makedirs(self.target_local_dir, exist_ok=True)
        for day in ["SEGUNDA", "TERCA", "QUARTA", "QUINTA", "SEXTA"]:
            os.makedirs(os.path.join(self.target_local_dir, day), exist_ok=True)

    def _load_config(self):
        """Carrega settings.json se existir."""
        config_path = Path(__file__).resolve().parent.parent / "config" / "settings.json"
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Erro ao carregar settings.json no BulletinSync: {e}")
        return {}

    def parse_bulletin_info(self, filename):
        """Identifica data e número do boletim. Ignora arquivos de edição."""
        # Logs detalhados para arquivos ignorados por palavras-chave
        for skip_word in ["OFF", "GRAVAÇÃO", "GRAVACAO", "BRUTO", "PILOTO"]:
            if skip_word in filename.upper():
                logger.debug(f"Arquivo ignorado (palavra-chave '{skip_word}'): {filename}")
                return None
                
        match = re.search(r"(\d{2})_(\d{2})_(\d{4})_B(\d+)", filename)
        if match:
            day, month, year, b_num = match.groups()
            try:
                dt = datetime(int(year), int(month), int(day))
                return {
                    "date": dt, 
                    "b_num": int(b_num), 
                    "filename": filename, 
                    "day_name": DAY_MAP[dt.weekday()]
                }
            except Exception as e:
                logger.debug(f"Falha ao processar data no arquivo {filename}: {e}")
                return None
        
        logger.debug(f"Arquivo ignorado (padrão de nome não coincide): {filename}")
        return None

    def sync(self):
        """Sincroniza do Drive Local para o Servidor Local."""
        logger.info(f"Iniciando espelhamento: {self.source_drive_dir} -> {self.target_local_dir}")
        
        if not os.path.exists(self.source_drive_dir):
            return {"success": False, "error": f"Pasta de origem não encontrada: {self.source_drive_dir}"}

        try:
            # 1. Mapear arquivos no Drive de forma recursiva
            drive_files_by_day = {}
            total_scanned = 0
            total_matched = 0
            
            for root, dirs, files in os.walk(self.source_drive_dir):
                for f in files:
                    if not f.lower().endswith(".mp3"): continue
                    total_scanned += 1
                    info = self.parse_bulletin_info(f)
                    if not info: continue
                    
                    total_matched += 1
                    day = info['day_name']
                    if day not in drive_files_by_day or info['date'] > drive_files_by_day[day]['date']:
                        drive_files_by_day[day] = {"date": info['date'], "files": [os.path.join(root, f)]}
                    elif info['date'] == drive_files_by_day[day]['date']:
                        drive_files_by_day[day]['files'].append(os.path.join(root, f))

            logger.info(f"Varredura concluída. Arquivos MP3: {total_scanned}, Casados: {total_matched}")
            
            # 2. Substituição Atômica no Servidor
            updated_days = []
            for day, data in drive_files_by_day.items():
                if day not in ["SEGUNDA", "TERCA", "QUARTA", "QUINTA", "SEXTA"]: continue
                
                target_dir = os.path.join(self.target_local_dir, day)
                local_dates = self._get_dates_in_local_dir(target_dir)
                max_local = max(local_dates) if local_dates else None
                
                # Se o Drive tem algo mais novo que o Local ou Local está vazio
                if not local_dates or data['date'] > max(local_dates):
                    logger.info(f"🔄 Atualizando {day}: Drive={data['date'].strftime('%d/%m/%Y')} | Local={max_local.strftime('%d/%m/%Y') if max_local else 'Vazio'}")
                    
                    # Pasta temporária
                    temp_maneuver = os.path.join(os.environ.get("TEMP", "C:\\TEMP"), f"omni_sync_{day}")
                    try:
                        if os.path.exists(temp_maneuver): shutil.rmtree(temp_maneuver)
                        os.makedirs(temp_maneuver)
                        
                        for f_path in data['files']:
                            shutil.copy2(f_path, os.path.join(temp_maneuver, os.path.basename(f_path)))
                        
                        if os.listdir(temp_maneuver):
                            # Limpa destino
                            for f in os.listdir(target_dir):
                                try: os.remove(os.path.join(target_dir, f))
                                except: pass
                            
                            # Move arquivos
                            for f in os.listdir(temp_maneuver):
                                shutil.move(os.path.join(temp_maneuver, f), os.path.join(target_dir, f))
                            
                            updated_days.append(f"{day} ({data['date'].strftime('%d/%m')})")
                    finally:
                        # Garantir limpeza da pasta temporária
                        if os.path.exists(temp_maneuver):
                            try: shutil.rmtree(temp_maneuver)
                            except Exception as te: logger.warning(f"Falha ao limpar pasta TEMP {temp_maneuver}: {te}")

            msg = f"Sincronia Finalizada. Dias atualizados: {', '.join(updated_days) if updated_days else 'Tudo em dia'}."
            logger.info(msg)
            return {
                "success": True, 
                "message": msg, 
                "updated": len(updated_days),
                "total_scanned": total_scanned,
                "total_matched": total_matched
            }

        except Exception as e:
            logger.error(f"Erro no espelhamento local: {e}")
            return {"success": False, "error": str(e)}

    def _get_dates_in_local_dir(self, directory):
        dates = []
        if not os.path.exists(directory): return []
        for f in os.listdir(directory):
            info = self.parse_bulletin_info(f)
            if info: dates.append(info['date'])
        return dates

    def get_status(self):
        status = {}
        for day in ["SEGUNDA", "TERCA", "QUARTA", "QUINTA", "SEXTA"]:
            day_path = os.path.join(self.target_local_dir, day)
            if not os.path.exists(day_path):
                status[day] = {"count": 0, "dates": []}
                continue
            files = [f for f in os.listdir(day_path) if f.lower().endswith(".mp3")]
            dates = set()
            for f in files:
                info = self.parse_bulletin_info(f)
                if info: dates.add(info['date'].strftime("%d/%m/%Y"))
            status[day] = {"count": len(files), "dates": sorted(list(dates), reverse=True)}
        return status

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    syncer = BulletinSync()
    print(syncer.sync())
