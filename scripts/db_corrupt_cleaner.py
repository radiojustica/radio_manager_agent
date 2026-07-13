
import sqlite3
import os
from core.database import SessionLocal
from core.models import Musica
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DBCleaner")

def is_corrupted(text):
    if not text:
        return False
    if len(text) < 2:
        return False
    # Checa se todos os caracteres em índices pares são 'A'
    evens = text[0::2]
    return all(c == 'A' for c in evens)

def decode_text(text):
    if is_corrupted(text):
        return text[1::2]
    return text

def run_cleanup():
    db = SessionLocal()
    musicas = db.query(Musica).all()
    
    fixed_artist = 0
    fixed_title = 0
    
    for m in musicas:
        modified = False
        
        if is_corrupted(m.artista):
            m.artista = decode_text(m.artista)
            fixed_artist += 1
            modified = True
            
        if is_corrupted(m.titulo):
            m.titulo = decode_text(m.titulo)
            fixed_title += 1
            modified = True
            
        if modified:
            db.add(m)
            
    db.commit()
    logger.info(f"Limpeza concluída! Artistas corrigidos: {fixed_artist}, Títulos corrigidos: {fixed_title}")

if __name__ == '__main__':
    run_cleanup()
