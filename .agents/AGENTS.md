# Regras do Workspace - Rádio TJRN

As regras abaixo são **inegociáveis** para todos os agentes trabalhando neste workspace:

1.  **Preservação Absoluta de Documentos:**
    *   Nenhum documento original (roteiros, textos, planilhas de controle, áudios históricos ou arquivos institucionais) pode ser **apagado, movido ou alterado** sem autorização expressa e direta do usuário.
    *   Arquivos em unidades compartilhadas ou de trabalho (como o Google Drive montado `H:\` ou o servidor `D:\`) são estritamente de apenas-leitura para ações de exclusão ou alteração.

2.  **Limpeza Estrita:**
    *   Os robôs da Fábrica de IA e scripts de pipeline local estão autorizados a apagar **apenas** os arquivos de apoio temporários locais que eles próprios criarem (`f.unlink()` locais) na pasta `/workspace` ou cache.
