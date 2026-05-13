# 🎙️ Omni Core V2

**Sistema de Automação de Rádio Inteligente e Modular**

O Omni Core V2 é um ecossistema modular para automação e monitoramento de estações de rádio, integrando **ZaraRadio**, **BUTT**, **vMix** e **Gemini AI**.

## 🏗️ Arquitetura
O sistema é dividido em quatro pilares principais:

1.  **Core**: Gestão de banco de dados (SQLite), modelos e lógica de sistema.
2.  **Workers**: Agentes autônomos que executam tarefas específicas (Curadoria, Guardião, Sincronização, Relatórios).
3.  **API**: Servidor FastAPI que orquestra os workers e fornece endpoints para o frontend.
4.  **Frontend**: Dashboard moderno em React para cockpit e gestão do acervo.

## 🚀 Como Iniciar
Basta executar o script principal:
```powershell
python start.py
```
Isso iniciará a API, os workers e abrirá o dashboard automaticamente em seu navegador.

## 🛠️ Principais Componentes
- **GuardianWorker**: Monitora a saúde do sistema, previne reinícios e reconecta o streaming.
- **CuradoriaWorker**: Analisa BPM, Energia e Mood das músicas via Librosa e Gemini AI.
- **ReportWorker**: Gera relatórios semanais de performance e auditoria em CSV.
- **BulletinWorker**: Sincroniza boletins informativos automaticamente via Google Drive.

## 📊 Dashboard
Acesse em: [http://localhost:8001](http://localhost:8001)

## 📖 Documentação Adicional
- [OPERACAO.md](OPERACAO.md): Guia detalhado de operação e suporte.
- [GUIA_RAPIDO.md](GUIA_RAPIDO.md): Instruções rápidas para novos usuários.
- [MODULARIZATION_ROADMAP.md](MODULARIZATION_ROADMAP.md): Histórico da evolução do sistema.

---
**Desenvolvido com Malícia e Competência por Pickle Rick.** *belch* 🥒
