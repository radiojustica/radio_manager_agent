import os
import sys
import glob
import asyncio

sys.path.append("C:/Users/STREAMING/.gemini/antigravity/scratch/radio_ia-main/radio_ia-main")
sys.path.append("C:/Users/STREAMING/.gemini/antigravity/scratch/radio_ia-main/radio_ia-main/modules/boletins")
import gerar_boletins_tts

async def main_custom():
    gerar_boletins_tts.ROTEIROS_DIR_BOLETINS = r"H:\Meu Drive\RADIO TJRN CONTEÚDO\00_PRODUCAO_2026\01_BOLETINS_DIARIOS\01_ROTEIROS\06 - JUN - 26\18 06 - QUI"
    await gerar_boletins_tts.main()

if __name__ == '__main__':
    asyncio.run(main_custom())