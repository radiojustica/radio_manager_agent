# core/compliance_validator.py
"""
Compliance Validator — Omni Core V3
===================================
O validador regulatório e de regras do canal (Camada Determinística Inviolável).
Garante conformidade antes de qualquer playlist ser executada na rádio.
"""

import os
import logging
from datetime import datetime
from core.database import SessionLocal
from core.models import Musica
from director.profile import PROFILE
from scripts.artist_cleaner import clean_artist_name
from core.time_utils import now_local

logger = logging.getLogger("OmniCore.ComplianceValidator")

def pertence_ao_tema_dict(meta_dict, caminho, tema) -> bool:
    if not tema:
        return False
    
    m_meta = meta_dict.get(caminho, {})
    estilo_lower = m_meta.get("estilo", "").lower()
    artista_lower = m_meta.get("artista", "").lower()
    caminho_upper = caminho.upper()
    
    if tema == "clarone":
        return any(x in estilo_lower for x in ["clarone", "pixinguinha", "choro"]) or "PIXINGUINHA" in caminho_upper
    elif tema == "choro":
        return any(x in estilo_lower for x in ["choro", "chorinho", "pixinguinha"])
    elif tema == "jazz":
        return any(x in estilo_lower for x in ["jazz", "blues"])
    elif tema == "tecladista":
        return any(x in estilo_lower for x in ["teclado", "tecladista", "piano", "keyboard", "synth", "sintetizador"])
    elif tema == "reggae":
        return "reggae" in estilo_lower
    elif tema == "marisa_monte":
        return "marisa monte" in artista_lower or "MARISA MONTE" in caminho_upper
    elif tema == "rock":
        return any(x in estilo_lower for x in ["rock", "metal"])
    elif tema == "hiphop":
        return any(x in estilo_lower for x in ["hip-hop", "hip hop", "rap"])
    elif tema == "folclore":
        return any(x in estilo_lower for x in ["folclore", "samba de coco", "coco de roda", "regional"]) or any(x in caminho_upper for x in ["FOLCLORE", "SAMBA DE COCO", "COCO DE RODA"])
    elif tema == "mpb":
        return any(x in estilo_lower for x in ["mpb", "bossa", "musica popular brasileira"])
    elif tema == "musico":
        return any(x in estilo_lower for x in ["instrumental", "virtuoso", "solo", "bossa", "choro", "jazz"]) or "INSTRUMENTAL" in caminho_upper
    elif tema == "samba":
        return any(x in estilo_lower for x in ["samba", "pagode"]) or any(x in caminho_upper for x in ["ROCAS", "SAMBA"])
    elif tema == "tango":
        return any(x in estilo_lower for x in ["tango", "astor piazzolla", "gardel", "latino"])
    elif tema == "forro":
        ESTILOS_FORRO = ["forró", "forro", "luiz gonzaga", "baião", "baiao", "xote", "xaxado"]
        return any(x in estilo_lower for x in ESTILOS_FORRO) or any(x.upper() in caminho_upper for x in ESTILOS_FORRO)
    return False

class ComplianceValidator:
    def __init__(self):
        self.constraints = PROFILE["constraints"]
        self.quotas = PROFILE["quotas"]

    def get_track_durations(self, paths: list[str]) -> dict[str, int]:
        """Consulta o banco de dados para obter a duração real das músicas."""
        durations = {}
        if not paths:
            return durations

        db = SessionLocal()
        try:
            # Consulta as durações em lote para otimizar performance
            musicas = db.query(Musica).filter(Musica.caminho.in_(paths)).all()
            for m in musicas:
                durations[m.caminho] = m.duracao or 210
        except Exception as e:
            logger.error(f"[Compliance] Erro ao buscar durações no banco: {e}")
        finally:
            db.close()
        return durations

    def get_track_tema_especial(self, paths: list[str]) -> dict[str, str]:
        """Consulta o banco de dados para obter o tema especial de cada música."""
        temas = {}
        if not paths:
            return temas

        db = SessionLocal()
        try:
            musicas = db.query(Musica).filter(Musica.caminho.in_(paths)).all()
            for m in musicas:
                if m.tema_especial:
                    temas[m.caminho] = m.tema_especial.lower()
        except Exception as e:
            logger.error(f"[Compliance] Erro ao buscar temas especiais no banco: {e}")
        finally:
            db.close()
        return temas

    def get_track_estilos(self, paths: list[str]) -> dict[str, str]:
        """Consulta o banco de dados para obter o estilo de cada música."""
        estilos = {}
        if not paths:
            return estilos

        db = SessionLocal()
        try:
            musicas = db.query(Musica).filter(Musica.caminho.in_(paths)).all()
            for m in musicas:
                if m.estilo:
                    estilos[m.caminho] = m.estilo.lower()
        except Exception as e:
            logger.error(f"[Compliance] Erro ao buscar estilos no banco: {e}")
        finally:
            db.close()
        return estilos

    def get_track_metadata(self, paths: list[str]) -> dict[str, dict]:
        """Consulta o banco de dados para obter estilo, artista e tema_especial em lote."""
        meta = {}
        if not paths:
            return meta

        db = SessionLocal()
        try:
            musicas = db.query(Musica).filter(Musica.caminho.in_(paths)).all()
            for m in musicas:
                meta[m.caminho] = {
                    "artista": m.artista or "",
                    "estilo": m.estilo or "",
                    "tema_especial": m.tema_especial or ""
                }
        except Exception as e:
            logger.error(f"[Compliance] Erro ao buscar metadados no banco: {e}")
        finally:
            db.close()
        return meta

    def get_track_type(self, path: str) -> str:
        """Classifica o tipo da faixa baseado no caminho e nome do arquivo."""
        path_upper = path.upper()
        if r"D:\RADIO\MUSICAS" in path_upper:
            # Proteção contra carimbos/vinhetas soltos na pasta de músicas
            if "CARIMBO" in path_upper or "VHT" in path_upper or "VINHETA" in path_upper:
                return "VINHETA"
            return "MUSICA"
        elif r"D:\RADIO\VINHETAS" in path_upper or "VHT" in path_upper or "VINHETA" in path_upper:
            return "VINHETA"
        elif r"D:\RADIO\SPOTS" in path_upper or "SPOT" in path_upper:
            return "SPOT"
        elif r"D:\SERVIDOR\BOLETINS" in path_upper or "BOLETIM" in path_upper:
            return "BOLETIM"
        elif r"D:\SERVIDOR\PROGRAMAS" in path_upper:
            return "PROGRAMA"
            
        # Fallback pelo nome do arquivo
        nome = os.path.basename(path_upper)
        if "VHT" in nome or "VINHETA" in nome or "CARIMBO" in nome:
            return "VINHETA"
        if "SPOT" in nome:
            return "SPOT"
        if "BOLETIM" in nome:
            return "BOLETIM"
        return "MUSICA"

    def validate_playlist(self, file_path: str, hour: int, date_context: datetime = None) -> list[str]:
        """
        Valida se um arquivo M3U cumpre todas as regras inegociáveis de conformidade.
        Retorna uma lista com as violações. Se vazia, a playlist é 100% segura.
        """
        violations = []
        if not os.path.exists(file_path):
            return ["Arquivo de playlist não encontrado."]

        if date_context is None:
            date_context = now_local()

        # Lê os caminhos da playlist
        raw_lines = []
        try:
            with open(file_path, "r", encoding="cp1252", errors="ignore") as f:
                raw_lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
        except Exception as e:
            return [f"Falha técnica ao ler arquivo M3U: {e}"]

        if not raw_lines:
            return ["A playlist está vazia."]

        # Validação de consecutivos (não pode ter 2 spots seguidos, 2 vinhetas seguidas, 2 boletins seguidos)
        last_type = None
        last_path = None
        for path in raw_lines:
            t = self.get_track_type(path)
            if t in ["VINHETA", "SPOT", "BOLETIM"]:
                if t == last_type:
                    violations.append(
                        f"Detecção de colisão consecutiva de assets: {t} seguido de {t} "
                        f"('{os.path.basename(last_path)}' -> '{os.path.basename(path)}')."
                    )
                    break  # Rejeita na primeira colisão
            last_type = t
            last_path = path

        # Separa caminhos por categoria e calcula duração estimada
        music_paths = []
        total_duration = 0
        
        # Coleta todas as músicas para busca em lote no banco
        potential_music_paths = [p for p in raw_lines if r"D:\RADIO\MUSICAS" in p.upper()]
        db_durations = self.get_track_durations(potential_music_paths)
        db_temas = self.get_track_tema_especial(potential_music_paths)

        for path in raw_lines:
            path_upper = path.upper()
            if r"D:\RADIO\MUSICAS" in path_upper:
                music_paths.append(path)
                # Pega a duração real do DB ou padrão de 210s
                total_duration += db_durations.get(path, 210)
            elif r"D:\RADIO\VINHETAS" in path_upper:
                total_duration += 5  # Duração padrão vinheta
            elif r"D:\RADIO\SPOTS" in path_upper:
                total_duration += 30  # Duração padrão spot
            elif r"D:\SERVIDOR\BOLETINS" in path_upper:
                total_duration += 120  # Duração padrão boletim
            elif r"D:\SERVIDOR\PROGRAMAS" in path_upper:
                # Estimativa de programas baseada no nome
                if "GIRO" in path_upper:
                    total_duration += 600
                elif "MEMORIA" in path_upper:
                    total_duration += 2400
                elif "LEVEMENTE" in path_upper:
                    total_duration += 2400
                elif "JORNAL" in path_upper or "NOT" in path_upper:
                    total_duration += 300
                else:
                    total_duration += 300
            else:
                # Outros tipos de arquivo (fallback genérico)
                total_duration += 180

        # 1. Validação de Duração (7200s - 8000s)
        # Permite flexibilidade de +/- 5 minutos (300s) para evitar problemas com grade quebrada e blocos extras
        min_dur = 7200
        max_dur = 8000
        if total_duration < min_dur or total_duration > max_dur:
            violations.append(
                f"Duração total ({total_duration}s / {total_duration/60:.1f}min) "
                f"fora dos limites regulamentares permitidos ({min_dur}s - {max_dur}s)."
            )

        # 2. Validação de Janela de Separação de Artista
        artist_window = self.constraints["artist_separation_count"]
        for i in range(len(music_paths)):
            window = music_paths[i : i + artist_window]
            if len(window) < 2:
                break
            artistas = [clean_artist_name(None, p) for p in window]
            atual = artistas[0]
            if atual != "VARIOUS" and artistas.count(atual) > 1:
                violations.append(
                    f"Artista '{atual}' repete violando a janela de separação mínima de {artist_window} músicas."
                )
                break  # Apenas uma violação por auditoria para evitar flood

        # 3. Validação de Janela de Separação de Música/Faixa
        track_window = self.constraints["track_separation_count"]
        for i in range(len(music_paths)):
            window = music_paths[i : i + track_window]
            if len(window) < 2:
                break
            caminhos = [p.lower() for p in window]
            atual = caminhos[0]
            if caminhos.count(atual) > 1:
                nome_musica = os.path.basename(atual)
                violations.append(
                    f"Música '{nome_musica}' repete violando a janela de separação de {track_window} músicas."
                )
                break

        # 4. Validação de Quota Regional
        regional_count = sum(1 for p in music_paths if r"REGIONAL" in p.upper())
        if len(music_paths) >= 8 and regional_count == 0:
            violations.append("Nenhuma música regional identificada na playlist (Quota Mínima: 1 a cada 8 faixas).")

        # 5. Validação de Sazonalidade Estrita
        mes_atual = date_context.month
        
        # Filtra violações sazonais com base no mês e nos metadados/pastas físicas
        for path in music_paths:
            path_lower = path.lower()
            tema = db_temas.get(path, "")

            # Bloqueio de natal fora de dezembro
            if mes_atual != 12:
                if "especial_natal" in path_lower or tema == "natal":
                    violations.append(f"Música natalina '{os.path.basename(path)}' tocando fora de Dezembro.")
                    break

            # Bloqueio de festas juninas fora de junho
            if mes_atual != 6:
                if "especial_junho" in path_lower or tema == "junho":
                    violations.append(f"Música junina/sazonal '{os.path.basename(path)}' tocando fora de Junho.")
                    break

        # 6. Validação de Sazonalidade Temática e Cota para Datas Especiais
        dia_mes = (mes_atual, date_context.day)
        DIAS_TEMATICOS = {
            (3, 22): "clarone",
            (4, 23): "choro",
            (4, 30): "jazz",
            (5, 24): "tecladista",
            (5, 25): "reggae",
            (6, 14): "marisa_monte",
            (7, 13): "rock",
            (8, 11): "hiphop",
            (8, 22): "folclore",
            (10, 17): "mpb",
            (11, 22): "musico",
            (12, 2): "samba",
            (12, 11): "tango",
            (12, 13): "forro",
        }
        
        if dia_mes in DIAS_TEMATICOS:
            tema = DIAS_TEMATICOS[dia_mes]
            db_meta = self.get_track_metadata(music_paths)
            tema_count = 0
            for path in music_paths:
                if pertence_ao_tema_dict(db_meta, path, tema):
                    tema_count += 1
            
            total_musicas = len(music_paths)
            if total_musicas > 0:
                pct_tema = tema_count / total_musicas
                # Cota de 60% para Rock (mínimo de 55% tolerado)
                # Cota de 50% para outros temas (mínimo de 45% tolerado)
                cota_exigida = 0.60 if tema == "rock" else 0.50
                limiar_tolerancia = 0.55 if tema == "rock" else 0.45
                
                if pct_tema < limiar_tolerancia:
                    violations.append(
                        f"Quantidade de músicas do tema '{tema}' abaixo do regulamentar para a data comemorativa ({date_context.day:02d}/{mes_atual:02d}). "
                        f"Proporção atual: {pct_tema*100:.1f}% (Mínimo exigido: {cota_exigida*100:.0f}%)."
                    )

        return violations

# Instância singleton global do validador de conformidade
compliance_validator_instance = ComplianceValidator()
