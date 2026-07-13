import os
import re
import shutil
import logging
import json
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("OmniCore.Spider")

DAY_MAP = {
    0: "SEGUNDA", 1: "TERCA", 2: "QUARTA", 3: "QUINTA", 4: "SEXTA", 5: "SABADO", 6: "DOMINGO"
}

def clean_dir(dir_path):
    if not os.path.exists(dir_path):
        return
    for f in os.listdir(dir_path):
        if f.lower().endswith(('.gdoc', '.docx', '.doc', '.pdf', '.txt', '.xlsx', '.gsheet')):
            logger.info(f"Protegendo documento: {f}")
            continue
        try:
            os.remove(os.path.join(dir_path, f))
        except OSError as oe:
            logger.warning(f"Não foi possível remover arquivo antigo {f}: {oe}")

class OmniSpider:
    def __init__(self):
        self.targets = []
        self._setup_targets()

    def _setup_targets(self):
        drive_base = r"H:\Meu Drive\RADIO TJRN CONTEÚDO\00_PRODUCAO_2026"
        
        # 1. Boletins
        self.targets.append({
            "type": "daily_multiple",
            "name": "Boletins",
            "source": os.path.join(drive_base, r"01_BOLETINS_DIARIOS\03_AUDIOS_RADIO"),
            "dest": r"D:\SERVIDOR\BOLETINS",
            "parser": self._parse_bulletin
        })

        # 2. NJUD
        self.targets.append({
            "type": "daily_single",
            "name": "NJUD",
            "source": os.path.join(drive_base, r"02_JORNAIS_NJUD\03_AUDIOS_RADIO"),
            "dest": r"D:\SERVIDOR\PROGRAMAS\JORNAL",
            "target_filename": "JORNAL_NJUD.mp3",
            "parser": self._parse_njud
        })

        # 3. Giro nas Comarcas
        self.targets.append({
            "type": "highest_number",
            "name": "Giro nas Comarcas",
            "source": os.path.join(drive_base, "03_GIRO_NAS_COMARCAS"),
            "dest": r"D:\SERVIDOR\PROGRAMAS\PROGRAMA_40\GIRONASCOMARCAS",
            "target_filename": "GIRO_ATUAL.mp3",
            "parser": self._parse_numbered
        })

        # 4. Levemente
        self.targets.append({
            "type": "highest_number",
            "name": "Levemente",
            "source": os.path.join(drive_base, "04_LEVEMENTE"),
            "dest": r"D:\SERVIDOR\PROGRAMAS\PROGRAMA_40\LEVEMENTE",
            "target_filename": "LEVEMENTE_ATUAL.mp3",
            "parser": self._parse_numbered
        })

        # 5. Memória da Justiça
        self.targets.append({
            "type": "highest_number",
            "name": "Memoria da Justica",
            "source": os.path.join(drive_base, "05_MEMORIA_DA_JUSTICA"),
            "dest": r"D:\SERVIDOR\PROGRAMAS\PROGRAMA_40\MEMORIA",
            "target_filename": "MEMORIA_ATUAL.mp3",
            "parser": self._parse_numbered
        })

    def _parse_bulletin(self, filename, filepath):
        for skip_word in ["OFF", "BRUTO", "PILOTO", "COPIA", "CÓPIA", "ROTEIRO", "APRESENTA", "GRAVAÇÃO", "GRAVACAO", "PTT-", "-WA", "AUD-", "_LEO", "_LIV", "_THI", "_LET", "_GRAV"]:
            if skip_word in filename.upper(): return None

        match = re.search(r"(\d{2})_(\d{2})_(\d{4})_B(\d+)", filename)
        if match:
            day, month, year, b_num = match.groups()
            try:
                dt = datetime(int(year), int(month), int(day))
                return {"date": dt, "day_name": DAY_MAP[dt.weekday()], "filepath": filepath, "filename": filename}
            except: pass
        return None

    def _parse_njud(self, filename, filepath):
        for skip_word in ["OFF", "BRUTO", "PILOTO", "COPIA", "CÓPIA", "ROTEIRO", "APRESENTA", "GRAVAÇÃO", "GRAVACAO"]:
            if skip_word in filename.upper(): return None
        if not filename.lower().endswith(".mp3"): return None

        match = re.search(r"njud[-_\s]+\d+[-_\s]+(\d{2})[-_\s](\d{2})(?:[-_\s](\d{4}))?", filename.lower())
        if match:
            day_str, month_str, year_str = match.groups()
            try:
                mtime = os.path.getmtime(filepath)
                mtime_dt = datetime.fromtimestamp(mtime)
                year = int(year_str) if year_str else mtime_dt.year
                dt = datetime(year, int(month_str), int(day_str))
                return {"date": dt, "day_name": DAY_MAP[dt.weekday()], "filepath": filepath, "filename": filename}
            except: pass
        return None

    def _parse_numbered(self, filename, filepath):
        for skip_word in ["OFF", "BRUTO", "PILOTO", "COPIA", "CÓPIA", "ROTEIRO", "APRESENTA", "GRAVAÇÃO", "GRAVACAO", "DOC", "VHT"]:
            if skip_word in filename.upper(): return None
        if not filename.lower().endswith(".mp3"): return None
        
        # Extrair o primeiro numero grande ou numero apos o nome do programa
        # Padroes: LM95, LEVEMENTE 102, GNC 104, MJ 50
        # Limitar a numeros de 1 a 4 digitos para evitar datas como "240226"
        match = re.search(r'(?:LM|LEVEMENTE|GNC|GIRO|MJ|MEMORIA)[-_\s]*0*(\d{1,4})\b', filename, re.IGNORECASE)
        if not match:
            # Fallback generico: primeiro numero encontrado
            match = re.search(r'\b0*(\d{1,4})\b', filename)
            
        if match:
            num = int(match.group(1))
            # Prevenir capturar o ano 2026 como numero do programa se for o unico numero
            if num == 2025 or num == 2026:
                # Tenta pegar outro numero antes do ano
                match2 = re.search(r'\b0*(\d{1,4})\b.*?(?:2025|2026)', filename)
                if match2:
                    num = int(match2.group(1))
                else:
                    return None # Provavelmente so tinha o ano
            return {"number": num, "filepath": filepath, "filename": filename}
        return None

    def _sync_daily_multiple(self, target):
        logger.info(f"🕷️ Spider varrendo: {target['name']}")
        source = target['source']
        dest = target['dest']
        if not os.path.exists(source):
            logger.warning(f"Pasta fonte não encontrada: {source}")
            return {"success": False, "error": "Fonte não encontrada"}

        os.makedirs(dest, exist_ok=True)
        for day in ["SEGUNDA", "TERCA", "QUARTA", "QUINTA", "SEXTA"]:
            os.makedirs(os.path.join(dest, day), exist_ok=True)

        found_items = []
        for root, _, files in os.walk(source):
            for f in files:
                if not f.lower().endswith(".mp3"): continue
                info = target['parser'](f, os.path.join(root, f))
                if info and info['day_name'] in ["SEGUNDA", "TERCA", "QUARTA", "QUINTA", "SEXTA"]:
                    found_items.append(info)

        # Agrupar por dia e data e pegar os arquivos mais recentes para cada dia
        # Isso substitui a pasta inteira pelos arquivos da data mais recente encontrada para aquele dia da semana
        updated = 0
        from itertools import groupby
        items_by_day = {}
        for item in found_items:
            day = item['day_name']
            if day not in items_by_day: items_by_day[day] = []
            items_by_day[day].append(item)

        for day, items in items_by_day.items():
            if not items: continue
            max_date = max(i['date'] for i in items)
            recent_items = [i for i in items if i['date'] == max_date]
            
            day_dest = os.path.join(dest, day)
            
            # Verificar se já estão lá
            local_files = os.listdir(day_dest)
            # Se as quantidades forem iguais e o nome do primeiro bater, assumimos sync ok para otimizar
            if len(local_files) == len(recent_items) and len(recent_items) > 0:
                if recent_items[0]['filename'] in local_files:
                    continue # Já sincronizado

            clean_dir(day_dest)
            for item in recent_items:
                shutil.copy2(item['filepath'], os.path.join(day_dest, item['filename']))
                updated += 1
                
        return {"success": True, "updated": updated, "message": f"{target['name']}: {updated} atualizações."}

    def _sync_daily_single(self, target):
        logger.info(f"🕷️ Spider varrendo: {target['name']}")
        source = target['source']
        dest = target['dest']
        if not os.path.exists(source):
            logger.warning(f"Pasta fonte não encontrada: {source}")
            return {"success": False, "error": "Fonte não encontrada"}

        os.makedirs(dest, exist_ok=True)
        for day in ["SEGUNDA", "TERCA", "QUARTA", "QUINTA", "SEXTA"]:
            os.makedirs(os.path.join(dest, day), exist_ok=True)

        found_items = []
        for root, _, files in os.walk(source):
            for f in files:
                info = target['parser'](f, os.path.join(root, f))
                if info and info['day_name'] in ["SEGUNDA", "TERCA", "QUARTA", "QUINTA", "SEXTA"]:
                    found_items.append(info)

        updated = 0
        items_by_day = {}
        for item in found_items:
            day = item['day_name']
            if day not in items_by_day: items_by_day[day] = []
            items_by_day[day].append(item)

        for day, items in items_by_day.items():
            if not items: continue
            max_item = max(items, key=lambda x: x['date'])
            
            day_dest = os.path.join(dest, day)
            meta_file = os.path.join(day_dest, "spider_meta.json")
            target_file = os.path.join(day_dest, target['target_filename'])
            
            # Check se atualizado
            if os.path.exists(target_file) and os.path.exists(meta_file):
                try:
                    with open(meta_file, 'r', encoding='utf-8') as mf:
                        meta = json.load(mf)
                        if meta.get('filename') == max_item['filename']:
                            continue
                except: pass
                
            clean_dir(day_dest)
            shutil.copy2(max_item['filepath'], target_file)
            with open(meta_file, 'w', encoding='utf-8') as mf:
                json.dump({"filename": max_item['filename'], "date": str(max_item['date'])}, mf)
            updated += 1
            
        return {"success": True, "updated": updated, "message": f"{target['name']}: {updated} atualizações."}

    def _sync_highest_number(self, target):
        logger.info(f"🕷️ Spider varrendo: {target['name']}")
        source = target['source']
        dest = target['dest']
        if not os.path.exists(source):
            logger.warning(f"Pasta fonte não encontrada: {source}")
            return {"success": False, "error": "Fonte não encontrada"}

        os.makedirs(dest, exist_ok=True)
        
        highest_item = None
        for root, _, files in os.walk(source):
            for f in files:
                info = target['parser'](f, os.path.join(root, f))
                if info:
                    if not highest_item or info['number'] > highest_item['number']:
                        highest_item = info

        if not highest_item:
            return {"success": True, "updated": 0, "message": f"{target['name']}: Nenhum arquivo válido encontrado."}
            
        meta_file = os.path.join(dest, "spider_meta.json")
        target_file = os.path.join(dest, target['target_filename'])
        
        if os.path.exists(target_file) and os.path.exists(meta_file):
            try:
                with open(meta_file, 'r', encoding='utf-8') as mf:
                    meta = json.load(mf)
                    if meta.get('number') == highest_item['number']:
                        return {"success": True, "updated": 0, "message": f"{target['name']}: Tudo em dia (Prog. {highest_item['number']})."}
            except: pass
            
        clean_dir(dest)
        shutil.copy2(highest_item['filepath'], target_file)
        with open(meta_file, 'w', encoding='utf-8') as mf:
            json.dump({"filename": highest_item['filename'], "number": highest_item['number']}, mf)
            
        logger.info(f"🕷️ Atualizado {target['name']} para programa #{highest_item['number']} ({highest_item['filename']})")
        return {"success": True, "updated": 1, "message": f"{target['name']}: Atualizado para #{highest_item['number']}."}

    def spin(self):
        results = []
        for t in self.targets:
            try:
                if t['type'] == 'daily_multiple':
                    res = self._sync_daily_multiple(t)
                elif t['type'] == 'daily_single':
                    res = self._sync_daily_single(t)
                elif t['type'] == 'highest_number':
                    res = self._sync_highest_number(t)
                results.append(res)
            except Exception as e:
                logger.error(f"Erro no spider alvo {t['name']}: {e}")
                results.append({"success": False, "error": str(e), "message": f"{t['name']} falhou."})
                
        total_updated = sum(r.get('updated', 0) for r in results)
        return {"success": True, "updated_total": total_updated, "details": results}

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    spider = OmniSpider()
    print(json.dumps(spider.spin(), indent=2, ensure_ascii=False))
