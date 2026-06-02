"""
Motor de Regras Musicais — Omni Core V2
========================================
Toda a inteligência de montagem de grade com estratégias anti-repetição,
dayparting de energia e quotas regionais.
"""

import os
import json
import random
import logging
from datetime import datetime, timezone
from core.time_utils import now_local
from scripts.artist_cleaner import clean_artist_name

logger = logging.getLogger("OmniCore.GradeRules")

# ===========================================================================
# CARREGAMENTO DE CONFIGURAÇÃO
# ===========================================================================

def _carregar_config() -> dict:
    """Lê o bloco 'grade' de settings.json. Fallback para valores padrão se falhar."""
    defaults = {
        "pasta_musicas":            r"D:\RADIO\MUSICAS",
        "pasta_programacao":        r"D:\RADIO\PROGRAMACAO",
        "pasta_vinhetas":           r"D:\RADIO\VINHETAS",
        "pasta_spots":              r"D:\RADIO\SPOTS",
        "pasta_boletins_raiz":      r"D:\SERVIDOR\BOLETINS",
        "pasta_quarentena":         r"D:\RADIO\QUARENTENA_TJ",
        "mood_padrao":              "Ensolarado",
        "duracao_bloco_segundos":   8000,  # Aumentado para 8000s (Segurança contra silêncio)
        "min_bloco_extra_segundos": 1800,
        "vinheta_a_cada_n":         1,
        "spot_a_cada_n":            4,
        "boletim_a_cada_n":         8,
        "max_historico_artistas":   30,    # Reduzido de 80 para 30
        "max_historico_musicas":    80,    # Reduzido de 200 para 80
        "regional_a_cada_n":        8,     # 1 regional a cada ~30min (8 faixas)
        "duracao_estimada_musica_s":  210,
        "duracao_estimada_vinheta_s": 5,
        "duracao_estimada_spot_s":    30,
        "duracao_estimada_boletim_s": 120,
    }
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "settings.json"),
        os.path.join(os.getcwd(), "config", "settings.json"),
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                cfg = {**defaults, **data.get("grade", {})}
                return cfg
            except Exception as e:
                logger.error(f"Erro ao ler settings.json em {path}: {e}")
    return defaults

CFG = _carregar_config()

def recarregar_config() -> dict:
    global CFG
    CFG = _carregar_config()
    return CFG

# ===========================================================================
# LÓGICA DE DAYPARTING (ENERGIA POR HORA)
# ===========================================================================

def obter_regras_energia_por_hora(hora: int) -> list[int]:
    """Define os limites dinâmicos de energia (Dayparting) conforme pedido pelo usuário."""
    if 0 <= hora < 6: return [1, 2, 3]    # Madrugada: Calmo
    if 6 <= hora < 10: return [4, 5]     # Manhã: Animado/Energético
    if 10 <= hora < 16: return [3, 4]    # Meio do dia: Moderado
    if 16 <= hora < 20: return [4, 5]    # Tarde: Animado
    return [1, 2, 3]                     # Noite: Tranquilo

# ===========================================================================
# REGRAS DE MOOD → ESTILOS MUSICAIS
# ===========================================================================

MOODS: dict[str, list[str]] = {
    "Ensolarado": [
        "pop / rock internacional", "rock nacional", "regional nordestina", 
        "mpb / contemporâneo", "pop", "surf rock", "reggae / pop"
    ],
    "Chuvoso": [
        "bossa nova / jazz", "jazz", "mpb / clássico", "blues", 
        "instrumental", "soul / jazz", "chillout"
    ],
    "Nublado": [
        "mpb / contemporâneo", "reggae / pop", "soul / funk", 
        "rock nacional", "mpb", "pop rock", "indie"
    ],
}

def estilos_para_mood(mood: str | None = None) -> list[str]:
    mood = mood or CFG.get("mood_padrao", "Ensolarado")
    return MOODS.get(mood, MOODS["Ensolarado"])

DIAS_SEMANA = {0: "SEGUNDA", 1: "TERCA", 2: "QUARTA", 3: "QUINTA", 4: "SEXTA", 5: "SABADO", 6: "DOMINGO"}

def carregar_grade_do_banco() -> dict:
    """Carrega a grade horária semanal da tabela system_configs do SQLite."""
    import sqlite3
    from core.database import DB_PATH
    try:
        if os.path.exists(DB_PATH):
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM system_configs WHERE key = 'weekly_schedule'")
            row = cursor.fetchone()
            conn.close()
            if row:
                return json.loads(row[0])
    except Exception as e:
        logger.error(f"Erro ao carregar grade do banco de dados: {e}")
    
    # Fallback da grade padrão se falhar
    return {
        "legendas": {
            "SPOT": {"tipo": "vinheta", "duracao": "curto", "pasta": "D:\\RADIO\\SPOTS"},
            "VH_INSTITUCIONAL": {"tipo": "vinheta", "duracao": "curto", "pasta": "D:\\RADIO\\VINHETAS"},
            "BOLETIM": {"tipo": "boletim", "duracao": "1-2 min", "pasta_raiz": "D:\\SERVIDOR\\BOLETINS"},
            "PROGRAMAS": {
                "GIRO_NAS_COMARCAS": {"duracao_minutos": 10, "pasta": "D:\\SERVIDOR\\PROGRAMAS\\PROGRAMA_40\\GIRONASCOMARCAS"},
                "MEMORIA_DA_JUSTICA": {"duracao_minutos": 40, "pasta": "D:\\SERVIDOR\\PROGRAMAS\\PROGRAMA_40\\MEMORIA"},
                "LEVEMENTE": {"duracao_minutos": 40, "pasta": "D:\\SERVIDOR\\PROGRAMAS\\PROGRAMA_40\\LEVEMENTE"},
                "NOTICIAS_DO_JUDICIARIO": {"duracao_minutos": 5, "pasta": "D:\\SERVIDOR\\DRIVE\\RADIO TJRN CONTEÚDO\\NOT JUDICIARIO (5 MIN)"}
            }
        },
        "grade_diaria": {
            "madrugada_manha": {
                "inicio": "00:01",
                "fim": "08:30",
                "loop": {"intervalo_minutos": 30, "estrutura": ["SPOT", "BOLETIM", "SPOT"]}
            },
            "noite_madrugada": {
                "inicio": "18:00",
                "fim": "23:59",
                "loop": {"intervalo_minutos": 30, "estrutura": ["SPOT", "BOLETIM", "SPOT"]}
            }
        },
        "excecoes_diurnas": {
            "segunda": {
                "09:00": ["SPOT", "BOLETIM", "SPOT", "MUSICA"],
                "10:00": ["SPOT", "BOLETIM", "SPOT", "MUSICA"],
                "10:45": ["SPOT", "NOTICIAS_DO_JUDICIARIO", "SPOT", "MUSICA"],
                "11:30": ["SPOT", "VH_INSTITUCIONAL", "SPOT", "MUSICA"],
                "12:00": ["SPOT", "BOLETIM", "SPOT", "MUSICA"],
                "16:00": ["VH_INSTITUCIONAL", "MEMORIA_DA_JUSTICA", "MUSICA"],
                "17:30": ["NOTICIAS_DO_JUDICIARIO"]
            },
            "terca": {
                "09:00": ["SPOT", "VH_INSTITUCIONAL", "MUSICA"],
                "10:00": ["SPOT", "VH_INSTITUCIONAL", "MUSICA"],
                "10:45": ["SPOT", "NOTICIAS_DO_JUDICIARIO", "SPOT", "MUSICA"],
                "11:30": ["SPOT", "BOLETIM", "SPOT", "MUSICA"],
                "12:00": ["SPOT", "BOLETIM", "SPOT", "MUSICA"],
                "15:00": ["SPOT", "BOLETIM", "GIRO_NAS_COMARCAS", "MUSICA"],
                "17:30": ["NOTICIAS_DO_JUDICIARIO"]
            },
            "quarta": {
                "09:00": ["SPOT", "BOLETIM", "SPOT", "MUSICA"],
                "10:00": ["SPOT", "BOLETIM", "SPOT", "MUSICA"],
                "10:45": ["SPOT", "NOTICIAS_DO_JUDICIARIO", "SPOT", "MUSICA"],
                "11:30": ["SPOT", "BOLETIM", "SPOT", "MUSICA"],
                "12:00": ["SPOT", "BOLETIM", "SPOT", "MUSICA"],
                "17:30": ["NOTICIAS_DO_JUDICIARIO"]
            },
            "quinta": {
                "09:00": ["SPOT", "VH_INSTITUCIONAL", "LEVEMENTE", "MUSICA"],
                "10:00": ["SPOT", "BOLETIM", "SPOT", "MUSICA"],
                "10:45": ["SPOT", "NOTICIAS_DO_JUDICIARIO", "SPOT", "MUSICA"],
                "11:30": ["SPOT", "BOLETIM", "SPOT", "MUSICA"],
                "12:00": ["SPOT", "BOLETIM", "SPOT", "MUSICA"],
                "17:30": ["NOTICIAS_DO_JUDICIARIO"]
            },
            "sexta": {
                "09:00": ["SPOT", "VH_INSTITUCIONAL", "MUSICA"],
                "10:00": ["SPOT", "BOLETIM", "SPOT", "MUSICA"],
                "10:45": ["SPOT", "NOTICIAS_DO_JUDICIARIO", "SPOT", "MUSICA"],
                "11:30": ["SPOT", "VH_INSTITUCIONAL", "SPOT", "MUSICA"],
                "12:00": ["SPOT", "VH_INSTITUCIONAL", "MUSICA"],
                "17:30": ["NOTICIAS_DO_JUDICIARIO"]
            }
        },
        "final_de_semana": {
            "sabado": {
                "06:00_15:00": {"loop": {"intervalo_minutos": 30, "estrutura": ["SPOT", "BOLETIM", "SPOT", "MUSICA"]}},
                "15:00_18:00": {"loop": {"intervalo_minutos": 30, "estrutura": ["SPOT", "BOLETIM", "SPOT", "MUSICA"]}}
            },
            "domingo": {
                "06:00_15:00": {"loop": {"intervalo_minutos": 30, "estrutura": ["SPOT", "BOLETIM", "SPOT", "MUSICA"]}},
                "15:00_18:00": {"loop": {"intervalo_minutos": 30, "estrutura": ["SPOT", "BOLETIM", "SPOT", "MUSICA"]}}
            }
        }
    }

def obter_boletins_dia(data_execucao=None) -> list[str]:
    """Retorna a lista de boletins mp3 correspondentes ao dia ou randômico se for fim de semana."""
    if data_execucao is None:
        data_execucao = now_local()
    
    dia_semana = data_execucao.weekday()  # 0=Segunda, ..., 6=Domingo
    dias_uteis = ["SEGUNDA", "TERCA", "QUARTA", "QUINTA", "SEXTA"]
    
    pasta_raiz = CFG.get("pasta_boletins_raiz", r"D:\SERVIDOR\BOLETINS")
    
    if dia_semana < 5:  # Segunda a Sexta
        dia_nome = dias_uteis[dia_semana]
        pasta = os.path.join(pasta_raiz, dia_nome)
        return listar_mp3(pasta)
    else:  # Sábado e Domingo
        # Pega boletins randomicamente de todos os dias (Segunda a Sexta)
        todos = []
        for dia in dias_uteis:
            pasta = os.path.join(pasta_raiz, dia)
            todos.extend(listar_mp3(pasta))
        return todos

def obter_programa_mais_recente(pasta: str) -> str | None:
    """Varre recursivamente a pasta e localiza o arquivo .mp3 mais recente."""
    if not pasta or not os.path.exists(pasta):
        return None
    candidatos = []
    for root, _, files in os.walk(pasta):
        for f in files:
            if f.lower().endswith(".mp3") and "?" not in f:
                caminho = os.path.join(root, f)
                try:
                    mtime = os.path.getmtime(caminho)
                    candidatos.append((caminho, mtime))
                except Exception:
                    pass
    if not candidatos:
        return None
    # Ordena pelo tempo de modificação decrescente (mais recente primeiro)
    candidatos.sort(key=lambda x: x[1], reverse=True)
    return candidatos[0][0]

def pasta_boletins_hoje() -> str:
    """Mantido para compatibilidade, retorna a pasta de hoje."""
    agora = now_local()
    dia_nome = DIAS_SEMANA.get(agora.weekday(), "SEGUNDA")
    return os.path.join(CFG["pasta_boletins_raiz"], dia_nome)

def listar_mp3(pasta: str) -> list[str]:
    try:
        if not pasta or not os.path.exists(pasta): return []
        # Filtro central: ignora arquivos com '?' no nome que crasham o leitor
        return [os.path.join(pasta, f) for f in os.listdir(pasta) if f.lower().endswith(".mp3") and "?" not in f]
    except Exception: return []

def carregar_assets_apoio(data_execucao=None) -> dict:
    return {
        "vinhetas": listar_mp3(CFG["pasta_vinhetas"]),
        "spots":    listar_mp3(CFG["pasta_spots"]),
        "boletins": obter_boletins_dia(data_execucao),
    }


# ===========================================================================
# GESTOR DE FILA (ESTRATÉGIA ANTI-REPETIÇÃO E DAYPARTING)
# ===========================================================================

HISTORICO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "engine_history.json")

class GestorFila:
    def __init__(self, acervo: list):
        self.pool_geral = []
        self.pool_regional = []
        
        for musica in acervo:
            if "?" in musica.caminho: continue
            if r"REGIONAL" in musica.caminho.upper():
                self.pool_regional.append(musica)
            else:
                self.pool_geral.append(musica)

        # FAIR SHUFFLE: Para quebrar a ordem alfabética do banco, 
        # nós embaralhamos as músicas que têm o mesmo peso (mesma quantidade de execuções).
        self.pool_geral = self._shuffle_by_priority(self.pool_geral)
        self.pool_regional = self._shuffle_by_priority(self.pool_regional)
        
        self.max_art = CFG.get("max_historico_artistas", 30)
        self.max_mus = CFG.get("max_historico_musicas", 80)
        self.historico_artistas, self.historico_musicas = self._carregar_historico()
        
        # Estado do fluxo para o "Conceito de Programação"
        self.ultimo_estilo = None

    def _carregar_historico(self):
        """Carrega o histórico persistente do disco."""
        try:
            if os.path.exists(HISTORICO_PATH):
                with open(HISTORICO_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("artistas", []), data.get("musicas", [])
        except Exception:
            pass
        return [], []

    def _atualizar_historico(self, artista, caminho):
        """Adiciona ao histórico e salva no disco."""
        art = clean_artist_name(artista, caminho)
        
        if art not in self.historico_artistas:
            self.historico_artistas.append(art)
        if caminho not in self.historico_musicas:
            self.historico_musicas.append(caminho)
        
        # Trim
        if len(self.historico_artistas) > self.max_art:
            self.historico_artistas.pop(0)
        if len(self.historico_musicas) > self.max_mus:
            self.historico_musicas.pop(0)
            
        try:
            os.makedirs(os.path.dirname(HISTORICO_PATH), exist_ok=True)
            with open(HISTORICO_PATH, "w", encoding="utf-8") as f:
                json.dump({
                    "artistas": self.historico_artistas,
                    "musicas": self.historico_musicas,
                    "updated_at": now_local().isoformat()
                }, f, indent=4)
        except Exception:
            pass

    def _shuffle_by_priority(self, lista):
        """Embaralha itens que possuem o mesmo nível de prioridade (vezes_tocada)."""
        if not lista: return []
        # Agrupa por vezes_tocada
        buckets = {}
        for m in lista:
            buckets.setdefault(m.vezes_tocada, []).append(m)
        
        resultado = []
        # Ordena as chaves (vezes_tocada) e embaralha cada balde individualmente
        for v in sorted(buckets.keys()):
            sub_lista = buckets[v]
            random.shuffle(sub_lista)
            resultado.extend(sub_lista)
        return resultado

    def proxima(self, tipo="geral", energias_alvo=None, evitar_estilo=None, mood_alvo=None):
        pool = self.pool_regional if tipo == "regional" and self.pool_regional else self.pool_geral
        if not pool:
            pool = self.pool_geral if tipo == "regional" else self.pool_regional
            if not pool: return None

        # Estilos preferidos para o mood atual
        estilos_preferidos = estilos_para_mood(mood_alvo) if mood_alvo else []

        # CONCEITO: Buscamos a melhor música que se encaixe no fluxo (Vibe Match)
        # Varremos as primeiras 100 músicas da fila de prioridade
        candidatas = []
        for i, m in enumerate(pool[:100]):
            art = clean_artist_name(m.artista, m.caminho)
            
            # Pula se for repetição de artista ou música
            if art in self.historico_artistas or m.caminho in self.historico_musicas:
                continue
            
            score = 0
            # Regra de Energia (Peso 3)
            if energias_alvo and m.energia in energias_alvo: score += 3
            
            # Regra de Mood/Estilo (Peso 4) - Prioridade máxima para aderência ao clima
            if mood_alvo and m.estilo.lower() in [e.lower() for e in estilos_preferidos]:
                score += 4
            
            # Regra de Alternância de Estilo (Peso 2)
            if evitar_estilo and m.estilo.upper() != evitar_estilo.upper(): score += 2
            
            candidatas.append((score, i, m))
        
        if candidatas:
            # Ordena pelo score (conceito) e pega uma das melhores
            candidatas.sort(key=lambda x: x[0], reverse=True)
            # Pega aleatoriamente entre as top 5 melhores do conceito
            top_selection = candidatas[:5]
            score, idx_original, m = random.choice(top_selection)
            
            self._atualizar_historico(m.artista, m.caminho)
            self.ultimo_estilo = m.estilo
            return pool.pop(idx_original)

        # Fallback de segurança: pega a primeira da fila (respeitando apenas repetição)
        for i, m in enumerate(pool):
            art = clean_artist_name(m.artista, m.caminho)
            if art not in self.historico_artistas and m.caminho not in self.historico_musicas:
                self._atualizar_historico(m.artista, m.caminho)
                return pool.pop(i)

        return pool.pop(0)

# ===========================================================================
# REGRAS DE INSERÇÃO
# ===========================================================================

def deve_inserir_vinheta(contador_musicas: int) -> bool:
    n = CFG.get("vinheta_a_cada_n", 1)
    return contador_musicas % n == 0 and n > 0

def deve_inserir_spot(contador_musicas: int) -> bool:
    n = CFG.get("spot_a_cada_n", 4)
    return contador_musicas % n == 0 and n > 0

def deve_inserir_boletim(contador_musicas: int) -> bool:
    n = CFG.get("boletim_a_cada_n", 8)
    return contador_musicas % n == 0 and n > 0

# ===========================================================================
# MONTAGEM DE BLOCO (ESTRATÉGIA DAYPARTING + QUOTAS)
# ===========================================================================

def montar_bloco(
    acervo: list,
    duracao_alvo_s: int,
    assets: dict | None = None,
    hora_inicio: int | None = None,
    mood: str | None = None,
) -> list[str]:
    """
    Monta a grade musical baseada no dia da semana e na grade configurada no banco de dados.
    Aplica conceito de programação profissional, curva de energia, e insere programas nos horários previstos.
    """
    if not acervo: return []
    
    # Determina a data exata de execução do bloco para saber o dia da semana
    agora = now_local()
    if hora_inicio is not None:
        # Se a hora de início for menor que a hora atual por mais de 4h,
        # significa que a geração é para o bloco da madrugada do dia seguinte.
        if hora_inicio < agora.hour - 4:
            from datetime import timedelta
            data_bloco = agora + timedelta(days=1)
        else:
            data_bloco = agora
    else:
        data_bloco = agora
        hora_inicio = agora.hour

    dias_map = {
        0: "segunda",
        1: "terca",
        2: "quarta",
        3: "quinta",
        4: "sexta",
        5: "sabado",
        6: "domingo"
    }
    dia_nome = dias_map.get(data_bloco.weekday(), "segunda")

    # Carrega a grade ativa do SQLite
    grade = carregar_grade_do_banco()
    
    # Carrega os assets baseados no dia do bloco
    if assets is None: 
        assets = carregar_assets_apoio(data_bloco)

    gestor = GestorFila(acervo)
    playlist: list[str] = ["#EXTM3U"]
    segundos_acumulados = 0
    contador_musicas = 0
    
    energias_base = obter_regras_energia_por_hora(hora_inicio)
    n_regional = CFG.get("regional_a_cada_n", 8)
    
    # Determina a meta de duração do bloco
    alvo = CFG.get("duracao_bloco_segundos", 8000)
    if duracao_alvo_s < 7200: alvo = duracao_alvo_s

    # Mapeia eventos horários agendados
    minuto_inicio_dia = hora_inicio * 60
    minuto_fim_dia = minuto_inicio_dia + (alvo // 60)
    
    eventos_agendados = []
    minutos_excecao = set()
    
    # Se houver exceções diurnas para o dia atual no banco, nós as lemos primeiro
    excecoes = {}
    if dia_nome not in ["sabado", "domingo"]:
        excecoes = grade.get("excecoes_diurnas", {}).get(dia_nome, {})
        for hora_str, itens in excecoes.items():
            try:
                h, m_val = map(int, hora_str.split(":"))
                m_abs = h * 60 + m_val
                if minuto_inicio_dia <= m_abs < minuto_fim_dia:
                    eventos_agendados.append((m_abs, hora_str, itens))
                    minutos_excecao.add(m_abs)
            except Exception as ex:
                logger.error(f"Erro ao parsear horario de excecao {hora_str}: {ex}")

    # Adiciona os loops recorrentes de apoio em todo o período do bloco (todos os dias)
    # 1. Boletins a cada 30 minutos (XX:00 e XX:30)
    # 2. Spots a cada 30 minutos com 20 minutos de diferença (XX:20 e XX:50)
    for m in range(minuto_inicio_dia, minuto_fim_dia):
        # Se aquele minuto já possui uma exceção diurna específica agendada, respeitamos
        if m in minutos_excecao:
            continue
            
        # Boletim a cada meia hora
        if m % 30 == 0:
            eventos_agendados.append((m, f"{m//60:02d}:{(m%60):02d}", ["SPOT", "BOLETIM", "SPOT"]))
        # Spot a cada meia hora com 20 minutos de diferença para os boletins (minutos terminando em 20 ou 50)
        elif (m - 20) % 30 == 0:
            eventos_agendados.append((m, f"{m//60:02d}:{(m%60):02d}", ["SPOT"]))
            
    # Ordena eventos agendados cronologicamente
    eventos_agendados.sort(key=lambda x: x[0])
    
    logger.info(f"[GradeRules] Gerando bloco para {dia_nome.upper()} às {hora_inicio:02d}H. Eventos no bloco: {[e[1] for e in eventos_agendados]}")

    # Processa os eventos ordenados na linha do tempo
    for m_abs, hora_str, sequencia in eventos_agendados:
        segundos_alvo_evento = (m_abs - minuto_inicio_dia) * 60
        
        # Preenche com músicas normais até atingir o tempo correspondente ao evento
        while segundos_acumulados + 120 < segundos_alvo_evento and segundos_acumulados < alvo:
            progresso = segundos_acumulados / alvo
            if progresso < 0.3:
                e_alvo = [min(energias_base), min(energias_base) + 1]
            elif progresso < 0.7:
                e_alvo = [max(energias_base) - 1, max(energias_base)]
            else:
                e_alvo = energias_base

            tipo = "regional" if contador_musicas > 0 and contador_musicas % n_regional == 0 else "geral"
            musica = gestor.proxima(
                tipo=tipo, 
                energias_alvo=e_alvo, 
                evitar_estilo=gestor.ultimo_estilo,
                mood_alvo=mood
            )
            
            if not musica: 
                break

            playlist.append(musica.caminho)
            segundos_acumulados += (musica.duracao or 210)
            contador_musicas += 1

            # Inserções de apoio padrão a cada N faixas
            if assets.get("vinhetas") and deve_inserir_vinheta(contador_musicas):
                playlist.append(random.choice(assets["vinhetas"]))
                segundos_acumulados += CFG.get("duracao_estimada_vinheta_s", 5)

            if assets.get("spots") and deve_inserir_spot(contador_musicas):
                playlist.append(random.choice(assets["spots"]))
                segundos_acumulados += CFG.get("duracao_estimada_spot_s", 30)

        # Insere a sequência programada do evento
        logger.info(f"[GradeRules] Inserindo sequencia de evento agendado ({hora_str}): {sequencia}")
        for item in sequencia:
            if item == "MUSICA":
                continue
                
            caminho_item = None
            duracao_estimada = 0
            
            if item == "SPOT":
                if assets.get("spots"):
                    caminho_item = random.choice(assets["spots"])
                    duracao_estimada = CFG.get("duracao_estimada_spot_s", 30)
            elif item == "VH_INSTITUCIONAL":
                if assets.get("vinhetas"):
                    caminho_item = random.choice(assets["vinhetas"])
                    duracao_estimada = CFG.get("duracao_estimada_vinheta_s", 5)
            elif item == "BOLETIM":
                if assets.get("boletins"):
                    caminho_item = random.choice(assets["boletins"])
                    duracao_estimada = CFG.get("duracao_estimada_boletim_s", 120)
            elif item in ["GIRO_NAS_COMARCAS", "MEMORIA_DA_JUSTICA", "LEVEMENTE", "NOTICIAS_DO_JUDICIARIO"]:
                # Obtém a configuração de pasta do programa na grade
                prog_cfg = grade.get("legendas", {}).get("PROGRAMAS", {}).get(item, {})
                pasta_prog = prog_cfg.get("pasta", "")
                
                # Adapta dinamicamente a pasta do NJUD para buscar o jornal local sincronizado por dia da semana
                if item == "NOTICIAS_DO_JUDICIARIO":
                    pasta_prog = os.path.join(r"D:\SERVIDOR\PROGRAMAS\NOTICIAS_DO_JUDICIARIO", dia_nome.upper())
                
                caminho_item = obter_programa_mais_recente(pasta_prog)
                duracao_estimada = prog_cfg.get("duracao_minutos", 5) * 60
                
                if caminho_item:
                    logger.info(f"[GradeRules] Programa '{item}' injetado com sucesso: {caminho_item}")
                else:
                    logger.warning(f"[GradeRules] Nao foi possivel encontrar arquivo em '{pasta_prog}' para '{item}'. Fallback para musica.")
            
            if caminho_item:
                playlist.append(caminho_item)
                segundos_acumulados += duracao_estimada

    # Se ainda sobrar tempo no bloco, preenche até a meta
    while segundos_acumulados < alvo:
        progresso = segundos_acumulados / alvo
        if progresso < 0.3:
            e_alvo = [min(energias_base), min(energias_base) + 1]
        elif progresso < 0.7:
            e_alvo = [max(energias_base) - 1, max(energias_base)]
        else:
            e_alvo = energias_base

        tipo = "regional" if contador_musicas > 0 and contador_musicas % n_regional == 0 else "geral"
        musica = gestor.proxima(
            tipo=tipo, 
            energias_alvo=e_alvo, 
            evitar_estilo=gestor.ultimo_estilo,
            mood_alvo=mood
        )
        
        if not musica: 
            break

        playlist.append(musica.caminho)
        segundos_acumulados += (musica.duracao or 210)
        contador_musicas += 1

        if assets.get("vinhetas") and deve_inserir_vinheta(contador_musicas):
            playlist.append(random.choice(assets["vinhetas"]))
            segundos_acumulados += CFG.get("duracao_estimada_vinheta_s", 5)

        if assets.get("spots") and deve_inserir_spot(contador_musicas):
            playlist.append(random.choice(assets["spots"]))
            segundos_acumulados += CFG.get("duracao_estimada_spot_s", 30)

    return playlist

def segundos_restantes_no_bloco() -> int:
    now = now_local()
    proximo_bloco_hora = ((now.hour // 2) + 1) * 2
    from datetime import timedelta
    proximo_dt = now.replace(hour=proximo_bloco_hora % 24, minute=0, second=0, microsecond=0)
    if proximo_bloco_hora >= 24: proximo_dt += timedelta(days=1)
    faltam = int((proximo_dt - now).total_seconds())
    minimo = CFG.get("min_bloco_extra_segundos", 1800)
    return max(faltam, minimo)

def regras_ativas() -> dict:
    return {
        "config": CFG,
        "moods": MOODS,
        "assets": {
            "vinhetas": len(listar_mp3(CFG["pasta_vinhetas"])),
            "spots":    len(listar_mp3(CFG["pasta_spots"])),
            "boletins": len(listar_mp3(pasta_boletins_hoje())),
        },
    }


