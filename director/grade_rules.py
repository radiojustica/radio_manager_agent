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
        "max_historico_artistas":   80,    # Expandido de 15 para 80
        "max_historico_musicas":    200,   # Novo limite de 200 músicas
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
            except: pass
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
    "Ensolarado": ["pop / rock internacional", "rock nacional", "regional nordestina", "mpb / contemporâneo", "pop"],
    "Chuvoso": ["bossa nova / jazz", "jazz", "mpb / clássico", "blues", "instrumental"],
    "Nublado": ["mpb / contemporâneo", "reggae / pop", "soul / funk", "rock nacional", "mpb"],
}

def estilos_para_mood(mood: str | None = None) -> list[str]:
    mood = mood or CFG.get("mood_padrao", "Ensolarado")
    return MOODS.get(mood, MOODS["Ensolarado"])

DIAS_SEMANA = {0: "SEGUNDA", 1: "TERCA", 2: "QUARTA", 3: "QUINTA", 4: "SEXTA", 5: "SABADO", 6: "DOMINGO"}

def pasta_boletins_hoje() -> str:
    """Retorna o caminho da pasta de boletins do dia atual (usando timezone local correto)."""
    # Usa datetime.now() mas com tratamento de timezone para garantir o dia correto
    # Se o servidor está em Brasil (UTC-3), o dia sempre será o correto
    agora = datetime.now()
    dia_nome = DIAS_SEMANA.get(agora.weekday(), "SEGUNDA")
    return os.path.join(CFG["pasta_boletins_raiz"], dia_nome)

def listar_mp3(pasta: str) -> list[str]:
    try:
        if not pasta or not os.path.exists(pasta): return []
        # Filtro central: ignora arquivos com '?' no nome que crasham o leitor
        return [os.path.join(pasta, f) for f in os.listdir(pasta) if f.lower().endswith(".mp3") and "?" not in f]
    except: return []

def carregar_assets_apoio() -> dict:
    return {
        "vinhetas": listar_mp3(CFG["pasta_vinhetas"]),
        "spots":    listar_mp3(CFG["pasta_spots"]),
        "boletins": listar_mp3(pasta_boletins_hoje()),
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
        
        self.max_art = CFG.get("max_historico_artistas", 80)
        self.max_mus = CFG.get("max_historico_musicas", 200)
        self.historico_artistas, self.historico_musicas = self._carregar_historico()
        
        # Estado do fluxo para o "Conceito de Programação"
        self.ultimo_estilo = None

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

    def proxima(self, tipo="geral", energias_alvo=None, evitar_estilo=None):
        pool = self.pool_regional if tipo == "regional" and self.pool_regional else self.pool_geral
        if not pool:
            pool = self.pool_geral if tipo == "regional" else self.pool_regional
            if not pool: return None

        # CONCEITO: Buscamos a melhor música que se encaixe no fluxo (Vibe Match)
        # Varremos as primeiras 50 músicas da fila de prioridade
        candidatas = []
        for i, m in enumerate(pool[:50]):
            art = clean_artist_name(m.artista, m.caminho)
            
            # Pula se for repetição de artista ou música
            if art in self.historico_artistas or m.caminho in self.historico_musicas:
                continue
            
            score = 0
            # Regra de Energia (Peso 3)
            if energias_alvo and m.energia in energias_alvo: score += 3
            
            # Regra de Alternância de Estilo (Peso 2)
            if evitar_estilo and m.estilo.upper() != evitar_estilo.upper(): score += 2
            
            candidatas.append((score, i, m))
        
        if candidatas:
            # Ordena pelo score (conceito) e pega uma das melhores
            candidatas.sort(key=lambda x: x[0], reverse=True)
            # Pega aleatoriamente entre as top 3 melhores do conceito
            top_selection = candidatas[:3]
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
) -> list[str]:
    """
    Monta a grade musical aplicando o conceito de PROGRAMAÇÃO PROFISSIONAL:
    - Curva de Energia: Suave -> Pico -> Suave.
    - Alternância de Textura: Evita gêneros repetidos em sequência.
    - Quebra de Ordem Alfabética: Via Fair Shuffle e Sorteio de Conceito.
    """
    if not acervo: return []
    if assets is None: assets = carregar_assets_apoio()

    gestor = GestorFila(acervo)
    playlist: list[str] = ["#EXTM3U"]
    segundos_acumulados = 0
    contador_musicas = 0
    
    hora = hora_inicio if hora_inicio is not None else datetime.now().hour
    energias_base = obter_regras_energia_por_hora(hora)
    n_regional = CFG.get("regional_a_cada_n", 8)
    
    alvo = CFG.get("duracao_bloco_segundos", 8000)
    if duracao_alvo_s < 7200: alvo = duracao_alvo_s

    logger.info(f"[GradeRules] Gerando CONCEITO para {hora}H — Meta: {alvo}s")

    while segundos_acumulados < alvo:
        # LÓGICA DE CONCEITO: Ajusta a energia alvo dinamicamente dentro do bloco de 2h
        # Progresso do bloco (0.0 a 1.0)
        progresso = segundos_acumulados / alvo
        
        # Curva de Energia (Simulada):
        # Início (0-30%): Energias mais baixas do range
        # Meio (30-70%): Energias mais altas do range (Pico)
        # Fim (70-100%): Energias médias para transição
        if progresso < 0.3:
            e_alvo = [min(energias_base), min(energias_base) + 1]
        elif progresso < 0.7:
            e_alvo = [max(energias_base) - 1, max(energias_base)]
        else:
            e_alvo = energias_base

        tipo = "regional" if contador_musicas > 0 and contador_musicas % n_regional == 0 else "geral"
        
        # Pede a próxima música passando o conceito de energia e evitando o estilo anterior
        musica = gestor.proxima(
            tipo=tipo, 
            energias_alvo=e_alvo, 
            evitar_estilo=gestor.ultimo_estilo
        )
        
        if not musica: break

        playlist.append(musica.caminho)
        segundos_acumulados += (musica.duracao or 210)
        contador_musicas += 1

        # Inserções de apoio
        if assets.get("vinhetas") and deve_inserir_vinheta(contador_musicas):
            playlist.append(random.choice(assets["vinhetas"]))
            segundos_acumulados += CFG.get("duracao_estimada_vinheta_s", 5)

        if assets.get("spots") and deve_inserir_spot(contador_musicas):
            playlist.append(random.choice(assets["spots"]))
            segundos_acumulados += CFG.get("duracao_estimada_spot_s", 30)

        if assets.get("boletins") and deve_inserir_boletim(contador_musicas):
            playlist.append(random.choice(assets["boletins"]))
            segundos_acumulados += CFG.get("duracao_estimada_boletim_s", 120)

    return playlist

def segundos_restantes_no_bloco() -> int:
    now = datetime.now()
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


