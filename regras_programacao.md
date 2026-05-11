# Regras de Programação Omni Core V2

Este documento define os padrões obrigatórios para a geração da grade musical da Rádio TJRN. Qualquer alteração no motor de geração deve respeitar estas diretrizes.

## 1. Estrutura do Bloco (2 Horas)
*   **Duração Alvo:** 8000 segundos (~2h13) para garantir margem de segurança contra silêncio.
*   **Vinhetas:** Inserção obrigatória a cada **1 música**.
*   **Spots/Comerciais:** Inserção a cada **4 músicas**.
*   **Boletins Informativos:** Inserção a cada **8 músicas**.
*   **Quota Regional:** Pelo menos **1 música regional** a cada 8 faixas (~30 min).

## 2. Anti-Repetição (Crítico)
*   **Separação de Artista:** Um artista não pode se repetir em um intervalo de **30 músicas** (aprox. 2 horas de programação).
*   **Separação de Música:** A mesma faixa não pode se repetir em um intervalo de **80 músicas** (aprox. 5 horas).
*   **Normalização:** Nomes de artistas devem ser comparados em CAIXA ALTA e sem espaços extras.
*   **Tratamento de Desconhecidos:** Caso o metadado do artista seja "Desconhecido" ou vazio, o sistema deve tentar extrair o nome do arquivo ou usar um fallback genérico, mas mantendo a restrição de repetição por título/caminho.

## 3. Dayparting (Energia Acústica)
A energia das músicas deve seguir o clima do dia e a faixa horária:
*   **00H - 06H (Madrugada):** Energias 1, 2, 3 (Calmo/Suave).
*   **06H - 10H (Manhã):** Energias 4, 5 (Animado/Despertar).
*   **10H - 16H (Meio do dia):** Energias 3, 4 (Moderado/Trabalho).
*   **16H - 20H (Tarde):** Energias 4, 5 (Animado/Retorno).
*   **20H - 00H (Noite):** Energias 1, 2, 3 (Tranquilo/Relaxante).

## 4. Moods (Estilos por Clima)
*   **Ensolarado:** Pop/Rock Internacional, Rock Nacional, Regional, MPB Contemporânea.
*   **Chuvoso:** Bossa Nova, Jazz, MPB Clássico, Blues, Instrumental.
*   **Nublado:** MPB Contemporânea, Reggae, Soul, Rock Nacional.

## 5. Auditoria e Correção
*   **Logs Diários:** Todos os blocos gerados devem ser auditados.
*   **Refazer Grade:** Se um bloco apresentar mais de 2 repetições de artista em menos de 1 hora, o arquivo `.m3u` deve ser deletado e gerado novamente com novas sementes de randomização.
