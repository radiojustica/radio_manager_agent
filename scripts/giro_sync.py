import os
import re
import shutil
import logging
import json
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("OmniCore.GiroSync")

DAY_MAP = {
    0: "SEGUNDA", 1: "TERCA", 2: "QUARTA", 3: "QUINTA", 4: "SEXTA", 5: "SABADO", 6: "DOMINGO"
}

class GiroSync:
    def __init__(self, source_dir=None, target_dir=None):
        config = self._load_config()
        
        # Mapeamento do Drive do Giro nas Comarcas
        self.source_drive_dir = source_dir or config.get("grade", {}).get(
            "pasta_drive_giro", 
            r"D:\SERVIDOR\DRIVE\RADIO TJRN CONTEÚDO\PROGRAMAS\PROGRAMA GIRO NAS COMARCAS (10min)"
        )
        self.target_local_dir = target_dir or config.get("grade", {}).get(
            "pasta_giro_raiz", 
            r"D:\SERVIDOR\PROGRAMAS\PROGRAMA_40\GIRONASCOMARCAS"
        )
        
        # Pasta do Drive Montado (H:) como fallback principal
        self.fallback_drive_dir = r"H:\Meu Drive\RADIO TJRN CONTEÚDO\PROGRAMAS\PROGRAMA GIRO NAS COMARCAS (10min)"
        
        os.makedirs(self.target_local_dir, exist_ok=True)

    def _load_config(self) -> dict:
        config_path = Path(__file__).resolve().parent.parent / "config" / "settings.json"
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Erro ao carregar settings.json no GiroSync: {e}")
        return {}

    def parse_giro_info(self, filepath: str):
        filename = os.path.basename(filepath)
        
        # Ignora arquivos parciais
        for skip_word in ["OFF", "BRUTO", "PILOTO", "COPIA", "CÓPIA", "ROTEIRO", "APRESENTA", "GRAVAÇÃO", "GRAVACAO"]:
            if skip_word in filename.upper():
                return None
                
        if not filename.lower().endswith(".mp3"):
            return None
            
        # Tenta extrair data no formato DD-MM ou DD_MM
        match = re.search(r"(\d{2})[-_](\d{2})", filename)
        if match:
            day_str, month_str = match.groups()
            try:
                mtime = os.path.getmtime(filepath)
                mtime_dt = datetime.fromtimestamp(mtime)
                # Assume o ano de modificação
                dt = datetime(mtime_dt.year, int(month_str), int(day_str))
                return {
                    "date": dt,
                    "filename": filename,
                    "filepath": filepath,
                    "day_name": DAY_MAP[dt.weekday()]
                }
            except:
                pass
                
        # Fallback para data de modificação física do arquivo
        try:
            mtime = os.path.getmtime(filepath)
            dt = datetime.fromtimestamp(mtime)
            return {
                "date": dt,
                "filename": filename,
                "filepath": filepath,
                "day_name": DAY_MAP[dt.weekday()]
            }
        except Exception as e:
            logger.debug(f"Falha ao ler mtime de {filename}: {e}")
            return None

    def sync(self) -> dict:
        """Sincroniza o Giro nas Comarcas mais recente para a pasta local."""
        source_dir = self.source_drive_dir
        if not os.path.exists(source_dir) and os.path.exists(self.fallback_drive_dir):
            source_dir = self.fallback_drive_dir
            
        logger.info(f"Iniciando espelhamento do Giro nas Comarcas: {source_dir} -> {self.target_local_dir}")
        
        if not os.path.exists(source_dir):
            return {"success": False, "error": f"Pasta de origem não encontrada: {source_dir}"}

        # VALIDAÇÃO DE SEGURANÇA: destino deve estar dentro de D:\SERVIDOR
        _RAIZ_SERVIDOR = r"D:\SERVIDOR"
        norm_target = os.path.normpath(os.path.abspath(self.target_local_dir))
        norm_servidor = os.path.normpath(os.path.abspath(_RAIZ_SERVIDOR))
        if not norm_target.startswith(norm_servidor + os.sep) and norm_target != norm_servidor:
            return {"success": False, "error": f"[SEGURANÇA] Pasta destino fora de {_RAIZ_SERVIDOR}: {self.target_local_dir}"}
            
        try:
            # Encontrar o Giro mais recente de todos os escaneados
            newest_giro = None
            total_scanned = 0
            total_matched = 0
            
            for root, dirs, files in os.walk(source_dir):
                for f in files:
                    total_scanned += 1
                    filepath = os.path.join(root, f)
                    info = self.parse_giro_info(filepath)
                    if not info:
                        continue
                        
                    total_matched += 1
                    if not newest_giro or info["date"] > newest_giro["date"]:
                        newest_giro = info
                        
            if not newest_giro:
                msg = "Nenhum arquivo válido de Giro nas Comarcas encontrado para sincronização."
                logger.info(msg)
                return {
                    "success": True,
                    "message": msg,
                    "updated": 0,
                    "total_scanned": total_scanned,
                    "total_matched": 0
                }
                
            target_file = os.path.join(self.target_local_dir, "GIRO_ATUAL.mp3")
            meta_file = os.path.join(self.target_local_dir, "GIRO_ATUAL.json")
            
            # Verifica se já está sincronizado com a exata versão mais recente do Drive
            if os.path.exists(target_file) and os.path.exists(meta_file):
                try:
                    with open(meta_file, "r", encoding="utf-8") as f_meta:
                        meta_data = json.load(f_meta)
                        if meta_data.get("filename") == newest_giro["filename"]:
                            # Já está sincronizado
                            logger.info(f"Giro nas Comarcas {newest_giro['filename']} já está atualizado no destino.")
                            return {
                                "success": True,
                                "message": "Tudo em dia.",
                                "updated": 0,
                                "total_scanned": total_scanned,
                                "total_matched": total_matched
                            }
                except:
                    pass
                    
            logger.info(f"🔄 Atualizando Giro nas Comarcas: copiando {newest_giro['filename']}...")
            
            # STAGING ATÔMICO: mover arquivos antigos para backup antes de copiar
            # Somente .mp3 e .json são elegíveis para substituição
            _EXTS_SUBSTITUIVEIS = ('.mp3', '.json')
            backup_dir = os.path.join(self.target_local_dir, "_backup_anterior")
            old_files = [
                f for f in os.listdir(self.target_local_dir)
                if os.path.isfile(os.path.join(self.target_local_dir, f))
                and f.lower().endswith(_EXTS_SUBSTITUIVEIS)
                and not f.startswith("_backup")
            ]
            
            os.makedirs(backup_dir, exist_ok=True)
            backed_up = []
            for fname in old_files:
                try:
                    shutil.move(os.path.join(self.target_local_dir, fname), os.path.join(backup_dir, fname))
                    backed_up.append(fname)
                except OSError as oe:
                    logger.warning(f"Falha ao mover {fname} para backup: {oe}")

            try:
                # Realiza a cópia física
                shutil.copy2(newest_giro["filepath"], target_file)
                
                # Escreve metadados
                with open(meta_file, "w", encoding="utf-8") as f_meta:
                    json.dump({
                        "filename": newest_giro["filename"],
                        "date": newest_giro["date"].strftime("%d/%m/%Y"),
                        "synced_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    }, f_meta, ensure_ascii=False, indent=2)
                    
                # Sucesso: remove o backup
                shutil.rmtree(backup_dir, ignore_errors=True)
                logger.info(f"Backup anterior removido após sincronização bem-sucedida.")
                    
            except Exception as copy_err:
                # Falha na cópia: restaurar arquivos do backup
                logger.error(f"Falha na cópia. Restaurando backup: {copy_err}")
                for fname in backed_up:
                    try:
                        shutil.move(os.path.join(backup_dir, fname), os.path.join(self.target_local_dir, fname))
                    except Exception as restore_err:
                        logger.error(f"Falha ao restaurar {fname}: {restore_err}")
                shutil.rmtree(backup_dir, ignore_errors=True)
                raise copy_err
                
            msg = f"Sincronia do Giro finalizada. Atualizado para: {newest_giro['filename']}."
            logger.info(msg)
            return {
                "success": True,
                "message": msg,
                "updated": 1,
                "total_scanned": total_scanned,
                "total_matched": total_matched
            }
            
        except Exception as e:
            logger.error(f"Erro no espelhamento do Giro nas Comarcas: {e}")
            return {"success": False, "error": str(e)}

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    syncer = GiroSync()
    print(syncer.sync())
