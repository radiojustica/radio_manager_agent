# gerar_configs_butt.py
import os

PASTA_SAIDA = "butt_configs"
os.makedirs(PASTA_SAIDA, exist_ok=True)

# Configurações específicas de cada instância
INSTANCIAS = [
    {"arquivo": "butt_32k.butt", "bitrate": 32, "log_dir": "D:\\LOG32", "server_ativo": "TJRN 32k", "api_port": 1256},
    {"arquivo": "butt_64k.butt", "bitrate": 64, "log_dir": "D:\\LOG64", "server_ativo": "TJRN 64k", "api_port": 1257},
    {"arquivo": "butt_128k.butt", "bitrate": 128, "log_dir": "D:\\LOG128", "server_ativo": "TJRN 128k", "api_port": 1258}
]

# Template baseado no arquivo do usuário, corrigido e com a seção de Remote Control adicionada
TEMPLATE = """[main]
bg_color = 252645120
txt_color = -256
server = {server_ativo}
srv_ent = TJRN 64k;TJRN 128k;TJRN 32k
icy = TJRN - Rádio Justiça
icy_ent = TJRN - Rádio Justiça
num_of_srv = 3
num_of_icy = 1
song_update_url_active = 0
song_update_url_interval = 1
song_update_url =
song_path = 
song_update = 0
song_delay = 0
song_prefix = 
song_suffix = 
read_last_line = 0
app_update_service = 0
app_update = 0
app_artist_title_order = 1
gain = 1.513561
signal_threshold = 0.000000
silence_threshold = 0.000000
signal_detection = 0
silence_detection = 0
check_for_update = 0
check_for_buttm = 1
start_agent = 1
minimize_to_tray = 1
connect_at_startup = 0
force_reconnecting = 0
reconnect_delay = 1
ic_charset = 
log_file = {log_dir}

[audio]
device = 15
device2 = -1
dev_remember = 1
samplerate = 48000
bitrate = {bitrate}
channel = 2
left_ch = 1
right_ch = 2
left_ch2 = 1
right_ch2 = 1
codec = mp3
resample_mode = 1
silence_level = 50.000000
signal_level = 30.000000
disable_dithering = 0
buffer_ms = 50
dev_name = RADIO (USB Audio CODEC ) [Loopback] [Windows WASAPI]
dev2_name = Nenhum

[record]
bitrate = 128
codec = mp3
start_rec = 0
stop_rec = 0
rec_after_launch = 0
overwrite_files = 0
sync_to_hour  = 0
split_time = 0
filename = rec_%Y%m%d-%H%M%S.mp3
signal_threshold = 0.000000
silence_threshold = 0.000000
signal_detection = 0
silence_detection = 0
folder = C:\\Users\\STREAMING\\Music\\

[tls]
cert_file = 
cert_dir = 

[dsp]
equalizer = 0
equalizer_rec = 0
eq_preset = Manual
gain1 = 0.000000
gain2 = 0.000000
gain3 = 0.000000
gain4 = 0.000000
gain5 = 0.000000
gain6 = 0.000000
gain7 = 0.000000
gain8 = 0.000000
gain9 = 0.000000
gain10 = 0.000000
compressor = 0
compressor_rec = 0
aggressive_mode = 0
threshold = -20.000000
ratio = 5.000000
attack = 0.010000
release = 1.000000
makeup_gain = 0.000000

[mixer]
primary_device_gain = 1.000000
primary_device_muted = 0
secondary_device_gain = 1.000000
secondary_device_muted = 0
streaming_gain = 1.000000
recording_gain = 1.000000
cross_fader = 0.000000

[gui]
attach = 0
ontop = 0
hide_log_window = 0
remember_pos = 1
x_pos = 1122
y_pos = 460
window_height = 395
lcd_auto = 0
default_stream_info = 0
start_minimized = 0
disable_gain_slider = 0
show_listeners = 1
listeners_update_rate = 10
lang_str = system
vu_low_color = 13762560
vu_mid_color = -421134336
vu_high_color = -939524096
vu_mid_range_start = -12
vu_high_range_start = -6
always_show_vu_tabs = 1
window_title = 
vu_mode = 1

[Remote Control]
enabled = 1
port = {api_port}
password = omni_admin

[mp3_codec_stream]
enc_quality = 3
stereo_mode = 0
bitrate_mode = 0
vbr_quality = 4
vbr_min_bitrate = 32
vbr_max_bitrate = 320
vbr_force_min_bitrate = 0
resampling_freq = 0
lowpass_freq_active = 0
lowpass_freq = 0.000000
lowpass_width_active = 0
lowpass_width = 0.000000
highpass_freq_active = 0
highpass_freq = 0.000000
highpass_width_active = 0
highpass_width = 0.000000

[mp3_codec_rec]
enc_quality = 3
stereo_mode = 0
bitrate_mode = 0
vbr_quality = 4
vbr_min_bitrate = 32
vbr_max_bitrate = 320
vbr_force_min_bitrate = 0
resampling_freq = 0
lowpass_freq_active = 0
lowpass_freq = 0.000000
lowpass_width_active = 0
lowpass_width = 0.000000
highpass_freq_active = 0
highpass_freq = 0.000000
highpass_width_active = 0
highpass_width = 0.000000

[vorbis_codec_stream]
bitrate_mode = 0
vbr_quality = 0
vbr_min_bitrate = 0
vbr_max_bitrate = 0

[vorbis_codec_rec]
bitrate_mode = 0
vbr_quality = 0
vbr_min_bitrate = 0
vbr_max_bitrate = 0

[opus_codec_stream]
bitrate_mode = 1
quality = 0
audio_type = 0
bandwidth = 0

[opus_codec_rec]
bitrate_mode = 1
quality = 0
audio_type = 0
bandwidth = 0

[aac_codec_stream]
bitrate_mode = 0
afterburner = 0
profile = 0

[aac_codec_rec]
bitrate_mode = 0
afterburner = 0
profile = 0

[flac_codec_stream]
bit_depth = 16

[flac_codec_rec]
bit_depth = 16

[wav_codec_rec]
bit_depth = 16

[midi]
dev_name = Disabled

[TJRN 64k]
address = z-quito.tjrn.jus.br
port = 8000
password = tj-33undduntsourc3
type = 1
tls = 0
custom_listener_url = 
custom_listener_mount = 
cert_hash = 
mount = radiojusticapotiguar64k
usr = source
protocol = 0

[TJRN 128k]
address = z-quito.tjrn.jus.br
port = 8000
password = tj-33undduntsourc3
type = 1
tls = 0
custom_listener_url = 
custom_listener_mount = 
cert_hash = 
mount = radiojusticapotiguar128k
usr = source
protocol = 0

[TJRN 32k]
address = z-quito.tjrn.jus.br
port = 8000
password = tj-33undduntsourc3
type = 1
tls = 0
custom_listener_url = 
custom_listener_mount = 
cert_hash = 
mount = radiojusticapotiguar32k
usr = source
protocol = 0

[TJRN - Rádio Justiça]
expand_variables = 0
pub = 1
description = 
genre = 
url = 
irc = 
icq = 
aim = 
"""

print("🔧 Gerando configurações padronizadas do BUTT...")
for inst in INSTANCIAS:
    conteudo = TEMPLATE.format(
        server_ativo=inst["server_ativo"],
        log_dir=inst["log_dir"],
        bitrate=inst["bitrate"],
        api_port=inst["api_port"]
    )
    
    caminho = os.path.join(PASTA_SAIDA, inst["arquivo"])
    with open(caminho, 'w', encoding='utf-8') as f:
        f.write(conteudo)
    print(f"✅ Criado: {caminho} (Bitrate: {inst['bitrate']}k | Log: {inst['log_dir']} | API Port: {inst['api_port']})")

print("\n🎉 Concluído! Substitua os arquivos antigos do BUTT por estes e crie as pastas de log (D:\\LOG32, D:\\LOG64, D:\\LOG128).")
