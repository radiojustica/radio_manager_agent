import os
from core.database import SessionLocal, engine
from core.models import Base, Musica
from datetime import datetime

# Garante que as tabelas existam
Base.metadata.create_all(bind=engine)

def sincronizar_fisico():
    PASTA_MUSICAS = r"D:\RADIO\MUSICAS"
    print(f"Iniciando sincronização física em {PASTA_MUSICAS}...")
    
    db = SessionLocal()
    novos = 0
    existentes = 0
    removidos = 0
    
    # Mapeia caminhos no banco para detecção de removidos
    caminhos_db = {m.caminho for m in db.query(Musica.caminho).all()}
    caminhos_fisicos = set()

    try:
        for root, _, files in os.walk(PASTA_MUSICAS):
            for file in files:
                if file.lower().endswith('.mp3'):
                    caminho = os.path.join(root, file)
                    caminhos_fisicos.add(caminho)
                    
                    if caminho not in caminhos_db:
                        nova_musica = Musica(
                            caminho=caminho,
                            titulo=file.replace(".mp3", ""),
                            artista=file.split(" - ")[0] if " - " in file else "Desconhecido",
                            estilo="outros",
                            energia=3,
                            auditado_acustica=False,
                            redflag=False,
                            ultima_reproducao=datetime.utcnow()
                        )
                        db.add(nova_musica)
                        novos += 1
                    else:
                        existentes += 1
            
            if (novos + existentes) % 500 == 0:
                db.commit()

        # Opcional: Marcar como removido ou deletar do banco o que não está mais no disco
        for caminho_zumbi in caminhos_db - caminhos_fisicos:
            db.query(Musica).filter(Musica.caminho == caminho_zumbi).delete()
            removidos += 1
            
        db.commit()
        print(f"SINCRONIZAÇÃO CONCLUÍDA:")
        print(f"> {novos} novos arquivos adicionados.")
        print(f"> {existentes} arquivos já conhecidos.")
        print(f"> {removidos} registros removidos (não encontrados no disco).")
        
    except Exception as e:
        db.rollback()
        print(f"ERRO durante a sincronização: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    sincronizar_fisico()


