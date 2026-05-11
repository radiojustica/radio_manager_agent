# Agente Especialista em Rádio (ZaraRadio + BUTT)

Este agente monitora sua transmissão 24/7 para garantir estabilidade e evitar reinicializações indesejadas do Windows.

## Localização dos Arquivos
O projeto está em: `C:\Users\STREAMING\.gemini\antigravity\scratch\radio_manager_agent`

## Como Iniciar
1. Abra o **PowerShell como Administrador**.
2. Execute o comando:
   ```powershell
   python C:\Users\STREAMING\.gemini\antigravity\scratch\radio_manager_agent\main.py
   ```

## Funcionalidades de Especialista:
- **Monitoramento de Processos**: Verifica se ZaraRadio e BUTT estão rodando.
- **Análise de Execução**: Lê os logs em `D:\RADIO\LOG ZARARADIO` para acompanhar a rádio.
- **Bloqueio de Reinício**: Impede que o Windows Update reinicie o PC enquanto o agente estiver rodando.
- **Sempre Ligado**: Desativa suspensão de tela e sistema para rádio não cair.

## Configurações Atuais (settings.json)
- **Executável**: `D:\ZaraRadio\ZaraRadio.exe`
- **Diretório de Logs**: `D:\RADIO\LOG ZARARADIO`
- **Intervalo de Checagem**: 60 segundos
