"""Demonstração da busca semântica.

Uso:
  python -m semantic_search.demo                 # roda as consultas de demonstração
  python -m semantic_search.demo "sua consulta"  # busca livre (top 3)

As consultas de demonstração foram escritas SEM palavras em comum com o
documento esperado (verificado por `shared_terms`, também coberto por teste).
Uma busca por palavra-chave não as encontraria; se o documento certo aparece
no topo, é porque a busca está comparando significado.
"""

import re
import sys
import unicodedata

from semantic_search.documents import Document
from semantic_search.search import SearchResult, search
from semantic_search.store import IndexNotFoundError

# (consulta, id do documento esperado)
DEMO_QUERIES: list[tuple[str, str]] = [
    ("meu cachorro fica apavorado com fogos de artifício no ano novo", "pets-ansiedade"),
    ("como evitar doença nos rins do meu bichano", "pets-gatos-agua"),
    ("quanto devo poupar caso eu perca o emprego", "financas-reserva"),
    ("como proteger meu e-mail e redes sociais de hackers", "tecnologia-senhas"),
    ("o que acontece quando o céu escurece de repente por causa de um astro na frente", "astronomia-eclipse"),
    ("quero plantar ervas para cozinhar na sacada", "jardinagem-horta"),
    ("estou sedentário e quero ganhar fôlego sem me machucar", "esportes-corrida"),
    ("qual invenção permitiu copiar textos em massa no século quinze", "historia-imprensa"),
    ("voltei do Japão e meu relógio biológico ficou bagunçado", "viagem-jetlag"),
    ("como parar de enrolar e render nos estudos", "educacao-estudo"),
    ("pesticidas estão matando os insetos que fabricam mel", "meio-ambiente-abelhas"),
]

# Palavras funcionais ignoradas na checagem de sobreposição (já sem acento).
_STOPWORDS = {
    "a", "o", "as", "os", "de", "do", "da", "dos", "das", "e", "em", "no", "na", "nos", "nas",
    "um", "uma", "uns", "umas", "para", "por", "com", "sem", "que", "se", "ao", "aos",
    "meu", "minha", "meus", "minhas", "seu", "sua", "eu", "nao", "como", "qual", "quais",
    "quanto", "estou", "esta", "estao", "pelo", "pela", "quando", "porque", "ou", "mas",
    "entre", "me", "mais",
}
_STEM_SIZE = 5


def _normalize(text: str) -> str:
    """Minúsculas e sem acentos: 'Fôlego' -> 'folego'."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _stems(text: str) -> set[str]:
    # Radical grosseiro (primeiros caracteres) para pegar variações como
    # joelho/joelhos ou proteger/protege: torna a checagem mais rigorosa.
    words = re.findall(r"[a-z0-9]+", _normalize(text))
    return {w[:_STEM_SIZE] for w in words if len(w) >= 3 and w not in _STOPWORDS}


def shared_terms(query: str, document: Document) -> set[str]:
    """Radicais de palavras de conteúdo que a consulta e o documento têm em comum."""
    return _stems(query) & _stems(f"{document.title} {document.text}")


def _print_results(results: list[SearchResult], expected_id: str | None = None) -> None:
    for rank, result in enumerate(results, start=1):
        marker = "  <- esperado" if result.document.id == expected_id else ""
        print(f"   {rank}. [{result.score:.3f}] {result.document.title} ({result.document.category}){marker}")


def run_demo(k: int = 3) -> int:
    # hit@1: esperado em 1º lugar; hit@k: esperado entre os k primeiros.
    hits_at_1 = hits_at_k = 0
    for query, expected_id in DEMO_QUERIES:
        results = search(query, k)
        ranked_ids = [r.document.id for r in results]
        hits_at_1 += ranked_ids[0] == expected_id
        hits_at_k += expected_id in ranked_ids
        mark = "✓" if ranked_ids[0] == expected_id else ("~" if expected_id in ranked_ids else "✗")
        print(f"\n{mark} Consulta: {query!r}")
        _print_results(results, expected_id)

    total = len(DEMO_QUERIES)
    print(f"\nhit@1: {hits_at_1}/{total} | hit@{k}: {hits_at_k}/{total}")
    print("(✓ esperado em 1º | ~ esperado no top-k | ✗ fora do top-k)")
    return 0


def main(argv: list[str]) -> int:
    try:
        if argv:
            query = " ".join(argv)
            print(f"Consulta: {query!r}")
            _print_results(search(query, 3))
            return 0
        return run_demo()
    except IndexNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
