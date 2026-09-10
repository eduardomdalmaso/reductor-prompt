#!/usr/bin/env python3
"""
Script para download automatizado e deduplicação de livros do repositório MinhNguyenDS/AI-pdf-books.
Categorias suportadas:
  - Paper
  - Machine Learning books
  - LLMOps and MLOps books
  - LLM and NLP books
  - Data Science books
  - AI books
  - AI Architecture books
"""

import os
import sys
import json
import hashlib
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO_API_URL = "https://api.github.com/repos/MinhNguyenDS/AI-pdf-books/git/trees/Master?recursive=1"
RAW_BASE_URL = "https://raw.githubusercontent.com/MinhNguyenDS/AI-pdf-books/Master"

TARGET_FOLDERS = [
    "Paper",
    "Machine Learning books",
    "LLMOps and MLOps books",
    "LLM and NLP books",
    "Data Science books",
    "AI books",
    "AI Architecture books"
]

DATABASE_DIR = Path(__file__).resolve().parent.parent / "database"

def calculate_sha256(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def get_existing_files():
    existing = {}
    for f in DATABASE_DIR.glob("*"):
        if f.is_file() and not f.name.startswith("."):
            existing[f.name.lower()] = {
                "path": f,
                "size": f.stat().st_size
            }
    return existing

def fetch_file_list():
    print("🔍 Consultando lista de arquivos no repositório GitHub...")
    req = urllib.request.Request(REPO_API_URL, headers={"User-Agent": "ReductorPrompt-BookDownloader/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
        tree = data.get("tree", [])

    files_to_download = []
    for item in tree:
        if item.get("type") == "blob":
            path = item.get("path", "")
            for folder in TARGET_FOLDERS:
                if path.startswith(folder + "/"):
                    filename = Path(path).name
                    files_to_download.append({
                        "category": folder,
                        "relative_path": path,
                        "filename": filename,
                        "expected_size": item.get("size", 0)
                    })
                    break
    return files_to_download

def download_file(item: dict, existing_files: dict) -> tuple:
    filename = item["filename"]
    rel_path = item["relative_path"]
    expected_size = item["expected_size"]
    dest_path = DATABASE_DIR / filename

    # Inteligência de Deduplicação Local Pré-Download
    if dest_path.exists():
        actual_size = dest_path.stat().st_size
        if expected_size > 0 and actual_size == expected_size:
            return ("SKIPPED_EXISTING", filename, item["category"], actual_size)
    
    # Se já existir um arquivo com o mesmo nome em minúsculas
    lower_name = filename.lower()
    if lower_name in existing_files:
        info = existing_files[lower_name]
        if expected_size > 0 and info["size"] == expected_size:
            return ("SKIPPED_EXISTING", filename, item["category"], info["size"])

    # Download
    encoded_path = urllib.parse.quote(rel_path)
    url = f"{RAW_BASE_URL}/{encoded_path}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (ReductorPrompt Downloader)"})

    temp_path = dest_path.with_suffix(dest_path.suffix + ".tmp")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp, open(temp_path, "wb") as out_f:
            total_read = 0
            while True:
                chunk = resp.read(1024 * 256)
                if not chunk:
                    break
                out_f.write(chunk)
                total_read += len(chunk)
        
        # Move arquivo final
        temp_path.replace(dest_path)
        return ("DOWNLOADED", filename, item["category"], total_read)
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        return ("ERROR", filename, item["category"], str(e))

def main():
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    existing_files = get_existing_files()
    
    print(f"📁 Pasta database/ contém {len(existing_files)} arquivos existentes.")
    items = fetch_file_list()
    print(f"📚 Encontrados {len(items)} arquivos nas 7 categorias especificadas.\n")

    downloaded = 0
    skipped = 0
    errors = 0

    max_workers = 6
    print(f"🚀 Iniciando download concorrente ({max_workers} threads) com inteligência anti-duplicação...\n")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(download_file, item, existing_files): item for item in items}
        for idx, future in enumerate(as_completed(futures), 1):
            status, filename, category, detail = future.result()
            if status == "DOWNLOADED":
                downloaded += 1
                size_mb = detail / (1024 * 1024)
                print(f"[{idx}/{len(items)}] ✅ Baixado: [{category}] {filename} ({size_mb:.2f} MB)")
            elif status == "SKIPPED_EXISTING":
                skipped += 1
                size_mb = detail / (1024 * 1024)
                print(f"[{idx}/{len(items)}] ⏩ Já existe (ignorado): [{category}] {filename} ({size_mb:.2f} MB)")
            else:
                errors += 1
                print(f"[{idx}/{len(items)}] ❌ Erro ao baixar [{category}] {filename}: {detail}")

    print("\n" + "="*50)
    print(f"🏁 Concluído!")
    print(f"   - Baixados com sucesso: {downloaded}")
    print(f"   - Ignorados (já existentes): {skipped}")
    print(f"   - Erros: {errors}")
    print("="*50)

if __name__ == "__main__":
    main()
