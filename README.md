# ArtBid — Art Auction House

![Next.js](https://img.shields.io/badge/Next.js-16-000000?style=for-the-badge&logo=nextdotjs&logoColor=white) ![React](https://img.shields.io/badge/React-19-149ECA?style=for-the-badge&logo=react&logoColor=white) ![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white) ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-4169E1?style=for-the-badge&logo=postgresql&logoColor=white) ![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=for-the-badge&logo=redis&logoColor=white) ![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white) ![License MIT](https://img.shields.io/badge/License-MIT-8B5CF6?style=for-the-badge&logo=license&logoColor=white)

**Arte em disputa. Lances em tempo real. Histórico verificável.**

O **ArtBid** é uma plataforma de leilões de arte que reúne pesquisa de obras, gestão de lotes, participação em leilões, carteira de créditos e consulta de auditoria numa única experiência.

O projecto combina uma interface em **Next.js** com uma API em **FastAPI**, persistência em **PostgreSQL** e processamento assíncrono com **Celery e Redis**.

## Índice

- [Visão geral](#visão-geral)
- [Funcionalidades](#funcionalidades)
- [Stack tecnológica](#stack-tecnológica)
- [Organização da aplicação](#organização-da-aplicação)
- [Executar localmente](#executar-localmente)
- [Endereços locais](#endereços-locais)
- [Configuração](#configuração)
- [Segurança e consistência](#segurança-e-consistência)
- [Integração com o catálogo de arte](#integração-com-o-catálogo-de-arte)
- [Auditoria à prova de adulteração](#auditoria-à-prova-de-adulteração)
- [Comandos úteis](#comandos-úteis)
- [Roteiro de demonstração](#roteiro-de-demonstração)
- [Comportamentos inesperados e limitações conhecidas](#comportamentos-inesperados-e-limitações-conhecidas)
- [Uso de IA](#Uso-de-IA)
- [Notas para publicação](#notas-para-publicação)
- [Autor](#autor)
- [Licença](#licença)

## Visão geral

O ArtBid foi concebido para unir a experiência de compra e venda de arte com transparência operacional e verificação de eventos. A plataforma cobre desde a pesquisa e criação de lotes até à participação em leilão, acompanhamento em tempo real e consultoria de auditoria.

## Funcionalidades

### Para leiloeiros

- Pesquisa de obras através da integração com o Art Institute of Chicago.
- Pré-visualização das informações das obras.
- Criação de lotes com lance inicial, incremento mínimo e período de participação.
- Consulta e gestão dos próprios lotes.
- Cancelamento de lotes sujeito às regras de negócio.
- Acompanhamento dos resultados dos leilões.

### Para licitantes

- Registo e autenticação.
- Consulta do catálogo e dos detalhes dos lotes.
- Participação nas salas de leilão.
- Carteira de créditos, depósitos e consulta de movimentos.
- Acompanhamento dos lances efectuados.
- Consulta de lotes ganhos e comprovativos.

### Para acompanhar e verificar

- Actualizações através de **Server-Sent Events — SSE**.
- Histórico de eventos por lote.
- Verificação de integridade da cadeia de auditoria.
- Checkpoints com suporte a assinatura.
- Comprovativos associados aos resultados dos leilões.

## Stack tecnológica

| Camada | Tecnologias |
| --- | --- |
| Interface | Next.js, React e TypeScript |
| Estilos | Tailwind CSS |
| Dados no frontend | TanStack Query |
| Formulários e validação | React Hook Form e Zod |
| API | FastAPI e Pydantic |
| Persistência | PostgreSQL e SQLAlchemy |
| Migrações | Alembic |
| Processamento assíncrono | Celery |
| Broker e infraestrutura de eventos | Redis |
| Comunicação em tempo real | Server-Sent Events |
| Ambiente local | Docker Compose |
| Administração do banco | Adminer |

## Organização da aplicação

O ArtBid está organizado como um monorepo:

```text
apps/
├── api/
│   ├── alembic/           # Migrações do banco
│   ├── app/
│   │   ├── api/           # Rotas, dependências e middleware
│   │   ├── audit/         # Cadeia de auditoria e verificação
│   │   ├── core/          # Configuração e componentes transversais
│   │   ├── db/            # Sessões e acesso ao PostgreSQL
│   │   ├── integrations/  # Integrações externas
│   │   ├── models/        # Modelos SQLAlchemy
│   │   ├── realtime/      # Publicação e distribuição de eventos
│   │   ├── schemas/       # Contratos de entrada e saída
│   │   ├── services/      # Regras de negócio
│   │   └── tasks/         # Tarefas Celery
│   └── scripts/           # Utilitários
└── web/
    ├── public/            # Recursos estáticos
    └── src/
        ├── app/           # Páginas e rotas do BFF
        ├── components/    # Componentes de interface
        ├── hooks/         # Hooks de acesso aos dados
        ├── lib/           # Contratos e utilitários
        └── server/        # Comunicação com o backend

docs/
├── schema.sql             # Referência do esquema

compose.yaml              # Serviços do ambiente local
compose.prod.yaml         # Serviços do ambiente em produção
.env.example              # Exemplo de configuração
LICENSE                   # Licença MIT
```

### Separação de responsabilidades

**Frontend e BFF:** o Next.js apresenta a interface e disponibiliza rotas intermediárias para comunicação com o backend.

**API:** o FastAPI concentra autenticação, autorização, validação, regras de negócio e acesso aos dados.

**Processamento assíncrono:** os workers Celery executam tarefas como acompanhamento do ciclo de vida dos lotes, liquidação, distribuição de eventos e manutenção da auditoria.

**Persistência:** o PostgreSQL armazena utilizadores, lotes, lances, carteiras, movimentos, eventos e comprovativos.

## Executar localmente

### Pré-requisitos

- Docker instalado e em execução.
- Docker Compose disponível através de `docker compose`.
- Uma cópia local do repositório.

Os comandos seguintes devem ser executados na raiz do projecto, onde está o ficheiro `compose.yaml`.

### 1. Configurar o ambiente

```bash
cp .env.example .env
```

Edita o ficheiro `.env` com as credenciais locais:

```dotenv
POSTGRES_DB=artbid
POSTGRES_USER=artbid
POSTGRES_PASSWORD=SUBSTITUIR_POR_UMA_PASSWORD_FORTE
REDIS_URL=redis://redis:6379/0
```

### 2. Iniciar o banco e o Redis

```bash
docker compose up -d db redis
```

### 3. Construir a imagem da API e aplicar as migrações

```bash
docker compose build api
docker compose run --rm api alembic upgrade head
```

Usa as migrações como mecanismo de criação e evolução do banco. O ficheiro `docs/schema.sql` contém instruções destrutivas de recriação de tabelas e **não deve ser importado sobre uma base com dados a preservar**.

### 4. Iniciar os restantes serviços

```bash
docker compose up -d --build
```

### 5. Confirmar o estado

```bash
docker compose ps
docker compose logs --tail=100 api web celery-worker celery-beat
```

### 6. Seed de dados demostrativos

```bash
docker compose exec api python scripts/seed.py
```

## Endereços locais

| Serviço | Endereço |
| --- | --- |
| Aplicação web | [localhost:3000](http://localhost:3000) |
| Swagger UI | [localhost:8000/docs](http://localhost:8000/docs) |
| ReDoc | [localhost:8000/redoc](http://localhost:8000/redoc) |
| Health check | [localhost:8000/health](http://localhost:8000/health) |
| Readiness | [localhost:8000/health/ready](http://localhost:8000/health/ready) |
| Adminer | [localhost:8081](http://localhost:8081) |

No Adminer, selecciona **PostgreSQL**, utiliza `db` como servidor e introduz as credenciais definidas no `.env`.

> Estas ligações apontam para a máquina onde o Docker está a correr. O Compose disponibilizado associa as portas ao endereço de loopback.

## Configuração

Algumas das configurações utilizadas no projecto:

| Variável | Finalidade |
| --- | --- |
| `DATABASE_URL` | Ligação da API ao PostgreSQL |
| `REDIS_URL` | Ligação ao Redis |
| `CELERY_BROKER_URL` | Broker das tarefas Celery |
| `CELERY_RESULT_BACKEND` | Backend de resultados das tarefas |
| `API_BASE_URL` | Endereço do backend utilizado pelo Next.js |
| `API_TIMEOUT_MS` | Timeout dos pedidos do BFF |
| `TOKEN_TTL_SECONDS` | Prazo de validade dos tokens |
| `AUDIT_ALIAS_SECRET` | Segredo utilizado na geração de aliases |
| `AUDIT_CHECKPOINT_PRIVATE_KEY` | Chave privada para assinatura de checkpoints |
| `AUDIT_CHECKPOINT_PUBLIC_KEY` | Chave pública para verificação |
| `AUDIT_CHECKPOINT_KEY_ID` | Identificação da chave |
| `AUDIT_CHECKPOINT_EXPORT_DIR` | Directório opcional de exportação dos checkpoints |

**Atenção ao Docker Compose:** adicionar uma variável ao `.env` da raiz não significa que ela seja automaticamente disponibilizada a todos os contentores. Confirma o seu encaminhamento em `environment` ou `env_file`, sobretudo nos serviços `api`, `celery-worker` e `celery-beat`.

## Segurança e consistência

O projecto inclui mecanismos orientados à protecção dos fluxos de leilão:

- Autorização por perfil de utilizador.
- Validação de pedidos no frontend intermediário e na API.
- Armazenamento de hashes de palavras-passe e tokens.
- Limitação de frequência em operações seleccionadas.
- Chaves de idempotência em operações de escrita seleccionadas.
- Bloqueios transaccionais nas operações de carteira.
- Restrições de integridade no PostgreSQL.
- Aliases de licitantes associados ao contexto do lote.
- Cabeçalhos de segurança na aplicação web.

**Idempotência** permite reutilizar a mesma chave numa repetição do mesmo pedido sem executar novamente a operação, conforme as regras implementadas para esse fluxo.

## Integração com o catálogo de arte

O ArtBid utiliza a API do **Art Institute of Chicago** para pesquisa e consulta de obras.

A disponibilidade dos metadados e a entrega das imagens são dependências distintas. Restrições do fornecedor, incluindo desafios da Cloudflare, podem impedir o carregamento de imagens mesmo quando a pesquisa devolve resultados correctamente.

Tem uma [issue aberta](https://github.com/art-institute-of-chicago/api-data/issues/9) sobre esse problema ainda.

Para este projecto, desenvolvi uma pequena API que retorna imagens aleatórias de arte, compilada a partir do Dataset [Best Artworks of All Time](https://www.kaggle.com/datasets/ikarus777/best-artworks-of-all-time) do [Kaggle](https://www.kaggle.com/) para servir como fallback das imagens.

A licença do código do ArtBid não se estende automaticamente às imagens de terceiros.

## Auditoria à prova de adulteração

**Técnica escolhida: cadeia de hashes SHA-256 (hash chaining) + checkpoints assinados Ed25519 + triggers append-only.**

1. Cada evento de negócio (`lot.created`, `bid.accepted`, `lot.extended`, `lot.closed`, `lot.cancelled`, `lot.settled`) é gravado em `audit_events` com `sequence` monotónico por lote, `actor_alias` (pseudónimo), `data` (JSONB) e `occurred_at`.
2. O `hash` é calculado sobre o **JSON canónico** do evento (chaves ordenadas, sem espaços) concatenado com o `previous_hash`:

   ```
   hash_i = SHA256( canonical_json(evento_i) | previous_hash )
   ```

3. `GET /v1/audit?lotId=…` (público) **recalcula toda a cadeia** e compara com os hashes gravados. Detecta:
   - **alteração** de qualquer campo → `hash_mismatch`;
   - **remoção** de um evento → `sequence_gap_or_reorder` e quebra do `previous_hash`;
   - **inserção posterior** → sequência duplicada/desordenada e hash diferente a partir do ponto de inserção (o atacante teria de recalcular toda a cauda — e mesmo assim os checkpoints assinados denunciam a alteração).
4. `scripts/audit.sql` impede `UPDATE`, `DELETE` e `TRUNCATE` directamente no banco (triggers `ENABLE ALWAYS`).

**Resposta de `GET /v1/audit`:** além de `status`, devolve `reason` (`hash_mismatch`, `sequence_gap_or_reorder`, `previous_hash_mismatch`, `checkpoint_failed`, `checkpoint_pending`) e o par `expectedHash` / `calculatedHash`. A página `/audit` lê `reason` para explicar casos diferentes: uma divergência na cadeia mostra "Divergência encontrada entre o hash esperado e o calculado", enquanto `checkpoint_failed` mostra que a cadeia local está consistente mas a assinatura do checkpoint não foi confirmada. Sem `reason`, os dois casos pareceriam a mesma coisa.

## Comandos úteis

### Acompanhar os logs

```bash
docker compose logs -f api web
```

### Acompanhar as tarefas

```bash
docker compose logs -f celery-worker celery-beat
```

### Aplicar migrações

```bash
docker compose exec api alembic upgrade head
```

### Ver a revisão actual do banco

```bash
docker compose exec api alembic current
```

### Executar verificações do frontend

```bash
docker compose exec web npm run lint
docker compose exec web npm run typecheck
```

### Parar os serviços

```bash
docker compose down
```

**Preservação dos dados:** o banco utiliza um volume Docker. O comando `docker compose down` mantém os volumes; adicionar a opção `-v` remove os volumes geridos pelo Compose e pode apagar os dados persistidos.

## Roteiro de demonstração

### 1. Contas e dados de demonstração

**Palavra-passe para as 3 contas:** `artbid-demo-2026`

| Perfil | Email | O que pode fazer |
| --- | --- | --- |
| Leiloeiro | `leiloeiro@demo.artbid` | Pesquisar obras, criar/cancelar lotes, ver resultados e receita. **Não pode licitar.** |
| Licitante A | `licitante@demo.artbid` | Saldo 120.000,00 BRL; lidera um lote e já ganhou outro. |
| Licitante B | `coleccionador@demo.artbid` | Saldo 90.000,00 BRL; lidera o lote principal. |

### 2. Roteiro

1. Pesquisar uma obra e consultar os seus detalhes.
2. Criar um lote com datas e valores válidos.
3. Abrir outra sessão com uma conta de **licitante**.
4. Adicionar créditos à carteira.
5. Consultar um lote aberto e efectuar um lance.
6. Acompanhar os movimentos da carteira e a actividade do leilão.
7. Consultar o histórico de auditoria do lote.
8. Após o encerramento e a liquidação, consultar o resultado e o comprovativo.

O início, o encerramento e a liquidação dependem das datas dos lotes e dos serviços de processamento estarem activos.

## Comportamentos inesperados e limitações conhecidas

1. **Sessão expira em 15 minutos e não há refresh.** `TOKEN_TTL_SECONDS=900`. Quando expira, o front-end limpa a sessão e é preciso voltar a entrar. Para uma demonstração longa, aumente `TOKEN_TTL_SECONDS` (60–86400).
2. **Sem `beat` não há tempo real nem fecho de lotes.** A passagem a `live`, a liquidação, os eventos SSE e os checkpoints dependem do Celery beat. A contagem decrescente no browser é local; o estado oficial vem do servidor.
3. **Criar lotes exige a API online.** A pesquisa e a criação de um lote consultam o AIC. A vitrine/sala/auditoria/comprovante não. Se o AIC cair, a mensagem é `UPSTREAM_UNAVAILABLE` e pode tentar novamente.
4. **Imagens de lotes novos vêm do CDN IIIF do AIC.** Para este projecto, desenvolvi uma pequena API que retorna imagens aleatórias de arte, compilada a partir do Dataset [Best Artworks of All Time](https://www.kaggle.com/datasets/ikarus777/best-artworks-of-all-time) do [Kaggle](https://www.kaggle.com/) para servir como fallback das imagens.
5. **Integridade pode mostrar "Verificação indisponível".** Se as chaves de checkpoint estiverem configuradas mas ainda não existir um checkpoint que cubra o lote, o estado é `unavailable` (aguarda até 60 s). Sem chaves configuradas, a verificação da cadeia é reportada como `verified`.

### Uso de IA

A IA foi usada como ferramenta de análise, revisão e documentação. 

Foi utilizado o Figma make para a criação do template usado para o projeto, uma vez que utiliza o React js para a criação do mesmo. 

Após a criação do schema do projeto, usei o Deepseek para poder gerar os models e schemas do fast api. E foi utilizada também para poder transformar o template em React para Next JS.

## Notas para publicação

O `compose.yaml` disponibilizado está orientado ao desenvolvimento: o frontend utiliza `npm run dev` e a API utiliza `--reload`.

Para publicação em produção: usar `compose.prod.yaml`.

## Autor

**Leandro Ventura**

## Licença

Código distribuído sob a **licença MIT**, conforme o ficheiro `LICENSE` incluído no repositório.