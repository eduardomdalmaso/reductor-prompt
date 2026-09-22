#!/usr/bin/env python3
"""
Baixa e compila a documentação completa do Laravel 12.x e PHP 8.4
para o banco de dados do ReductorPrompt.
"""

import os
import sys
import json
import urllib.request
import urllib.parse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ReductorPrompt/1.0"
BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_DIR = BASE_DIR / "database"


def fetch_file(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return f"<!-- Erro ao baixar {url}: {e} -->"


def download_laravel_docs():
    print("🚀 Baixando documentação oficial do Laravel 12.x (laravel/docs @ 12.x)...")
    tree_url = "https://api.github.com/repos/laravel/docs/git/trees/12.x?recursive=1"
    req = urllib.request.Request(tree_url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        items = [x["path"] for x in data.get("tree", []) if x["path"].endswith(".md")]

    print(f"  -> {len(items)} arquivos Markdown encontrados no repositório laravel/docs.")
    
    # Categorização inteligente dos 103 arquivos do Laravel 12.x
    groups = {
        "Laravel_12_Architecture_Routing_and_HTTP.md": {
            "title": "Laravel 12.x Architecture Routing and HTTP",
            "files": [
                "releases.md", "upgrade.md", "contributions.md", "installation.md",
                "configuration.md", "structure.md", "lifecycle.md", "container.md",
                "providers.md", "facades.md", "bootstrap.md", "routing.md",
                "middleware.md", "csrf.md", "controllers.md", "requests.md",
                "responses.md", "views.md", "blade.md", "vite.md", "urls.md",
                "session.md", "validation.md", "error-handling.md", "logging.md"
            ]
        },
        "Laravel_12_Eloquent_ORM_Database_and_Storage.md": {
            "title": "Laravel 12.x Eloquent ORM Database and Storage",
            "files": [
                "database.md", "queries.md", "pagination.md", "migrations.md",
                "seeding.md", "redis.md", "eloquent.md", "eloquent-relationships.md",
                "eloquent-collections.md", "eloquent-mutators.md", "eloquent-resources.md",
                "eloquent-serialization.md", "eloquent-factories.md", "scout.md",
                "filesystem.md", "cache.md"
            ]
        },
        "Laravel_12_Security_Auth_and_Testing.md": {
            "title": "Laravel 12.x Security Auth Testing and Verification",
            "files": [
                "authentication.md", "authorization.md", "passwords.md",
                "verification.md", "encryption.md", "hashing.md", "sanctum.md",
                "passport.md", "pennant.md", "testing.md", "http-tests.md",
                "console-tests.md", "browser-tests.md", "database-testing.md",
                "mocking.md"
            ]
        },
        "Laravel_12_Concurrency_Queues_Octane_and_AI.md": {
            "title": "Laravel 12.x Concurrency Queues Octane and AI Ecosystem",
            "files": [
                "artisan.md", "broadcasting.md", "events.md", "helpers.md",
                "http-client.md", "mail.md", "notifications.md", "packages.md",
                "queues.md", "rate-limiting.md", "scheduling.md", "strings.md",
                "collections.md", "concurrency.md", "context.md", "octane.md",
                "horizon.md", "pulse.md", "telescope.md", "reverb.md",
                "ai.md", "ai-sdk.md", "boost.md", "billing.md", "cashier-paddle.md",
                "dusk.md", "envoy.md", "folio.md", "fortify.md", "homestead.md",
                "precognition.md", "prompts.md", "sail.md", "socialite.md", "valet.md"
            ]
        }
    }

    # Baixar todo o conteúdo em paralelo
    raw_contents = {}
    with ThreadPoolExecutor(max_workers=12) as executor:
        url_map = {
            f: f"https://raw.githubusercontent.com/laravel/docs/12.x/{urllib.parse.quote(f)}"
            for f in items
        }
        future_to_file = {executor.submit(fetch_file, u): f for f, u in url_map.items()}
        for future in as_completed(future_to_file):
            f = future_to_file[future]
            raw_contents[f] = future.result()

    # Compilar cada grupo
    for out_filename, info in groups.items():
        out_path = DATABASE_DIR / out_filename
        with open(out_path, "w", encoding="utf-8") as out:
            out.write(f"# {info['title']}\n\n")
            out.write("> Documentação oficial e completa do Laravel 12.68.0 / 12.x extraída de `laravel/docs`.\n\n")
            
            for fname in info["files"]:
                if fname in raw_contents:
                    content = raw_contents[fname]
                    section = fname.replace(".md", "").replace("-", " ").title()
                    out.write(f"\n\n---\n\n## Capítulo: {section}\n")
                    out.write(f"*Arquivo Fonte: `laravel/docs/12.x/{fname}`*\n\n")
                    out.write(content.strip())
                    out.write("\n")
        print(f"✅ Gerado: {out_filename} ({out_path.stat().st_size / 1024:.1f} KB)")


def download_php_docs():
    print("\n🚀 Baixando documentação completa do PHP 8.4 (php/php-src @ PHP-8.4 & Guias Canônicos)...")
    
    # 1. UPGRADING e UPGRADING.INTERNALS oficiais
    upgrading = fetch_file("https://raw.githubusercontent.com/php/php-src/PHP-8.4/UPGRADING")
    upgrading_internals = fetch_file("https://raw.githubusercontent.com/php/php-src/PHP-8.4/UPGRADING.INTERNALS")
    news = fetch_file("https://raw.githubusercontent.com/php/php-src/PHP-8.4/NEWS")

    php_manual_path = DATABASE_DIR / "PHP_8_4_Complete_Reference_and_Migration_Manual.md"
    with open(php_manual_path, "w", encoding="utf-8") as out:
        out.write("# PHP 8.4 Complete Reference, New Features and Migration Manual\n\n")
        out.write("> Compilação oficial do PHP 8.4 contendo guias de migração, novas features (Property Hooks, Asymmetric Visibility, HTML5 DOM, Novas Funções de Array) e arquitetura interna.\n\n")
        
        out.write("## Capítulo 1: Visão Geral de Novas Funcionalidades do PHP 8.4\n\n")
        out.write("### 1.1 Property Hooks (Hooks de Propriedade)\n")
        out.write("O PHP 8.4 introduziu Property Hooks inspirados em linguagens modernas como Kotlin, Swift e C#. "
                  "Eles permitem interceptar operações de leitura (`get`) e escrita (`set`) diretamente na propriedade, "
                  "eliminando métodos getters/setters repetitivos.\n\n"
                  "```php\n"
                  "class User {\n"
                  "    public string $first;\n"
                  "    public string $last;\n"
                  "\n"
                  "    // Hook de leitura calculado\n"
                  "    public string $fullName {\n"
                  "        get => \"$this->first $this->last\";\n"
                  "    }\n"
                  "\n"
                  "    // Hook de escrita com validação\n"
                  "    public string $username {\n"
                  "        set {\n"
                  "            if (strlen($value) < 3) throw new InvalidArgumentException('Nome muito curto');\n"
                  "            $this->username = strtolower($value);\n"
                  "        }\n"
                  "    }\n"
                  "}\n"
                  "```\n\n")

        out.write("### 1.2 Visibilidade Assimétrica (Asymmetric Visibility)\n")
        out.write("Permite definir visibilidade distinta para leitura e escrita em propriedades de classe:\n\n"
                  "```php\n"
                  "class Book {\n"
                  "    // Público para leitura, mas modificável apenas dentro da classe\n"
                  "    public private(set) string $title;\n"
                  "    public protected(set) int $views = 0;\n"
                  "\n"
                  "    public function __construct(string $title) {\n"
                  "        $this->title = $title;\n"
                  "    }\n"
                  "}\n"
                  "```\n\n")

        out.write("### 1.3 Novo Parser e API DOM HTML5 (`Dom\\HTMLDocument`)\n")
        out.write("Nova API moderna compatível com o padrão WHATWG HTML5:\n\n"
                  "```php\n"
                  "use Dom\\HTMLDocument;\n"
                  "\n"
                  "$dom = HTMLDocument::createFromString('<!DOCTYPE html><div>Olá Mundo</div>');\n"
                  "$div = $dom->querySelector('div');\n"
                  "echo $div->textContent;\n"
                  "```\n\n")

        out.write("### 1.4 Encadeamento de Métodos sem Parênteses em `new`\n")
        out.write("Agora é permitido encadear chamadas de métodos diretamente na instanciação:\n\n"
                  "```php\n"
                  "// PHP 8.4 (sem parênteses envolventes)\n"
                  "$request = new Request()->withHeader('Accept', 'application/json')->send();\n"
                  "```\n\n")

        out.write("### 1.5 Novas Funções de Array e String\n")
        out.write("- `array_find(array $array, callable $callback): mixed`\n"
                  "- `array_find_key(array $array, callable $callback): mixed`\n"
                  "- `array_any(array $array, callable $callback): bool`\n"
                  "- `array_all(array $array, callable $callback): bool`\n"
                  "- `mb_trim(string $string, string $characters = ...): string`\n"
                  "- `mb_ltrim()`, `mb_rtrim()`\n"
                  "- `request_parse_body()` para parsing RFC 1867 sem multipart/form-data restrito ao POST.\n\n")

        out.write("### 1.6 Lazy Objects (Objetos Preguiçosos Nativos)\n")
        out.write("Suporte nativo do engine Zend para Ghost Objects e Proxies sem necessidade de geração de código intermediário.\n\n")

        out.write("\n\n---\n\n## Capítulo 2: Guia Oficial de Migração e Upgrading (PHP-8.4)\n\n")
        out.write(upgrading.strip())
        out.write("\n\n---\n\n## Capítulo 3: Mudanças Internas do Motor Zend (UPGRADING.INTERNALS)\n\n")
        out.write(upgrading_internals.strip())
        out.write("\n\n---\n\n## Capítulo 4: Registro de Alterações e Correções (NEWS)\n\n")
        out.write(news[:50000].strip())
        out.write("\n")

    print(f"✅ Gerado: {php_manual_path.name} ({php_manual_path.stat().st_size / 1024:.1f} KB)")


def main():
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    download_laravel_docs()
    download_php_docs()
    print("\n✨ Download e compilação de PHP 8.4 e Laravel 12.x concluídos com sucesso!")


if __name__ == "__main__":
    main()
