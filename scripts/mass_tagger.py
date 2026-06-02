import sqlite3
import os

DB_PATH = r"D:\RADIO\radio_omni.db"

MAPA_ARTISTAS = {
    "junho": [
        "MEIRINHOS DO FORRÓ", "Mastruz com Leite", "Luiz Gonzaga", 
        "Elino Julião", "Falamansa", "Trio Nordestino", "Dominguinhos", "Jackson do Pandeiro"
    ],
    "mulheres": [
        "VALÉRIA OLIVEIRA", "Elis Regina", "Leila Pinheiro", "Maria Bethânia", 
        "Ana Carolina", "GLORINHA OLIVEIRA", "Khrystal", "Terezinha de Jesus",
        "Elba Ramalho", "Roberta Sá", "Cátia de França", "Marinês"
    ],
    "cultura_potiguar": [
        "CARLOS ZENS", "KIKO CHAGAS", "ISAQUE GALVÃO", "Babal", "Galvão Filho", "Tanda Macedo"
    ],
    "choro_instrumental": [
        "K-Ximbinho", "Catita Choro e Gafieira", "Armandinho", "Sivuca"
    ],
    "nordestino": [
        "Alceu Valença", "Zé Ramalho", "Belchior", "Fagner", "Nação Zumbi", "Cordel do Fogo Encantado"
    ],
    "consciencia_negra": [
        "Margareth Menezes", "Ilê Aiyê", "Olodum", "Chico César", "Lazzo Matumbi"
    ]
}

def run():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    total_atualizado = 0
    
    for tag, artistas in MAPA_ARTISTAS.items():
        placeholders = ','.join(['?'] * len(artistas))
        # Case insensitive no SQLite geralmente é padrão para ASCII, mas usaremos LOWER para garantir se necessário
        # Como o banco tem acentos, vamos fazer um match aproximado ou exato via python
        # Mas via SQL:
        query = f"UPDATE musicas SET tema_especial = ? WHERE artista IN ({placeholders}) AND (tema_especial IS NULL OR tema_especial = '')"
        params = [tag] + artistas
        c.execute(query, params)
        linhas = c.rowcount
        print(f"[{tag}] Atualizadas {linhas} faixas via artista.")
        total_atualizado += linhas
        
    # Tratamento especial para o Natal (Pela palavra na música, e que não seja do Zens)
    c.execute("""
        UPDATE musicas 
        SET tema_especial = 'natal' 
        WHERE (titulo LIKE '%NATAL%' OR titulo LIKE '%NOEL%') 
        AND artista NOT LIKE '%CARLOS ZENS%'
        AND artista NOT LIKE '%BANDA FILARMÔNICA%'
        AND artista NOT LIKE '%Banda Sifônica%'
        AND (tema_especial IS NULL OR tema_especial = '')
    """)
    linhas_natal = c.rowcount
    print(f"[natal] Atualizadas {linhas_natal} faixas via título.")
    total_atualizado += linhas_natal
    
    # Tratamento para cultura potiguar pelas palavras "Natal das Dunas", "400 Anos", etc.
    c.execute("""
        UPDATE musicas 
        SET tema_especial = 'cultura_potiguar' 
        WHERE (titulo LIKE '%NATAL DAS DUNAS%' OR titulo LIKE '%NATAL 400 ANOS%')
        AND (tema_especial IS NULL OR tema_especial = '')
    """)
    linhas_potiguar_tit = c.rowcount
    print(f"[cultura_potiguar] Atualizadas {linhas_potiguar_tit} faixas via título da cidade.")
    total_atualizado += linhas_potiguar_tit
    
    conn.commit()
    conn.close()
    
    print(f"\n--- SUCESSO ---")
    print(f"Total de faixas marcadas: {total_atualizado}")

if __name__ == '__main__':
    run()
