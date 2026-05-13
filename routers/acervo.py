
"""
Rotas para gestão do acervo musical.
Inclui listagem, filtros, atualização de metadados e exportação.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import Optional, List
import csv
import io
import shutil
from datetime import datetime

from core.database import get_db
from core.models import Musica
from services.guardian_service import guardian_instance
import os

router = APIRouter(prefix="/api/acervo", tags=["Acervo"])

@router.get("")
@router.get("/")
def listar_acervo(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    estilo: Optional[str] = None,
    energia_min: Optional[int] = None,
    energia_max: Optional[int] = None,
    auditado: Optional[bool] = None,
    redflag: Optional[bool] = None
):
    """
    Lista as músicas do acervo com suporte a filtros e paginação.

    Args:
        db: Sessão do banco de dados.
        page: Número da página.
        limit: Itens por página.
        search: Termo para busca em título ou artista.
        estilo: Filtro por estilo exato.
        energia_min: Energia mínima (1-5).
        energia_max: Energia máxima (1-5).
        auditado: True para auditadas, False para pendentes.
        redflag: True para bloqueadas, False para liberadas.

    Returns:
        dict com itens, total e informações de página.
    """
    query = db.query(Musica)

    if search:
        query = query.filter(
            or_(
                Musica.titulo.ilike(f"%{search}%"),
                Musica.artista.ilike(f"%{search}%")
            )
        )
    if estilo:
        query = query.filter(Musica.estilo == estilo)
    if energia_min is not None:
        query = query.filter(Musica.energia >= energia_min)
    if energia_max is not None:
        query = query.filter(Musica.energia <= energia_max)
    if auditado is not None:
        query = query.filter(Musica.auditado_acustica == auditado)
    if redflag is not None:
        query = query.filter(Musica.redflag == redflag)

    total = query.count()
    items = query.offset((page - 1) * limit).limit(limit).all()

    return {
        "items": [item.to_dict() for item in items],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    }

@router.get("/estilos")
def listar_estilos(db: Session = Depends(get_db)):
    """
    Retorna a lista de estilos distintos presentes no acervo.

    Returns:
        List[str]: Estilos ordenados alfabeticamente.
    """
    estilos = db.query(Musica.estilo).distinct().order_by(Musica.estilo).all()
    return [e[0] for e in estilos if e[0]]

@router.put("/{musica_id}")
def atualizar_musica(
    musica_id: int,
    data: dict,
    db: Session = Depends(get_db)
):
    """
    Atualiza metadados de uma música específica.

    Args:
        musica_id: ID da música.
        data: Dicionário com campos a atualizar (energia, estilo, redflag, auditado_acustica).

    Returns:
        Música atualizada.

    Raises:
        HTTPException: 404 se música não encontrada.
    """
    musica = db.query(Musica).filter(Musica.id == musica_id).first()
    if not musica:
        raise HTTPException(status_code=404, detail="Música não encontrada")

    campos_permitidos = {"energia", "estilo", "redflag", "auditado_acustica"}
    for campo, valor in data.items():
        if campo in campos_permitidos:
            setattr(musica, campo, valor)

    db.commit()
    db.refresh(musica)
    return musica.to_dict()

@router.post("/batch/auditar")
async def auditar_em_lote(
    ids: List[int],
    db: Session = Depends(get_db)
):
    """
    Marca um lote de músicas para reauditoria pelo worker de curadoria.

    Args:
        ids: Lista de IDs das músicas.

    Returns:
        dict com quantidade processada.
    """
    # Apenas reseta o flag auditado_acustica para False, forçando o worker a reprocessar
    db.query(Musica).filter(Musica.id.in_(ids)).update(
        {Musica.auditado_acustica: False},
        synchronize_session=False
    )
    db.commit()
    return {"processados": len(ids)}

@router.post("/importar")
async def importar_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Importa metadados de um CSV e atualiza o banco de dados.
    Formato esperado: Caminho;Estilo;Energia;Auditado_Acustica
    """
    content = await file.read()
    try:
        decoded_content = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        decoded_content = content.decode("cp1252")
        
    f = io.StringIO(decoded_content)
    # Detecta delimitador (suporta ; ou ,)
    sample = f.read(1024)
    f.seek(0)
    dialect = csv.Sniffer().sniff(sample) if sample else None
    delimiter = dialect.delimiter if dialect else ';'
    
    reader = csv.DictReader(f, delimiter=delimiter)
    
    atualizados = 0
    erros = 0
    total = 0

    for row in reader:
        total += 1
        # Normalização de nomes de colunas (case-insensitive)
        cols = {k.strip().lower(): k for k in row.keys()}
        
        caminho = row.get(cols.get('caminho', 'Caminho'))
        if not caminho:
            erros += 1
            continue
            
        # Busca no banco
        musica = db.query(Musica).filter(Musica.caminho == caminho).first()
        if musica:
            try:
                if 'estilo' in cols:
                    musica.estilo = row[cols['estilo']].lower()
                if 'energia' in cols:
                    musica.energia = int(row[cols['energia']])
                if 'auditado_acustica' in cols:
                    musica.auditado_acustica = str(row[cols['auditado_acustica']]).lower() == 'true'
                if 'redflag' in cols:
                    musica.redflag = str(row[cols['redflag']]).lower() == 'true'
                
                atualizados += 1
            except:
                erros += 1
        else:
            erros += 1
            
    db.commit()
    
    msg = f"Importação finalizada: {atualizados} atualizados, {erros} erros, {total} total."
    guardian_instance.log_event("SUCCESS", msg)
    
    return {
        "status": "success",
        "total": total,
        "atualizados": atualizados,
        "erros": erros
    }

@router.post("/sincronizar")
async def sincronizar_acervo(db: Session = Depends(get_db)):
    """
    Sincroniza a pasta física de músicas com o banco de dados.
    Adiciona novas faixas, remove as inexistentes e atualiza renomeados.
    """
    PASTA_MUSICAS = r"D:\RADIO\MUSICAS"
    guardian_instance.log_event("SYNC", "Iniciando sincronização profunda do acervo...")
    
    arquivos_no_disco = set()
    novos = 0
    removidos = 0
    mantidos = 0
    
    # 1. Varredura de Disco e Adição/Atualização
    for root, _, files in os.walk(PASTA_MUSICAS):
        for file in files:
            if file.lower().endswith('.mp3'):
                caminho = os.path.abspath(os.path.join(root, file))
                arquivos_no_disco.add(caminho)
                
                musica = db.query(Musica).filter(Musica.caminho == caminho).first()
                if not musica:
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
                    # Atualiza o título se o nome do arquivo mudou mas o caminho é o mesmo
                    novo_titulo = file.replace(".mp3", "")
                    if musica.titulo != novo_titulo:
                        musica.titulo = novo_titulo
                    mantidos += 1
        db.commit()

    # 2. Limpeza de "Músicas Fantasmas" (Estão no banco mas não no disco)
    todas_musicas_db = db.query(Musica).all()
    for m in todas_musicas_db:
        if m.caminho not in arquivos_no_disco:
            # Verifica se o arquivo não foi apenas movido para a quarentena (para evitar deletar o registro)
            if not os.path.exists(m.caminho):
                db.delete(m)
                removidos += 1
    db.commit()

    msg = f"Sync finalizado: {novos} novos, {removidos} removidos do banco, {mantidos} mantidos."
    guardian_instance.log_event("SUCCESS", msg)
    return {"status": "success", "novos": novos, "removidos": removidos, "mantidos": mantidos}

@router.get("/exportar")
async def exportar_acervo(
    ids: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Exporta metadados do acervo para CSV.
    Pode filtrar por uma lista de IDs (separados por vírgula).
    """
    query = db.query(Musica)
    if ids:
        id_list = [int(i) for i in ids.split(",")]
        query = query.filter(Musica.id.in_(id_list))
    
    musicas = query.all()
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["Caminho", "Artista", "Titulo", "Estilo", "Energia", "Auditado", "Redflag"], delimiter=";")
    writer.writeheader()
    
    for m in musicas:
        writer.writerow({
            "Caminho": m.caminho,
            "Artista": m.artista,
            "Titulo": m.titulo,
            "Estilo": m.estilo,
            "Energia": m.energia,
            "Auditado": m.auditado_acustica,
            "Redflag": m.redflag
        })
    
    output.seek(0)
    filename = f"export_acervo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/quarantine")
def listar_quarentena(db: Session = Depends(get_db)):
    """
    Lista todas as músicas que foram enviadas para quarentena (redflag=True).
    """
    quarentenadas = db.query(Musica).filter(Musica.redflag == True).all()
    return [m.to_dict() for m in quarentenadas]


