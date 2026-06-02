import re
import unicodedata
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup

def normalize_string(s):
    """Remove acentos, converte para minusculo e remove caracteres nao-alfanumericos."""
    s = s.strip().lower()
    # Substitui caracteres comuns
    s = s.replace("&", "e").replace(" - ", "-")
    # Transforma caracteres acentuados em comuns
    s = "".join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    # Substitui espacos por hifens e mantem apenas letras, numeros e hifens
    s = s.replace(" ", "-")
    s = re.sub(r'[^a-z0-9\-]', '', s)
    # Remove hifens duplicados
    s = re.sub(r'-+', '-', s)
    return s.strip('-')

def fetch_from_letras(artista, titulo):
    """Tenta baixar a letra diretamente do letras.mus.br."""
    art_norm = normalize_string(artista)
    tit_norm = normalize_string(titulo)
    url = f"https://www.letras.mus.br/{art_norm}/{tit_norm}/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')
            soup = BeautifulSoup(html, 'html.parser')
            
            # O letras.mus.br geralmente coloca a letra em divs cnt-letra ou lyric-original
            lyric_div = soup.find('div', class_='lyric-original') or soup.find('div', class_='cnt-letra')
            if lyric_div:
                # Extrai o texto preservando as quebras de linha entre os paragrafos/divs
                paragraphs = lyric_div.find_all('p')
                if paragraphs:
                    lyrics = "\n\n".join(p.get_text("\n") for p in paragraphs)
                else:
                    lyrics = lyric_div.get_text("\n")
                return lyrics.strip()
    except Exception as e:
        pass
    return None

def fetch_from_vagalume(artista, titulo):
    """Tenta baixar a letra diretamente do vagalume.com.br."""
    art_norm = normalize_string(artista)
    tit_norm = normalize_string(titulo)
    url = f"https://www.vagalume.com.br/{art_norm}/{tit_norm}.html"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')
            soup = BeautifulSoup(html, 'html.parser')
            
            # O vagalume coloca a letra na div com id lyr_original
            lyric_div = soup.find('div', id='lyr_original')
            if lyric_div:
                # Substitui <br> por quebras de linha
                for br in lyric_div.find_all("br"):
                    br.replace_with("\n")
                return lyric_div.get_text().strip()
    except Exception as e:
        pass
    return None

def get_lyrics(artista, titulo):
    """Tenta buscar a letra da musica em diferentes portais."""
    # 1. Tenta letras.mus.br
    lyrics = fetch_from_letras(artista, titulo)
    if lyrics:
        return lyrics, "letras.mus.br"
        
    # 2. Tenta vagalume
    lyrics = fetch_from_vagalume(artista, titulo)
    if lyrics:
        return lyrics, "vagalume.com.br"
        
    return None, None

if __name__ == "__main__":
    import sys
    art = "Elba Ramalho"
    tit = "Ai Que Saudade d'Ocê"
    if len(sys.argv) > 2:
        art = sys.argv[1]
        tit = sys.argv[2]
        
    print(f"Buscando letra para: {art} - {tit}")
    letra, fonte = get_lyrics(art, tit)
    if letra:
        print(f"Encontrado via {fonte}:\n")
        print(letra[:500] + "...")
    else:
        print("Letra nao encontrada.")
