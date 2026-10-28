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
  compromisso mas não aplica categoria. Depois de criar, marque `Rotina` com a
  tool `agenda_categorizar` do MCP do cartório (perfil tabelião): pegue o id com
  `agenda_compromissos` (ou o id devolvido pela criação), simule, mostre e grave
  com `confirmar=True`. Se o MCP do cartório não estiver conectado ou responder
  403, lembre o tabelião de marcar a categoria `Rotina` manualmente.

### Categorizar compromissos

- Categoria em compromisso já existente: `agenda_categorizar` (põe e tira, sem
  mexer em horário, assunto ou convidados). Os nomes válidos vêm de
  `agenda_categorias`.
- Sempre simule primeiro e mostre o antes → depois. Id de série recorrente muda
  a série inteira.

### Outras categorias usadas na agenda

`Rotina` (café, almoço, locomoção), `Saúde` (academia), `BNI`,
`Beatriz/Alice` (levar e buscar na escola), `Pessoal`.
