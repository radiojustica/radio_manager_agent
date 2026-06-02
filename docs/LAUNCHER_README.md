# Omni Core V2 - Launcher Unificado

## Como usar

### Opção 1: Script Batch (Recomendado para Windows)
1. Clique duas vezes no arquivo `START_OMNI.bat`
2. O sistema iniciará automaticamente:
   - Backend em background
   - Frontend no navegador
   - Sem piscar a tela

### Opção 2: Linha de comando
```bash
python launcher.py
```

### Opção 3: Execução direta (modo antigo)
```bash
python main.py  # Inicia com UI visível
```

## O que o launcher faz

1. **Inicia o backend** em background sem mostrar janelas
2. **Aguarda o servidor** ficar pronto (porta 8001)
3. **Abre o navegador** automaticamente no frontend
4. **Mantém tudo rodando** até você pressionar Ctrl+C

## Benefícios

- ✅ **Um clique** para iniciar tudo
- ✅ **Sem piscar** a tela do PC
- ✅ **Navegador abre automaticamente**
- ✅ **Backend roda em background**
- ✅ **Interface limpa** e simples

## Solução de problemas

### Se o navegador não abrir
- Acesse manualmente: http://localhost:8001

### Se o backend não iniciar
- Verifique se há outra instância rodando
- Execute `python main.py` para ver mensagens de erro

### Se houver problemas de permissões
- Execute como Administrador

## Arquivos importantes

- `launcher.py` - Script principal de inicialização
- `main.py` - Backend principal (agora suporta modo background)
- `START_OMNI.bat` - Atalho para Windows
- `frontend/dist/` - Interface web