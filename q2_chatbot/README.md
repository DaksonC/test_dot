# Q2 — Chatbot tutor de Python (LangChain + OpenAI)

Chatbot de terminal que responde dúvidas de **programação em Python** usando um LLM da
OpenAI, com **LangChain** gerenciando prompt, memória da conversa e integração com o modelo.
O tracing no **LangSmith** é opcional.

## Como instalar

```bash
cd q2_chatbot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Configure a chave: copie o [`.env.example`](../.env.example) da raiz para `.env`,
na raiz do repositório ou dentro de `q2_chatbot/`, e preencha `OPENAI_API_KEY`.
O `.env` está no `.gitignore`.

| Variável | Obrigatória | Padrão | Descrição |
|---|---|---|---|
| `OPENAI_API_KEY` | sim | — | Chave da API da OpenAI |
| `OPENAI_MODEL` | não | `gpt-5.6-luna` | Modelo usado (ex.: `gpt-5.6-terra`, `gpt-4o`) |
| `OPENAI_TEMPERATURE` | não | padrão do modelo | 0 a 2. Modelos de raciocínio podem aceitar só o padrão |
| `CHAT_MAX_HISTORY_MESSAGES` | não | `20` | Quantas mensagens do histórico são enviadas ao modelo |
| `LANGSMITH_TRACING` | não | `false` | `true` ativa o tracing no LangSmith |
| `LANGSMITH_API_KEY` | se tracing | — | Chave do LangSmith |
| `LANGSMITH_PROJECT` | não | `default` | Projeto onde os traces aparecem |

## Como rodar

```bash
python -m chatbot
```

```
=== Tutor de Python ===
Modelo: gpt-5.6-luna | Tracing LangSmith: desativado

Pergunte algo sobre Python (ex.: 'Como criar uma lista em Python?').
Comandos: /limpar apaga o histórico | /sair encerra.

Você: Como criar uma lista em Python?
Tutor: ...resposta exibida em streaming...
```

- `/sair` (ou `sair`, `exit`, `quit`, Ctrl+D) encerra o programa.
- `/limpar` apaga a memória da conversa.
- Ctrl+C durante uma resposta interrompe só aquela resposta.

### Tracing com LangSmith (opcional)

```bash
# no .env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_...
LANGSMITH_PROJECT=tutor-python
```

O LangChain lê essas variáveis automaticamente e envia cada execução da chain
(prompt, histórico, resposta, latência e tokens) para o LangSmith. Nenhuma mudança
no código é necessária. O `config.py` só valida a combinação: se o tracing estiver
ligado sem chave, o programa falha na inicialização com uma mensagem clara.

## Como testar

```bash
pytest
```

Os testes **não chamam a API**. Eles usam um modelo falso (`GenericFakeChatModel`
do langchain-core) que devolve respostas pré-definidas e grava as mensagens que
recebeu. Com isso é possível verificar:

- o prompt de sistema e a pergunta enviados ao modelo;
- a memória: a 2ª pergunta leva o turno anterior;
- o isolamento entre sessões e o comando `/limpar`;
- o recorte do histórico (só as últimas N mensagens vão para o modelo);
- o loop do terminal com entradas simuladas, incluindo os erros da OpenAI (401, 404 e 429), que são simulados.

## Exemplos de perguntas e respostas

As respostas reais são geradas pelo próprio chatbot, e não escritas à mão:

```bash
python -m chatbot.examples   # requer OPENAI_API_KEY; gera EXEMPLOS.md
```

Perguntas usadas, todas na **mesma sessão**. A 2ª só faz sentido se a memória funcionar:

1. Como criar uma lista em Python?
2. E como eu adiciono e removo itens nela?
3. Qual a diferença entre lista e tupla? Quando usar cada uma?
4. Como ler um arquivo CSV em Python?

Resultado: [`EXEMPLOS.md`](EXEMPLOS.md).

O arquivo é regravado a cada resposta. Se a API falhar no meio, as respostas já obtidas
são mantidas e o arquivo fica marcado como **incompleto**. O script tenta até 5 vezes com
backoff quando o problema é limite por minuto, e explica o que fazer em cada erro. O 429 tem
duas causas diferentes: `insufficient_quota` significa que a conta está sem crédito, e
`rate_limit_exceeded` significa excesso de requisições por minuto.

## Estrutura

```
chatbot/
├── config.py    # Settings a partir do ambiente/.env, com validação
├── chain.py     # SYSTEM_PROMPT, SessionStore, build_llm, build_chain
├── cli.py       # loop do terminal, streaming e tratamento de erros
├── examples.py  # gera EXEMPLOS.md com respostas reais
└── __main__.py  # python -m chatbot
tests/
├── conftest.py      # RecordingFakeChatModel (LLM falso)
├── test_chain.py    # prompt, memória, sessões e recorte
├── test_cli.py      # loop, comandos e erros da API
├── test_examples.py # gerador de exemplos: salvamento parcial e mensagens de erro
└── test_config.py   # variáveis obrigatórias e validações
```

## Decisões técnicas

- **Chain em LCEL:** `histórico recortado → ChatPromptTemplate → ChatOpenAI → StrOutputParser`.
  O prompt tem três partes: `system` (papel de tutor), `MessagesPlaceholder("history")` e a pergunta.
- **Memória com `RunnableWithMessageHistory`:** busca o histórico pelo `session_id`, injeta no
  prompt e grava pergunta e resposta **só se a chamada terminar bem**, sem deixar uma pergunta
  órfã no histórico. Isso é coberto por teste.
- **Recorte do histórico (`trim_messages`):** o histórico completo fica guardado, mas o modelo
  recebe só as últimas N mensagens. Isso limita custo e latência e evita estourar a janela de
  contexto. O recorte conta mensagens, não tokens: é simples e previsível.
- **Streaming:** a resposta aparece enquanto é gerada, o que é importante para explicações longas.
- **Erros da OpenAI:** chave inválida (401) e modelo inexistente (404) encerram o programa com
  uma mensagem clara. Rate limit (429), falha de rede e outros erros da API avisam e mantêm a conversa.
- **Configuração:** `python-dotenv` + validação na inicialização (*fail fast*). As variáveis
  exportadas no shell têm prioridade sobre o `.env`, e nenhuma chave aparece no código.
- **Modelo padrão `gpt-5.6-luna`:** a opção da OpenAI otimizada para custo, suficiente para
  explicações didáticas. É configurável por `OPENAI_MODEL`. A `temperature` só é enviada se
  configurada, porque modelos de raciocínio podem rejeitar valores diferentes do padrão.
- **Testabilidade:** `run_chat` recebe `input_fn` e `write` por injeção, e `build_chain` recebe
  qualquer chat model. Os testes rodam sem terminal e sem rede.

### Sobre o deprecation do `RunnableWithMessageHistory`

No LangChain 1.x, `RunnableWithMessageHistory` e `InMemoryChatMessageHistory` continuam
funcionando, mas estão marcados como *deprecated* (remoção prevista para a 2.0). A recomendação
oficial é usar a persistência do **LangGraph** (checkpointer com `thread_id`). Mantive a API
pedida no escopo e tomei três cuidados:

- fixei `langchain-core==1.6.4`;
- silenciei **apenas** esses dois avisos, para não poluir o terminal;
- isolei a memória em `build_chain`/`SessionStore`: a migração para LangGraph troca só esse ponto,
  e o CLI e os testes de comportamento continuam valendo.

### Limitações conhecidas

- A memória fica em RAM e se perde ao fechar o programa. Em produção, um `BaseChatMessageHistory`
  em Redis ou num banco (ou um checkpointer do LangGraph) permitiria persistência e várias instâncias.
- O recorte por número de mensagens não garante um limite de tokens: uma única mensagem muito longa
  ainda pode pesar.
- O escopo "só Python" depende do prompt de sistema. Não há um classificador de entrada dedicado.
