import os
import re
import shutil
import logging
from datetime import datetime

logger = logging.getLogger("OmniCore.BulletinSync")

# Caminhos Locais (Sincronizados via Google Drive Desktop)
SOURCE_DRIVE_DIR = r"D:\SERVIDOR\DRIVE\RADIO TJRN CONTEÚDO\EDIÇÃO\BOLETINS"
TARGET_LOCAL_DIR = r"D:\SERVIDOR\BOLETINS"

DAY_MAP = {
    0: "SEGUNDA", 1: "TERCA", 2: "QUARTA", 3: "QUINTA", 4: "SEXTA", 5: "SABADO", 6: "DOMINGO"
}

class BulletinSync:
    def __init__(self):
        os.makedirs(TARGET_LOCAL_DIR, exist_ok=True)
        for day in ["SEGUNDA", "TERCA", "QUARTA", "QUINTA", "SEXTA"]:
            os.makedirs(os.path.join(TARGET_LOCAL_DIR, day), exist_ok=True)

    def parse_bulletin_info(self, filename):
        """Identifica data e número do boletim. Ignora arquivos de edição."""
        if any(x in filename.upper() for x in ["OFF", "GRAVAÇÃO", "GRAVACAO", "BRUTO", "PILOTO"]):
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
            except: return None
        return None

    def sync(self):
        """Sincroniza do Drive Local (G:) para o Servidor Local (D:)."""
        logger.info(f"Iniciando espelhamento local: {SOURCE_DRIVE_DIR} -> {TARGET_LOCAL_DIR}")
        
        if not os.path.exists(SOURCE_DRIVE_DIR):
            return {"success": False, "error": f"Pasta de origem não encontrada: {SOURCE_DRIVE_DIR}"}

        try:
            # 1. Mapear arquivos no Drive (D:\...\BOLETINS) de forma recursiva
            drive_files_by_day = {}
            total_scanned = 0
            total_matched = 0
            
            for root, dirs, files in os.walk(SOURCE_DRIVE_DIR):
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

            logger.info(f"Varredura concluída. Arquivos MP3: {total_scanned}, Casados com padrão: {total_matched}")
            for day, data in drive_files_by_day.items():
                logger.info(f"Drive - Mais recente para {day}: {data['date'].strftime('%d/%m/%Y')} ({len(data['files'])} arquivos)")

            # 2. Substituição Atômica no Servidor (D:)
            updated_days = []
            for day, data in drive_files_by_day.items():
                if day not in ["SEGUNDA", "TERCA", "QUARTA", "QUINTA", "SEXTA"]: continue
                
                target_dir = os.path.join(TARGET_LOCAL_DIR, day)
                local_dates = self._get_dates_in_local_dir(target_dir)
                max_local = max(local_dates) if local_dates else None
                
                logger.info(f"Analisando {day}: Drive={data['date'].strftime('%d/%m/%Y')} | Local={max_local.strftime('%d/%m/%Y') if max_local else 'Vazio'}")

                # Se o Drive tem algo mais novo que o Local ou Local está vazio
                if not local_dates or data['date'] > max(local_dates):
                    logger.info(f"🔄 Atualizando {day} para {data['date'].strftime('%d/%m/%Y')}...")
                    
                    # Passo de Segurança: Copiar para uma pasta temporária antes
                    temp_maneuver = os.path.join(os.environ.get("TEMP", "C:\\TEMP"), f"omni_sync_{day}")
                    if os.path.exists(temp_maneuver): shutil.rmtree(temp_maneuver)
                    os.makedirs(temp_maneuver)
                    
                    for f_path in data['files']:
                        shutil.copy2(f_path, os.path.join(temp_maneuver, os.path.basename(f_path)))
                    
                    # Se a cópia para o TEMP deu certo, limpa o D: e move
                    if os.listdir(temp_maneuver):
                        for f in os.listdir(target_dir):
                            try: os.remove(os.path.join(target_dir, f))
                            except: pass
                        
                        for f in os.listdir(temp_maneuver):
                            shutil.move(os.path.join(temp_maneuver, f), os.path.join(target_dir, f))
                        
                        updated_days.append(f"{day} ({data['date'].strftime('%d/%m')})")
                        shutil.rmtree(temp_maneuver)

            msg = f"Sincronia Finalizada. Dias atualizados: {', '.join(updated_days) if updated_days else 'Tudo em dia'}."
            logger.info(msg)
            return {"success": True, "message": msg, "updated": len(updated_days)}

        except Exception as e:
            logger.error(f"Erro no espelhamento local: {e}")
            return {"success": False, "error": str(e)}

    def _get_dates_in_local_dir(self, directory):
        dates = []
        for f in os.listdir(directory):
            info = self.parse_bulletin_info(f)
            if info: dates.append(info['date'])
        return dates

    def get_status(self):
        status = {}
        for day in ["SEGUNDA", "TERCA", "QUARTA", "QUINTA", "SEXTA"]:
            day_path = os.path.join(TARGET_LOCAL_DIR, day)
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


