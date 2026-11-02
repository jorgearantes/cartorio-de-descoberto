# Instruções para o Claude

## Agenda do Outlook (Microsoft 365)

A agenda é a do tabelião, no fuso `E. South America Standard Time` (Brasília).
Antes de marcar, confira se o horário está livre e avise sobre conflitos.

### Reuniões externas

- **Título:** `Reunião: Nome (Profissão)`, com o nome da pessoa exatamente como
  aparece na agenda/contatos. Ex.: `Reunião: Fernando Guedes (Advogado)`.
- **Duração padrão:** 1h, salvo indicação em contrário.
- **Local:** só o endereço, no formato `Rua/Av. Nome, número, Cidade, UF`.
  Ex.: `Av. Barão do Rio Branco, 2817, Juiz de Fora, MG`.
- **Descrição:** complemento do endereço (sala, andar). Ex.: `Sala 1004`.
- **Mostrar como:** Ocupado. Sem categoria.
- **Sem participantes**, a menos que o tabelião peça (convidados recebem e-mail).

### Locomoção

- Toda reunião externa leva um compromisso `Locomoção` de **30 minutos
  imediatamente antes**, terminando no horário de início da reunião.
- Mostrar como: Ocupado. Sem local nem descrição.
- **Categoria: `Rotina`.** O conector Microsoft 365 do claude.ai cria o
  compromisso mas não aplica categoria. Quando o MCP do cartório (perfil
  tabelião) estiver conectado, crie a reunião com `agenda_criar` (com `local`
  ela já cria a Locomoção de 30 min antes) e confira em `agenda_listar` se a
  Locomoção ficou com `Rotina`; se não, corrija com `agenda_alterar`
  (`categorias_csv="Rotina"`). Sem o MCP do cartório, crie pelo conector do
  claude.ai e lembre o tabelião de marcar a categoria `Rotina` manualmente.

### Categorizar compromissos (MCP do cartório)

- Um compromisso: `agenda_alterar` com `categorias_csv`. Vários de uma vez:
  `agenda_categorizar` com `itens_json` (`[{"id": "...", "categorias":
  ["Rotina"]}]`). Os ids vêm de `agenda_listar`; os nomes exatos, de
  `agenda_categorias`.
- Sempre chame primeiro sem `confirmar`, mostre o resultado e só grave com
  `confirmar=True` depois do sim.

### Outras categorias usadas na agenda

`Rotina` (café, almoço, locomoção), `Saúde` (academia), `BNI`,
`Beatriz/Alice` (levar e buscar na escola), `Pessoal`.
