# API REST — Sistema de Gerenciamento de Confecção

Documentação inicial dos endpoints para a aplicação de gerenciamento de clientes e pedidos de uma empresa de confecção de roupas.

> **Observação:** esta é uma proposta inicial de API. Os nomes dos campos, regras de negócio, códigos HTTP e formatos das respostas podem ser ajustados durante a implementação.

## Sumário

- [Visão geral](#visão-geral)
- [Convenções](#convenções)
- [Clientes](#clientes)
- [Pedidos](#pedidos)
- [Itens dos pedidos](#itens-dos-pedidos)
- [Relatórios](#relatórios)
- [Regras de negócio sugeridas](#regras-de-negócio-sugeridas)
- [Prioridade de implementação](#prioridade-de-implementação)

## Visão geral

A API permite:

- Cadastrar, consultar, editar e excluir clientes.
- Cadastrar e gerenciar pedidos vinculados a clientes.
- Adicionar vários itens a um pedido.
- Registrar referência, modelo, tecido, cor e quantidades por tamanho.
- Consultar pedidos por cliente, mês, ano, período e status.
- Obter indicadores para o dashboard e relatórios.

### Relacionamento principal

```text
Cliente 1 ───── N Pedido 1 ───── N Item do pedido
```

Um cliente pode possuir vários pedidos, e cada pedido pode conter vários itens. Cada item representa uma referência/modelo de roupa com seu próprio tecido, cor, grade de tamanhos, quantidades e valor.

## Convenções

- **Base URL sugerida:** `/api/v1`
- **Formato:** JSON
- **Datas:** `YYYY-MM-DD`
- **Valores monetários:** números decimais, por exemplo `800.00`.
- **Identificadores:** IDs únicos gerados pelo sistema.
- Os exemplos de dados deste documento são fictícios.

Os exemplos abaixo mostram os caminhos sem o prefixo `/api/v1`. Por exemplo, `GET /clientes` corresponde a `GET /api/v1/clientes` se o prefixo for adotado.

### Métodos HTTP

| Método | Uso |
|---|---|
| `GET` | Consultar dados |
| `POST` | Criar um recurso |
| `PUT` | Substituir/atualizar um recurso |
| `PATCH` | Atualizar parcialmente um recurso |
| `DELETE` | Excluir um recurso |

## Clientes

### `POST /clientes` — Cadastrar cliente

Cria um novo cliente.

**Exemplo de requisição:**

```json
{
  "nome": "Maria Confecções",
  "telefone": "44999999999",
  "email": "maria@email.com",
  "documento": "12345678000199",
  "endereco": "Rua das Flores, 123"
}
```

**Resposta esperada:** `201 Created`, com o cliente cadastrado e seu ID.

### `GET /clientes` — Listar clientes

Retorna a lista de clientes.

**Parâmetros de consulta opcionais:**

| Parâmetro | Descrição | Exemplo |
|---|---|---|
| `busca` | Pesquisa por nome ou telefone | `?busca=Maria` |
| `pagina` | Página dos resultados, se houver paginação | `?pagina=1` |
| `limite` | Quantidade de resultados por página | `?limite=20` |

**Exemplo:** `GET /clientes?busca=Maria`

### `GET /clientes/{id}` — Consultar cliente

Retorna os dados de um cliente específico.

**Exemplo:** `GET /clientes/1`

### `PUT /clientes/{id}` — Editar cliente

Atualiza os dados de um cliente existente.

**Exemplo:** `PUT /clientes/1`

```json
{
  "nome": "Maria Confecções",
  "telefone": "44988887777",
  "email": "contato@mariaconfeccoes.com",
  "documento": "12345678000199",
  "endereco": "Rua das Flores, 456"
}
```

### `PATCH /pedidos/{id}/status` — Atualizar status do pedido

Atualiza somente o status do pedido.

**Exemplo:** `PATCH /cliente/1/status`

```json
{
  "status": "ativo"
}
```

Os status devem ser definidos pelo grupo: `ativo` e `desativado`.


### `DELETE /clientes/{id}` — Excluir cliente

Solicita a exclusão de um cliente.

**Exemplo:** `DELETE /clientes/1`

**Regra sugerida:** se o cliente possuir pedidos associados, bloquear a exclusão ou utilizar exclusão lógica, para preservar o histórico.

## Pedidos

### `POST /pedidos` — Cadastrar pedido

Cria um pedido associado a um cliente.

**Exemplo de requisição:**

```json
{
  "cliente_id": 1,
  "data_pedido": "2026-10-08",
  "observacoes": "Entregar até o fim do mês"
}
```

Os itens podem ser adicionados depois por meio de `POST /pedidos/{id}/itens`, ou incluídos no cadastro inicial se a API for projetada para aceitar o pedido completo de uma só vez.

### `GET /pedidos` — Listar e filtrar pedidos

Retorna os pedidos cadastrados. Pode aceitar os seguintes parâmetros:

| Parâmetro | Descrição | Exemplo |
|---|---|---|
| `cliente_id` | Filtra pelo cliente | `?cliente_id=1` |
| `mes` | Mês do pedido, de 1 a 12 | `?mes=10` |
| `ano` | Ano do pedido | `?ano=2026` |
| `data_inicio` | Data inicial do período | `?data_inicio=2026-10-01` |
| `data_fim` | Data final do período | `?data_fim=2026-10-15` |
| `status` | Filtra pelo status | `?status=em_producao` |

**Exemplos:**

- `GET /pedidos?cliente_id=1`
- `GET /pedidos?mes=10&ano=2026`
- `GET /pedidos?data_inicio=2026-10-01&data_fim=2026-10-15`
- `GET /pedidos?status=em_producao`

### `GET /pedidos/{id}` — Consultar pedido

Retorna os dados de um pedido específico, podendo incluir seus itens.

**Exemplo:** `GET /pedidos/105`

### `PUT /pedidos/{id}` — Editar pedido

Atualiza os dados gerais de um pedido.

**Exemplo:** `PUT /pedidos/105`

```json
{
  "cliente_id": 1,
  "data_pedido": "2026-10-09",
  "observacoes": "Entrega combinada para sexta-feira"
}
```

### `PATCH /pedidos/{id}/status` — Atualizar status do pedido

Atualiza somente o status do pedido.

**Exemplo:** `PATCH /pedidos/105/status`

```json
{
  "status": "em_producao"
}
```

Os status devem ser definidos pelo grupo. Uma sugestão inicial: `recebido`, `em_producao`, `concluido`, `entregue` e `cancelado`.

### `DELETE /pedidos/{id}` — Excluir pedido

Solicita a exclusão de um pedido.

**Exemplo:** `DELETE /pedidos/105`

**Regra sugerida:** definir se a exclusão será permitida para qualquer pedido ou apenas para pedidos que ainda não foram concluídos/entregues. Outra opção é utilizar cancelamento ou exclusão lógica para preservar o histórico.

## Itens dos pedidos

Cada pedido pode conter vários itens. Um item corresponde a uma referência/modelo e possui tecido, cor, quantidades por tamanho e valor.

### `POST /pedidos/{id}/itens` — Adicionar item

Adiciona um item a um pedido existente.

**Exemplo de requisição para camiseta:**

```json
{
  "referencia": "REF-001",
  "modelo": "Camiseta",
  "tecido": "Algodão",
  "cor": "Preta",
  "quantidades": {
    "PP": 0,
    "P": 20,
    "M": 10,
    "G": 10,
    "GG": 0
  },
  "valor_total": 800.00
}
```

Para jeans, a grade pode usar os tamanhos numéricos:

```json
{
  "referencia": "REF-002",
  "modelo": "Calça jeans",
  "tecido": "Jeans",
  "cor": "Azul",
  "quantidades": {
    "36": 5,
    "38": 10,
    "40": 15,
    "42": 10,
    "44": 5,
    "46": 3,
    "48": 2,
    "50": 0
  },
  "valor_total": 1200.00
}
```

O campo `valor_total` é ilustrativo. O grupo deve definir se o valor será digitado pelo usuário ou calculado com base no preço por peça.

### `GET /pedidos/{id}/itens` — Listar itens do pedido

Retorna todos os itens associados a um pedido.

**Exemplo:** `GET /pedidos/105/itens`

### `GET /itens-pedido/{id}` — Consultar item

Retorna os dados de um item específico.

**Exemplo:** `GET /itens-pedido/501`

### `PUT /itens-pedido/{id}` — Editar item

Atualiza os dados de um item, incluindo referência, modelo, tecido, cor, grade de tamanhos, quantidades e valor.

**Exemplo:** `PUT /itens-pedido/501`

O corpo da requisição segue a mesma estrutura de um item enviado no endpoint de criação.

### `DELETE /itens-pedido/{id}` — Remover item

Remove um item de um pedido.

**Exemplo:** `DELETE /itens-pedido/501`

## Relatórios

Os endpoints de relatório são consultas agregadas que podem alimentar os cartões e gráficos do dashboard.

### `GET /relatorios/dashboard` — Indicadores gerais

Retorna um resumo para a tela inicial.

**Parâmetros opcionais:** `mes` e `ano`.

**Exemplo:** `GET /relatorios/dashboard?mes=10&ano=2026`

**Exemplo de resposta:**

```json
{
  "total_clientes": 12,
  "pedidos_no_mes": 28,
  "total_pecas": 1245,
  "valor_total_pedidos": 28750.00
}
```

Os números são apenas ilustrativos.

### `GET /relatorios/faturamento` — Resumo financeiro

Retorna os valores agregados dos pedidos em determinado período.

**Parâmetros sugeridos:** `data_inicio`, `data_fim`, `cliente_id` e, se necessário, `status`.

**Exemplo:** `GET /relatorios/faturamento?data_inicio=2026-10-01&data_fim=2026-10-31`

> Definam se o relatório representa o valor dos pedidos registrados, concluídos, entregues ou efetivamente pagos. Esses conceitos não são equivalentes.

### `GET /relatorios/pecas` — Resumo de quantidades

Retorna a quantidade de peças em determinado período, podendo agrupar os resultados por modelo, referência, tamanho ou cliente.

**Exemplo:** `GET /relatorios/pecas?mes=10&ano=2026`

### `GET /relatorios/clientes/{id}` — Histórico do cliente

Retorna um resumo do histórico de pedidos de um cliente.

**Exemplo:** `GET /relatorios/clientes/1`

Pode incluir quantidade de pedidos, total de peças e valor acumulado, conforme as regras definidas pelo grupo.

## Regras de negócio sugeridas

1. Todo pedido deve estar associado a um cliente existente.
2. Um pedido pode possuir vários itens.
3. Cada item deve conter referência, modelo, tecido, cor e quantidades por tamanho.
4. As quantidades devem ser números inteiros não negativos.
5. O sistema deve validar a grade de tamanhos permitida para cada tipo de peça.
6. O total de peças de um item deve ser calculado pela soma de suas quantidades por tamanho.
7. O total de peças de um pedido deve corresponder à soma dos totais de seus itens.
8. O sistema deve definir se o valor total é informado manualmente ou calculado a partir do preço unitário.
9. A exclusão de clientes e pedidos deve preservar a integridade do histórico.
10. Os filtros de período devem funcionar com datas inicial e final, sem exigir a criação de tabelas mensais ou quinzenais.

### Respostas HTTP sugeridas

| Código | Significado |
|---|---|
| `200 OK` | Consulta ou atualização realizada |
| `201 Created` | Recurso criado |
| `204 No Content` | Exclusão realizada sem corpo de resposta |
| `400 Bad Request` | Requisição inválida |
| `404 Not Found` | Recurso não encontrado |
| `409 Conflict` | Conflito com uma regra ou recurso existente |
| `422 Unprocessable Entity` | Dados enviados não passaram pela validação |

## Prioridade de implementação

### Essencial

- CRUD de clientes.
- CRUD de pedidos.
- CRUD de itens do pedido.
- Associação entre clientes e pedidos.
- Grades de tamanhos e quantidades.
- Registro de referência, modelo, tecido e cor.

### Recomendado

- Pesquisa de clientes.
- Filtros por cliente e período.
- Cálculo automático do total de peças.
- Status dos pedidos.
- Dashboard e relatórios básicos.

### Opcional

- Autenticação e login.
- Exportação para Excel ou PDF.
- Histórico de alterações.
- Cadastro separado de tecidos e modelos reutilizáveis.

---

**Nota final:** não é necessário criar um endpoint para cada botão da interface. Várias telas podem utilizar o mesmo endpoint, com parâmetros diferentes. Esta documentação serve como ponto de partida e deve ser alinhada à arquitetura e aos requisitos definidos pelo grupo.
