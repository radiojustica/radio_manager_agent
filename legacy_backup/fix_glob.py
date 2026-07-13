import os
path = "C:/Users/STREAMING/.gemini/antigravity/scratch/radio_ia-main/radio_ia-main/modules/boletins/gerar_boletins_tts.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old_str = 'roteiros = glob.glob(os.path.join(ROTEIROS_DIR_BOLETINS, "**", "*.txt"), recursive=True)'
new_str = 'roteiros = glob.glob(os.path.join(ROTEIROS_DIR_BOLETINS, "**", "*.txt"), recursive=True) + glob.glob(os.path.join(ROTEIROS_DIR_BOLETINS, "**", "*.gdoc"), recursive=True)'

content = content.replace(old_str, new_str)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Fix ok")