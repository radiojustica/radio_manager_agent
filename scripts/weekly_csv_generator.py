import os
import csv
import glob
from datetime import datetime, timedelta

class WeeklyCSVGenerator:
    def __init__(self, log_dir: str, output_dir: str):
        self.log_dir = log_dir
        self.output_dir = output_dir

    def generate_report(self, days: int = 7) -> str:
        """Parses ZaraRadio logs for the last N days and generates a CSV report."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        report_filename = f"Execution_Report_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
        report_path = os.path.join(self.output_dir, report_filename)
        
        os.makedirs(self.output_dir, exist_ok=True)
        
        data = []
        
        # Collect all log files in range
        for i in range(days + 1):
            date_to_check = start_date + timedelta(days=i)
            log_name = f"{date_to_check.strftime('%Y-%m-%d')}.log"
            log_path = os.path.join(self.log_dir, log_name)
            
            if os.path.exists(log_path):
                data.extend(self._parse_log_file(log_path, date_to_check.strftime('%Y-%m-%d')))

        if not data:
            return ""

        keys = ["Data", "Hora", "Acao", "Arquivo", "Artista", "Titulo"]
        try:
            with open(report_path, 'w', newline='', encoding='utf-8-sig') as f:
                dict_writer = csv.DictWriter(f, fieldnames=keys, delimiter=';')
                dict_writer.writeheader()
                dict_writer.writerows(data)
            return report_path
        except Exception as e:
            print(f"Error generating CSV: {e}")
            return ""

    def _parse_log_file(self, file_path: str, date_str: str) -> list:
        entries = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
                for line in lines:
                    line = line.strip()
                    if not line or "início" not in line.lower():
                        continue
                        
                    # Split by multiple spaces or tab
                    parts = line.split('\t')
                    if len(parts) < 3:
                        # Try split by multiple spaces (at least 4)
                        import re
                        parts = re.split(r'\s{4,}', line)
                        
                    if len(parts) >= 3:
                        time_str = parts[0].strip()
                        action = parts[1].strip()
                        file_info = parts[2].strip()
                        
                        # Only include songs (ignore jingles/spots if needed, but usually ECAD wants everything)
                        # We try to extract Artist - Title from filename
                        filename = os.path.basename(file_info).replace('.mp3', '').replace('.wav', '')
                        artist = ""
                        title = filename
                        
                        if " - " in filename:
                            f_parts = filename.split(" - ", 1)
                            artist = f_parts[0].strip()
                            title = f_parts[1].strip()
                            
                        entries.append({
                            "Data": date_str,
                            "Hora": time_str,
                            "Acao": action,
                            "Arquivo": file_info,
                            "Artista": artist,
                            "Titulo": title
                        })
        except Exception as e:
            print(f"Error parsing log {file_path}: {e}")
            
        return entries

if __name__ == "__main__":
    # Test call
    gen = WeeklyCSVGenerator(r"D:\RADIO\LOG ZARARADIO", "reports")
    path = gen.generate_report(7)
    print(f"Report generated at: {path}")


