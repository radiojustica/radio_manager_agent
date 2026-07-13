import os
path = 'C:/Users/STREAMING/.gemini/antigravity/scratch/radio_ia-main/radio_ia-main/modules/boletins/gerar_boletins_tts.py'
content = open(path, 'r', encoding='utf-8').read()
content = content.replace("def ler_e_parsear_roteiro_local(txt_path):\n    with open(txt_path, 'r', encoding='utf-8') as f:\n        content = f.read()", "def ler_e_parsear_roteiro_local(txt_path):\n    if txt_path.endswith('.gdoc'):\n        import json, urllib.request\n        with open(txt_path, 'r', encoding='utf-8') as f:\n            doc_id = json.load(f).get('doc_id')\n        req = urllib.request.Request(f\"https://docs.google.com/document/d/{doc_id}/export?format=txt\", headers={'User-Agent': 'Mozilla/5.0'})\n        with urllib.request.urlopen(req) as response:\n            content = response.read().decode('utf-8-sig', errors='ignore')\n    else:\n        with open(txt_path, 'r', encoding='utf-8') as f:\n            content = f.read()")
content = content.replace('.replace(".txt", ".mp3")', '.replace(".txt", ".mp3").replace(".gdoc", ".mp3")')
open(path, 'w', encoding='utf-8').write(content)
print('fixed 2')
