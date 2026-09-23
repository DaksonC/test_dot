# Q3 — Busca semântica com embeddings e vector store

Sistema de **busca semântica** sobre um conjunto de 24 documentos curtos em português.
Os textos são convertidos em **embeddings** com `sentence-transformers` e armazenados em
um índice **FAISS** persistido em disco. A função `search(query, k)` devolve os documentos
mais parecidos **em significado** com a consulta, mesmo sem palavras em comum.

## Como instalar

```bash
cd q3_semantic_search
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

O `requirements.txt` instala o **PyTorch só para CPU**, sem baixar cerca de 2 GB de bibliotecas CUDA.
Na primeira execução, o modelo (cerca de 470 MB) é baixado do Hugging Face Hub e fica em cache.
O aviso `unauthenticated requests to the HF Hub` pode ser ignorado. Definir `HF_TOKEN` só aumenta
o limite de download.

## Como rodar

```bash
# 1) Gera os embeddings e persiste o índice em index/
python -m semantic_search.build

# 2) Demonstração com consultas pré-definidas
python -m semantic_search.demo

# 3) Busca livre
python -m semantic_search.demo "receita de comida brasileira com feijão"
```

Uso como biblioteca:

```python
from semantic_search import search

for result in search("meu cachorro tem medo de fogos", k=3):
    print(f"{result.score:.3f}  {result.document.title}")
```

## Como testar

```bash
pytest                  # unitários: embedder falso, sem baixar modelo (< 1 s)
pytest -m integration   # integração: modelo real + índice em disco (rode o build antes)
```

- **Unitários:** usam um `FakeEmbedder` (bag-of-words com hashing) que respeita o mesmo contrato
  do embedder real. Cobrem ordenação por score, formato dos resultados, `k` maior que a coleção,
  validações, persistência (salvar e carregar), detecção de índice inconsistente e de modelo trocado,
  e o dataset.
- **Integração:** vetores reais normalizados, a função `search()` pública e cada consulta da
  demonstração com o documento esperado no top-3.

## Como funciona o pipeline

```
data/documents.json ──► título + texto ──► SentenceTransformer ──► vetores 384d normalizados
                                                                         │
                                                                         ▼
      consulta ──► mesmo modelo ──► vetor normalizado ──► IndexFlatIP.search ──► top-k (id, score)
                                                                         │
                                          index/documents.json (posição i = vetor i) ◄──┘
```

### 1. Documentos
`data/documents.json` tem 24 documentos (`id`, `title`, `category`, `text`) de 13 categorias
(animais, culinária, saúde, finanças, tecnologia, astronomia, jardinagem, esportes, viagem,
história, meio ambiente, música, educação). O carregamento valida os campos obrigatórios e
rejeita ids duplicados.

### 2. Geração dos embeddings
- **Modelo:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`. É multilíngue (inclui
  português), gera vetores de **384 dimensões** e roda bem em CPU. Foi treinado com pares de
  paráfrases, então frases com o mesmo sentido ficam próximas mesmo com vocabulário diferente.
- **Texto embutido:** `"{título}. {texto}"`. O título resume o assunto e reforça o sinal.
- **Normalização:** `normalize_embeddings=True` deixa cada vetor com norma L2 = 1. Isso importa
  para o passo seguinte.
- O modelo trunca entradas acima de 128 tokens. Os documentos daqui são curtos. Textos longos
  precisariam ser divididos em trechos (*chunking*) antes.

### 3. Armazenamento no FAISS
- **`IndexFlatIP`:** busca **exata** por produto interno (*inner product*). Com vetores
  normalizados, **produto interno = similaridade de cosseno**, então o score fica entre -1 e 1,
  e quanto maior, mais parecido.
- **Por que exata:** com dezenas ou milhares de vetores, a força bruta leva microssegundos e não
  precisa de treino. Índices aproximados (IVF, HNSW) só compensam em escala de milhões.
- **Persistência em `index/`,** que não é versionada porque é regenerável:

  | Arquivo | Conteúdo |
  |---|---|
  | `index.faiss` | os vetores (`faiss.write_index`) |
  | `documents.json` | os documentos **na mesma ordem dos vetores**: o id que o FAISS devolve é a posição na lista |
  | `meta.json` | modelo, dimensão, quantidade de documentos e data de criação |

- **Ao carregar,** o sistema verifica se os três arquivos são consistentes entre si (quantidade e
  dimensão). Na busca, recusa um embedder diferente do modelo que gerou o índice, porque vetores
  de modelos diferentes não são comparáveis.

### 4. Busca
`search(query, k)`:
1. valida a consulta (não vazia) e `k` (maior ou igual a 1);
2. limita `k` ao tamanho da coleção;
3. gera o embedding da consulta com o **mesmo modelo**;
4. chama `index.search` e devolve uma lista de `SearchResult(document, score)` em ordem decrescente de score.

O índice e o modelo são carregados uma vez por processo (`lru_cache`).

## Demonstração: busca por significado, não por palavra

As 11 consultas do `demo.py` foram escritas **sem nenhuma palavra de conteúdo em comum** com o
documento esperado. Isso é checado por código (`shared_terms`), e não só no olho: a comparação
ignora maiúsculas, acentos e *stopwords* e compara radicais de 5 letras, o que também pega plurais
e variações. Um teste garante isso para todas as consultas. Uma busca por palavra-chave não
encontraria nenhum desses documentos.

Saída real de `python -m semantic_search.demo` (trechos):

```
✓ Consulta: 'meu cachorro fica apavorado com fogos de artifício no ano novo'
   1. [0.491] Ansiedade em cães durante rojões (animais)  <- esperado
   2. [0.178] Como fazer o gato beber mais água (animais)
   3. [0.155] Eclipse solar (astronomia)

✓ Consulta: 'qual invenção permitiu copiar textos em massa no século quinze'
   1. [0.485] A prensa de Gutenberg (história)  <- esperado

✓ Consulta: 'pesticidas estão matando os insetos que fabricam mel'
   1. [0.624] Importância das abelhas (meio ambiente)  <- esperado

~ Consulta: 'como evitar doença nos rins do meu bichano'
   1. [0.340] Desidratação em dias quentes (saúde)
   2. [0.242] Como fazer o gato beber mais água (animais)  <- esperado

hit@1: 8/11 | hit@3: 11/11
```

- **cachorro/fogos de artifício → cães/rojões**, **pesticidas/fabricam mel → agrotóxicos/abelhas**
  e **copiar textos em massa → prensa de Gutenberg**: a relação é de sinônimo ou de conceito, não
  de palavra.
- Busca livre `"receita de comida brasileira com feijão"` → **Feijoada tradicional** (0.763).

### Onde o modelo erra, e o que isso ensina

Em 3 consultas o esperado ficou em 2º ou 3º lugar. Mantive essas consultas de propósito, em vez de
reescrevê-las até acertar:

| Consulta | 1º lugar | Leitura |
|---|---|---|
| "doença nos rins do meu **bichano**" | Desidratação | A gíria "bichano" não é bem associada a "gato", e "doença" puxa o documento de saúde |
| "ganhar **fôlego** sem me machucar" | Higiene do sono | O sentido de condicionamento físico ficou ambíguo com "bem-estar" |
| "relógio biológico **bagunçado**" | Eclipse solar (0.255) | Todos os scores ficaram baixos: sinal de baixa confiança, e não de acerto |

Melhorias possíveis: um modelo maior (ex.: `multilingual-e5-base`), um **limiar mínimo de score**
para responder "nada relevante", **busca híbrida** (BM25 + vetores) e **re-ranking** com um
cross-encoder.

## Estrutura

```
data/documents.json          # 24 documentos de exemplo
semantic_search/
├── config.py                # caminhos e nome do modelo
├── documents.py             # Document + carregamento/validação do JSON
├── embeddings.py            # protocolo Embedder + SentenceTransformerEmbedder
├── store.py                 # build/save/load do índice FAISS
├── search.py                # SemanticSearcher.search e o atalho search(query, k)
├── build.py                 # python -m semantic_search.build
└── demo.py                  # python -m semantic_search.demo
tests/                       # unitários (embedder falso) + integração (modelo real)
index/                       # gerado pelo build (não versionado)
```

## Decisões técnicas

- **`sentence-transformers` em vez de `transformers` puro:** faz o *mean pooling* e a normalização
  corretos para esse modelo. Com `transformers` puro seria preciso implementar isso à mão.
- **Protocolo `Embedder`:** índice e busca não conhecem o modelo concreto. Isso permite testes
  rápidos com um embedder falso e troca de modelo sem mexer no resto.
- **Mapeamento posicional (vetor i = documento i),** com validação ao carregar. É simples, e a
  checagem evita a pior falha possível: devolver o documento errado em silêncio.
- **FAISS em vez de Milvus:** é uma biblioteca embarcada, sem servidor. Faz sentido para um único
  processo e uma coleção pequena. Milvus, Qdrant ou pgvector passam a valer quando há atualizações
  concorrentes, filtros por metadados, várias instâncias ou volume grande.
- **Índice como artefato de build:** fica fora do git e é regenerado com um comando. O `meta.json`
  registra com qual modelo foi gerado.
