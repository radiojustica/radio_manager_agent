import json
import os
from pathlib import Path
from core.reward import RewardStore
from datetime import datetime

def generate_detailed_report():
    store = RewardStore()
    workers_data = store.data.get('workers', {})
    
    report = [
        '# 🏆 RELATÓRIO COMPLETO DE DESEMPENHO - OMNI CORE V2',
        f'**Extraído em:** {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}',
        '',
        'Este relatório apresenta uma visão exaustiva da performance de todos os agentes (workers) do sistema Omni Core V2, baseando-se nos logs de recompensas e penalidades.',
        ''
    ]

    # Ordenar workers por pontuação total (decrescente)
    sorted_workers = sorted(workers_data.items(), key=lambda x: x[1]['score_total'], reverse=True)

    for name, data in sorted_workers:
        cycles = data.get('cycles', 0)
        score_total = data.get('score_total', 0)
        avg_score = score_total / cycles if cycles > 0 else 0
        
        report.append(f'## 🤖 Worker: {name}')
        report.append(f'- **Pontuação Total:** `{score_total}`')
        report.append(f'- **Ciclos Executados:** `{cycles}`')
        report.append(f'- **Média de Eficiência:** `{avg_score:.2f} pts/ciclo`')
        
        last = data.get('last_result')
        if last:
            # Formatar timestamp para algo mais legível
            ts = last['timestamp']
            try:
                ts_obj = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                ts_str = ts_obj.strftime("%d/%m/%Y %H:%M:%S")
            except:
                ts_str = ts
                
            report.append(f'- **Última Atividade:** `{ts_str}`')
            report.append(f'- **Último Resultado:** `Score: {last["score"]}`')
            
            if last.get('violations'):
                report.append('  - **🚫 Violações Recentes:**')
                for v in last['violations']:
                    report.append(f'    - {v}')
        
        history = data.get('history', [])
        if history:
            report.append('\n### 🕒 Linha do Tempo Recente (Últimos 10 Ciclos)')
            report.append('| Timestamp | Score | Status |')
            report.append('| :--- | :--- | :--- |')
            for h in reversed(history[-10:]):
                try:
                    h_ts = datetime.fromisoformat(h['timestamp'].replace('Z', '+00:00')).strftime("%H:%M:%S")
                except:
                    h_ts = h['timestamp']
                
                status = '🔴 FALHA' if h.get('violations') else '🟢 OK'
                report.append(f'| {h_ts} | {h["score"]} | {status} |')
        
        report.append('\n---')

    report.append('\n_Gerado automaticamente por Omni Core V2 AI Architecture_')

    os.makedirs('reports', exist_ok=True)
    report_path = 'reports/complete_performance_report_20260511.md'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))
    
    return report_path

if __name__ == "__main__":
    path = generate_detailed_report()
    print(f"Relatório gerado com sucesso em: {path}")
