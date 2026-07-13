import os
import base64
from pathlib import Path

# Configurações de caminhos
ARTIFACT_DIR = Path(r"C:\Users\STREAMING\.gemini\antigravity\brain\5196666c-f17b-491e-bddd-d39864b7b6e4")
IMG_DASHBOARD_PATH = ARTIFACT_DIR / "dashboard_mockup_1783948228265.png"
IMG_GUARDIAN_PATH = ARTIFACT_DIR / "guardian_system_1783948241414.png"
OUTPUT_HTML_PATH = ARTIFACT_DIR / "media_kit_omni_core.html"

def image_to_base64(path):
    if not os.path.exists(path):
        print(f"Erro: Imagem não encontrada em {path}")
        return ""
    with open(path, "rb") as img_file:
        b64_data = base64.b64encode(img_file.read()).decode("utf-8")
        ext = path.suffix.replace(".", "")
        return f"data:image/{ext};base64,{b64_data}"

def build_html():
    print("Convertendo imagens para Base64...")
    b64_dashboard = image_to_base64(IMG_DASHBOARD_PATH)
    b64_guardian = image_to_base64(IMG_GUARDIAN_PATH)

    print("Gerando template HTML do Media Kit...")
    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Omni Core V2 - Media Kit</title>
    <!-- Google Fonts: Inter -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-main: #0f172a;       /* Slate 900 - Fundo principal */
            --bg-card: #1e293b;       /* Slate 800 - Fundo de cartões */
            --bg-accent: #334155;     /* Slate 700 - Destaques secundários */
            --text-primary: #f8fafc;  /* Slate 50 - Títulos e textos claros */
            --text-secondary: #cbd5e1;/* Slate 300 - Parágrafos */
            --text-muted: #94a3b8;    /* Slate 400 - Textos de apoio */
            --accent-color: #38bdf8;  /* Sky 400 - Azul tecnológico sóbrio */
            --accent-green: #34d399;  /* Emerald 400 - Status operacional */
            --border-color: #475569;  /* Slate 600 - Bordas sutis */
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-main);
            color: var(--text-secondary);
            line-height: 1.6;
            padding: 0;
            overflow-x: hidden;
        }}

        .container {{
            max-width: 1000px;
            margin: 0 auto;
            padding: 2rem 1.5rem;
        }}

        header {{
            text-align: center;
            padding: 4rem 1.5rem 3rem 1.5rem;
            background: linear-gradient(180deg, rgba(30, 41, 59, 0.5) 0%, rgba(15, 23, 42, 0) 100%);
            border-bottom: 1px solid rgba(71, 85, 105, 0.2);
            position: relative;
        }}

        .badge {{
            display: inline-block;
            padding: 0.35rem 1rem;
            background-color: rgba(56, 189, 248, 0.1);
            color: var(--accent-color);
            border: 1px solid rgba(56, 189, 248, 0.2);
            border-radius: 9999px;
            font-size: 0.85rem;
            font-weight: 600;
            letter-spacing: 0.05em;
            margin-bottom: 1.5rem;
            text-transform: uppercase;
        }}

        h1 {{
            font-size: 2.75rem;
            font-weight: 800;
            color: var(--text-primary);
            line-height: 1.2;
            margin-bottom: 1rem;
            letter-spacing: -0.02em;
        }}

        .subtitle {{
            font-size: 1.2rem;
            font-weight: 400;
            color: var(--text-muted);
            max-width: 600px;
            margin: 0 auto 1.5rem auto;
        }}

        .divider {{
            height: 4px;
            width: 80px;
            background: var(--accent-color);
            margin: 1.5rem auto 0 auto;
            border-radius: 9999px;
        }}

        .author-box {{
            background-color: var(--bg-card);
            border-left: 4px solid var(--accent-color);
            border-radius: 0.5rem;
            padding: 1.5rem;
            margin: 3rem 0;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1);
        }}

        .author-box h3 {{
            color: var(--text-primary);
            font-size: 1.15rem;
            margin-bottom: 0.5rem;
            font-weight: 600;
        }}

        .author-box p {{
            font-size: 0.95rem;
            color: var(--text-secondary);
        }}

        .section {{
            margin-bottom: 4rem;
        }}

        .section-title {{
            font-size: 1.75rem;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            letter-spacing: -0.01em;
        }}

        .section-title::after {{
            content: '';
            flex-grow: 1;
            height: 1px;
            background-color: var(--border-color);
            opacity: 0.3;
            margin-left: 0.5rem;
        }}

        p {{
            margin-bottom: 1.25rem;
            font-size: 1.05rem;
        }}

        /* Grid de Benefícios */
        .benefits-grid {{
            display: grid;
            grid-template-columns: 1fr;
            gap: 1.5rem;
            margin-top: 2rem;
        }}

        @media (min-width: 768px) {{
            .benefits-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}
        }}

        .benefit-card {{
            background-color: var(--bg-card);
            border: 1px solid rgba(71, 85, 105, 0.3);
            border-radius: 0.75rem;
            padding: 2rem;
            transition: all 0.2s ease-in-out;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        }}

        .benefit-card:hover {{
            transform: translateY(-2px);
            border-color: rgba(56, 189, 248, 0.4);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        }}

        .benefit-icon {{
            font-size: 2rem;
            margin-bottom: 1rem;
            display: inline-block;
        }}

        .benefit-card h3 {{
            font-size: 1.25rem;
            color: var(--text-primary);
            margin-bottom: 0.75rem;
            font-weight: 600;
        }}

        .benefit-card p {{
            font-size: 0.95rem;
            color: var(--text-muted);
            margin-bottom: 0;
        }}

        /* Mídia e Imagens */
        .media-container {{
            margin: 2.5rem 0;
            background-color: var(--bg-card);
            border: 1px solid rgba(71, 85, 105, 0.3);
            border-radius: 0.75rem;
            padding: 1rem;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
            text-align: center;
        }}

        .media-image {{
            max-width: 100%;
            height: auto;
            border-radius: 0.5rem;
            border: 1px solid rgba(71, 85, 105, 0.2);
            display: block;
            margin: 0 auto;
        }}

        .media-caption {{
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-top: 0.75rem;
            font-style: italic;
        }}

        /* Tabela Comparativa */
        .table-responsive {{
            width: 100%;
            overflow-x: auto;
            margin: 2rem 0;
            border-radius: 0.75rem;
            border: 1px solid rgba(71, 85, 105, 0.3);
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 0.95rem;
        }}

        th {{
            background-color: var(--bg-accent);
            color: var(--text-primary);
            font-weight: 600;
            padding: 1rem 1.25rem;
            border-bottom: 2px solid var(--border-color);
        }}

        td {{
            padding: 1rem 1.25rem;
            border-bottom: 1px solid rgba(71, 85, 105, 0.2);
            background-color: var(--bg-card);
        }}

        tr:last-child td {{
            border-bottom: none;
        }}

        .text-green {{
            color: var(--accent-green);
            font-weight: 500;
        }}

        /* Tabela de Dayparting */
        .dayparting-table th {{
            background-color: rgba(30, 41, 59, 0.8);
        }}

        /* Call To Action */
        .cta-section {{
            background: linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%);
            border: 1px solid rgba(56, 189, 248, 0.2);
            border-radius: 1rem;
            padding: 3rem 2rem;
            text-align: center;
            margin-top: 5rem;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.15);
        }}

        .cta-section h2 {{
            font-size: 2rem;
            color: var(--text-primary);
            margin-bottom: 1rem;
            font-weight: 700;
        }}

        .cta-section p {{
            max-width: 600px;
            margin: 0 auto 2rem auto;
            color: var(--text-secondary);
        }}

        .cta-button {{
            display: inline-block;
            background-color: var(--accent-color);
            color: var(--bg-main);
            font-weight: 700;
            font-size: 1.05rem;
            padding: 0.85rem 2.25rem;
            border-radius: 0.5rem;
            text-decoration: none;
            transition: all 0.2s ease-in-out;
            box-shadow: 0 4px 14px 0 rgba(56, 189, 248, 0.4);
        }}

        .cta-button:hover {{
            background-color: #7dd3fc;
            transform: translateY(-1px);
            box-shadow: 0 6px 20px 0 rgba(56, 189, 248, 0.5);
        }}

        footer {{
            text-align: center;
            padding: 3rem 1.5rem;
            margin-top: 4rem;
            border-top: 1px solid rgba(71, 85, 105, 0.2);
            color: var(--text-muted);
            font-size: 0.85rem;
        }}

        /* Estilização para Alertas */
        .alert-box {{
            background-color: rgba(30, 41, 59, 0.6);
            border-left: 4px solid var(--accent-color);
            padding: 1.25rem 1.5rem;
            border-radius: 0.375rem;
            margin: 1.5rem 0;
        }}

        .alert-box p {{
            margin: 0;
            font-size: 0.95rem;
            color: var(--text-secondary);
        }}
    </style>
</head>
<body>

    <header>
        <span class="badge">Apresentação Tecnológica</span>
        <h1>OMNI CORE V2</h1>
        <p class="subtitle">O cérebro autônomo de inteligência, estabilidade e curadoria acústica que gerencia a sua rádio em segundo plano.</p>
        <div class="divider"></div>
    </header>

    <div class="container">
        
        <div class="author-box">
            <h3>Concebido de Radialista para Radialista</h3>
            <p>Idealizado por <strong>Thiago Macedo</strong>, jornalista e radialista com anos de experiência em estúdios de transmissão. O Omni Core V2 foi desenhado para resolver as dores reais que os comunicadores e programadores enfrentam diariamente no ar, blindando a operação e liberando a equipe humana para o trabalho artístico e criativo.</p>
        </div>

        <section class="section">
            <h2 class="section-title">O Que é o Omni Core V2?</h2>
            <p>O Omni Core V2 é um sistema modular inteligente que gerencia a retaguarda tecnológica da sua emissora. Ele não altera a forma como sua equipe opera: seus locutores e operadores continuam utilizando o confiável <strong>ZaraRadio</strong> para a reprodução de áudio e o leve <strong>BUTT</strong> para codificar a transmissão de internet. O Omni Core envolve essas ferramentas clássicas com uma camada de inteligência artificial e monitoramento ativo, elevando a rádio a um padrão industrial de resiliência e curadoria musical.</p>
        </section>

        <section class="section">
            <h2 class="section-title">O Cockpit de Controle Remoto</h2>
            <p>Através de um painel administrativo moderno e responsivo, o diretor de programação e o proprietário da rádio conseguem acompanhar em tempo real toda a saúde operacional da rádio, visualizar as músicas executadas, e monitorar o status do streaming de qualquer dispositivo conectado à internet.</p>
            
            <div class="media-container">
                <img src="{b64_dashboard}" class="media-image" alt="Dashboard do Cockpit Omni Core V2">
                <div class="media-caption">Cockpit Web em tempo real: telemetria acústica, status de rede e controle proativo da emissora.</div>
            </div>
        </section>

        <section class="section">
            <h2 class="section-title">Os Agentes Autônomos (Workers)</h2>
            <p>Operando em segundo plano de forma silenciosa e precisa, os agentes autônomos garantem que o som nunca pare e a qualidade musical se mantenha no topo:</p>
            
            <div class="benefits-grid">
                <div class="benefit-card">
                    <span class="benefit-icon">🛡️</span>
                    <h3>Guardião do Ar (Guardian)</h3>
                    <p>Monitora os processos de transmissão (ZaraRadio e BUTT) em tempo real. Se o player travar ou o streaming cair, ele reinicia o software e reconecta a transmissão instantaneamente. Ele também impede o Windows de forçar atualizações e reinícios em horários comerciais de pico.</p>
                </div>
                <div class="benefit-card">
                    <span class="benefit-icon">🧠</span>
                    <h3>Curadoria Acústica por IA</h3>
                    <p>Analisa a biblioteca musical utilizando Inteligência Artificial (Gemini) e análise de áudio matemática. O sistema cataloga BPM, energia acústica e humor (valence) de cada música. Músicas ruins, distorcidas ou com energia muito abaixo do padrão vão automaticamente para a Quarentena.</p>
                </div>
                <div class="benefit-card">
                    <span class="benefit-icon">☀️</span>
                    <h3>Playlist Baseada em Clima</h3>
                    <p>Gera grades musicais de 24h integradas com a previsão meteorológica da cidade. Dias ensolarados puxam ritmos Pop e enérgicos; dias chuvosos priorizam tons intimistas como Jazz e Bossa Nova. Tudo isso respeitando regras estritas de não repetir o mesmo cantor por 2 horas.</p>
                </div>
                <div class="benefit-card">
                    <span class="benefit-icon">☁️</span>
                    <h3>Sincronia de Notícias na Nuvem</h3>
                    <p>Sincroniza boletins gravados pela equipe jornalística no Google Drive diretamente com o computador de transmissão em segundos. O locutor não precisa manipular pendrives ou arquivos de áudio; tudo é substituído automaticamente na grade com segurança.</p>
                </div>
            </div>
        </section>

        <section class="section">
            <h2 class="section-title">Monitoramento Físico e Processos</h2>
            <p>O sistema supervisiona a infraestrutura local, garantindo que o hardware de transmissão não sobrecarregue e mantendo a taxa de transmissão estável, registrando todas as ações de proteção em logs centralizados para auditoria rápida.</p>
            
            <div class="media-container">
                <img src="{b64_guardian}" class="media-image" alt="Monitoramento de Processos e Servidor">
                <div class="media-caption">Mecanismo de Watchdog ativo: verificação constante de processos de transmissão, uso de CPU/RAM e reconexão de streaming.</div>
            </div>
        </section>

        <section class="section">
            <h2 class="section-title">A Curva de Energia Musical (Dayparting)</h2>
            <p>A programação musical acompanha a rotina do ouvinte ao longo do dia, otimizando a energia de acordo com a faixa horária:</p>
            
            <div class="table-responsive">
                <table class="dayparting-table">
                    <thead>
                        <tr>
                            <th>Horário</th>
                            <th>Nível de Energia</th>
                            <th>Objetivo para o Ouvinte</th>
                            <th>Gêneros Recomendados</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong>00h às 06h</strong></td>
                            <td>Baixa (1 a 3)</td>
                            <td>Acompanhar a madrugada de forma suave</td>
                            <td>MPB Clássica, Blues, Jazz, Instrumental</td>
                        </tr>
                        <tr>
                            <td><strong>06h às 10h</strong></td>
                            <td>Alta (4 a 5)</td>
                            <td>Despertar e animar o início do dia</td>
                            <td>Pop, Rock Nacional, Ritmos Regionais</td>
                        </tr>
                        <tr>
                            <td><strong>10h às 16h</strong></td>
                            <td>Moderada (3 a 4)</td>
                            <td>Manter o ritmo produtivo em lojas e escritórios</td>
                            <td>MPB Contemporânea, Reggae, Soul, MPB Pop</td>
                        </tr>
                        <tr>
                            <td><strong>16h às 20h</strong></td>
                            <td>Alta (4 a 5)</td>
                            <td>Energetizar o ouvinte no trânsito de retorno</td>
                            <td>Pop/Rock Nacional, Pop Internacional, Hits</td>
                        </tr>
                        <tr>
                            <td><strong>20h às 00h</strong></td>
                            <td>Baixa/Média (1 a 3)</td>
                            <td>Relaxar e desacelerar após o expediente</td>
                            <td>Bossa Nova, MPB Acústico, Soft Rock</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </section>

        <section class="section">
            <h2 class="section-title">Rádio Visual e Compliance Automatizados</h2>
            <p>Se a sua rádio transmite a programação em vídeo para redes sociais (YouTube/Facebook), o Omni Core se comunica com o <strong>vMix</strong>. Quando o rádio toca uma vinheta de abertura, comerciais ou faixas, o vMix recebe comandos de rede para trocar as cenas de vídeo de forma sincronizada, rodando a Rádio Visual de forma 100% autônoma.</p>
            
            <div class="alert-box">
                <p><strong>Comprovantes de Veiculação (ECAD & Patrocinadores):</strong> O sistema registra cada segundo de áudio veiculado e exporta relatórios semanais formatados. Ideal para comprovar a publicidade dos parceiros e gerir taxas de direitos autorais de forma rápida.</p>
            </div>
        </section>

        <section class="section">
            <h2 class="section-title">O Salto Tecnológico para Sua Rádio</h2>
            <div class="table-responsive">
                <table>
                    <thead>
                        <tr>
                            <th>Recurso</th>
                            <th>Rádio Convencional (Manual)</th>
                            <th>Rádio com Omni Core V2</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong>Recuperação de Quedas</strong></td>
                            <td>Manual. O ar fica mudo até o técnico intervir fisicamente.</td>
                            <td class="text-green">Automática. O ar reergue em milissegundos.</td>
                        </tr>
                        <tr>
                            <td><strong>Atualizações do Windows</strong></td>
                            <td>Derrubam o computador em horários de pico.</td>
                            <td class="text-green">Bloqueadas ativamente durante a programação.</td>
                        </tr>
                        <tr>
                            <td><strong>Filtro de Qualidade de Faixas</strong></td>
                            <td>Depende de ouvir música por música para achar defeitos.</td>
                            <td class="text-green">Varredura e isolamento automático por IA na Quarentena.</td>
                        </tr>
                        <tr>
                            <td><strong>Distribuição de Notícias</strong></td>
                            <td>Operador precisa baixar, renomear e arrastar áudios.</td>
                            <td class="text-green">Sincronização proativa via Google Drive sem toque humano.</td>
                        </tr>
                        <tr>
                            <td><strong>Adaptação Climatológica</strong></td>
                            <td>Playlist engessada que toca músicas repetidas e frias.</td>
                            <td class="text-green">Grades flexíveis geradas de acordo com o clima do dia.</td>
                        </tr>
                        <tr>
                            <td><strong>Operação de Rádio Visual</strong></td>
                            <td>Requer operador de vídeo manual alternando cenas.</td>
                            <td class="text-green">Disparo inteligente e síncrono de cenas no vMix por áudio.</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </section>

        <div class="cta-section">
            <h2>Eleve o Nível Tecnológico da Sua Emissora</h2>
            <p>Traga a inteligência do Omni Core V2 para a sua rádio. Garanta 99.9% de uptime na transmissão, fidelize seu ouvinte com programação adaptativa, libere sua equipe de tarefas repetitivas e modernize sua presença de vídeo comercial.</p>
            <a href="mailto:comercial@omnicore.com.br?subject=Interesse%20no%20Omni%20Core%20V2" class="cta-button">Fale Conosco e Solicite uma Demonstração</a>
        </div>

        <footer>
            <p>© 2026 Omni Core V2. Desenvolvido por Thiago Macedo. Todos os direitos reservados.</p>
            <p>Sistema Operacional: Windows | Versão de Produção 2.0.0</p>
        </footer>

    </div>

</body>
</html>
"""
    
    with open(OUTPUT_HTML_PATH, "w", encoding="utf-8") as out_file:
        out_file.write(html_content)
    
    print(f"Sucesso! Media Kit gerado com sucesso em: {OUTPUT_HTML_PATH}")

if __name__ == "__main__":
    build_html()
