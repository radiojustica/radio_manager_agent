import os
import sys
import subprocess

current_dir = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
project_root = os.path.dirname(os.path.dirname(current_dir)).replace("\\", "/")

def main():
    print("=== AGENTE DE IA UNIFICADO (MODO LOCAL .TXT) ===")
    
    script_boletins = os.path.join(project_root, "modules/boletins/gerar_boletins_tts.py").replace("\\", "/")
    print(f"\n-> Iniciando pipeline de Boletins: {script_boletins}")
    res_bol = subprocess.run([sys.executable, script_boletins], capture_output=False)
    if res_bol.returncode != 0:
        print(f"[AVISO] Pipeline de Boletins encerrou com código {res_bol.returncode}")
        
    script_njud = os.path.join(project_root, "modules/jornal/gerar_njud_tts.py").replace("\\", "/")
    print(f"\n-> Iniciando pipeline de NJUD: {script_njud}")
    res_njud = subprocess.run([sys.executable, script_njud], capture_output=False)
    if res_njud.returncode != 0:
        print(f"[AVISO] Pipeline do NJUD encerrou com código {res_njud.returncode}")

    print("\n=== EXECUÇÃO DO AGENTE FINALIZADA ===")

if __name__ == "__main__":
    main()
