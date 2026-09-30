# 📦 HydraForge — Pipeline de Ingestão, Validação e Preparação de Datasets

> **Guia Técnico de Arquivos Aceitos, Ferramentas de Auditoria e Preparação para Treinamento YOLO (v8/11/26)**

---

## 📂 1. Tipos de Arquivos e Formatos Aceitos

| Categoria | Extensões Suportadas | Formato / Estrutura Esperada |
| :--- | :--- | :--- |
| **Imagens Individuais** | `.jpg`, `.jpeg`, `.png`, `.bmp`, `.webp` | Imagens RGB brutas ou acompanhadas de arquivos `.txt` espelhados. |
| **Vídeos Brutos** | `.mp4`, `.avi`, `.mov`, `.mkv` | Extração automática de frames por amostragem temporal (1-5 FPS) ou detecção de mudança de cena (*Scene Change Detection*). |
| **Pacotes Compactados** | `.zip`, `.tar`, `.tar.gz` | Arquivos contendo pastas `images/` e `labels/` ou pastas organizadas por classe. |
| **Anotações Externas** | `.txt`, `.json`, `.xml` | • **YOLO (.txt)**: `<class_id> <cx> <cy> <w> <h>` normalizado (0.0 a 1.0)<br>• **COCO (.json)**: Convertido automaticamente para YOLO via `convert_coco`<br>• **Pascal VOC (.xml)**: Bounding boxes em pixels absolutos convertidas automaticamente. |
| **Configuração de Dataset** | `data.yaml` | Arquivo canônico com caminhos absolutos/relativos, splits e mapa contíguo de classes (`names: {0: person, 1: car}`). |

---

## 🛠️ 2. Ferramentas Integradas de Validação e Preparação

### 1️⃣ Validador da "Regra do Espelho" (Mirror Rule Check)
- **Problema**: O motivo #1 de falha silenciosa de treino no YOLO é rotular imagens em diretórios não espelhados ou com extensões trocadas (o modelo treina com fundo vazio).
- **Ação do HydraForge**: Valida se cada arquivo em `images/train/X.jpg` possui seu respectivo `labels/train/X.txt`. Identifica imagens sem rótulo e classifica se são *Background Images* intencionais (recomendado 2% a 5% para reduzir falsos positivos) ou falha de anotação.

### 2️⃣ Analisador de Distribuição & Desbalanceamento de Classes
- **Inspeção de Proporção**: Alerta caso uma classe represente menos de 5% ou mais de 80% do total de instâncias.
- **Distribuição de Tamanhos de Bounding Box**: Classifica as caixas em *Small* ($<32^2\text{px}$), *Medium* ($32^2 - 96^2\text{px}$) e *Large* ($>96^2\text{px}$) para sugerir a resolução de treino ideal (`imgsz=640` vs `imgsz=1280`).

### 3️⃣ Auto-Split com Prevenção de "Data Leakage"
- **Problema**: Fazer split aleatório de frames de um mesmo vídeo espalha frames quase idênticos no `train` e no `val`, gerando métricas de validação falsamente infladas (*Overfitting ilusório*).
- **Ação do HydraForge**: Agrupa frames originados do mesmo clipe/câmera dentro do mesmo split (80% Train / 10% Val / 10% Test).

### 4️⃣ Deduplicação Criptográfica e Perceptual (pHash / Cosine Similarity)
- Remove automaticamente frames estáticos (câmera parada sem movimento) antes do treino, economizando VRAM da GPU e acelerando as épocas em até 40%.

### 5️⃣ Auto-Anotador Zero-Shot (SAM 2 + YOLO-World)
- Permite carregar um lote de imagens não anotadas, digitar uma classe em linguagem natural (ex: *"capacete de proteção"*) e auto-gerar as caixas/máscaras preliminares para revisão visual rápida.
