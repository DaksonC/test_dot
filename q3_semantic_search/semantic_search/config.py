"""Caminhos e constantes do projeto."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = PROJECT_ROOT / "data" / "documents.json"
# Artefato gerado (não versionado): pode ser recriado com `python -m semantic_search.build`.
INDEX_DIR = PROJECT_ROOT / "index"

# Modelo multilíngue (inclui português), 384 dimensões, leve o bastante para CPU.
# Treinado com pares de paráfrases: frases com o mesmo sentido ficam próximas
# no espaço vetorial mesmo sem palavras em comum.
DEFAULT_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
