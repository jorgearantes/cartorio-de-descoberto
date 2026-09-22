"""Gera as cotações em PDF para Sandro Borges (22/09/2026).

1) Escritura Pública de Inventário e Partilha (fração de 50% do imóvel)
2) Escritura Pública de Compra e Venda (100% do imóvel para Sandro Borges)

Os emolumentos, TFJ e Recompe ficam em aberto para lançamento pelo sistema
do cartório (Tabela 2026 - Lei Estadual 15.424/2004).
"""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

OUT = Path(__file__).parent
FONT_DIR = "/usr/share/fonts/truetype/liberation"
pdfmetrics.registerFont(TTFont("DV", f"{FONT_DIR}/LiberationSans-Regular.ttf"))
pdfmetrics.registerFont(TTFont("DVB", f"{FONT_DIR}/LiberationSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("DVI", f"{FONT_DIR}/LiberationSans-Italic.ttf"))
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DVB", italic="DVI")

AZUL = colors.HexColor("#1F3A5F")
CINZA = colors.HexColor("#F2F4F7")
AMARELO = colors.HexColor("#FFF6DB")

ss = getSampleStyleSheet()
S = {
    "t": ParagraphStyle("t", parent=ss["Title"], fontName="DVB", fontSize=14,
                        textColor=AZUL, spaceAfter=2, leading=17),
    "st": ParagraphStyle("st", parent=ss["Normal"], fontName="DV", fontSize=8.5,
                         alignment=TA_CENTER, textColor=colors.grey),
    "h": ParagraphStyle("h", parent=ss["Heading2"], fontName="DVB", fontSize=10.5,
                        textColor=AZUL, spaceBefore=9, spaceAfter=4),
    "p": ParagraphStyle("p", parent=ss["Normal"], fontName="DV", fontSize=8.8,
                        leading=11.8, spaceAfter=3),
    "b": ParagraphStyle("b", parent=ss["Normal"], fontName="DV", fontSize=8.8,
                        leading=11.8, leftIndent=10, bulletIndent=0, spaceAfter=2),
    "c": ParagraphStyle("c", parent=ss["Normal"], fontName="DV", fontSize=8.5,
                        leading=10.5),
    "cb": ParagraphStyle("cb", parent=ss["Normal"], fontName="DVB", fontSize=8.5,
                         leading=10.5),
    "sm": ParagraphStyle("sm", parent=ss["Normal"], fontName="DVI", fontSize=7.6,
                         leading=9.5, textColor=colors.HexColor("#555555")),
}

A_PREENCHER = "<i>a lançar pelo sistema</i>"


def brl(v):
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def tabela(linhas, larguras, header=True, destaque_ultima=False):
    dados = [[Paragraph(str(c), S["cb" if (header and i == 0) else "c"]) for c in l]
             for i, l in enumerate(linhas)]
    t = Table(dados, colWidths=larguras, repeatRows=1 if header else 0)
    estilo = [
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C9CED6")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if header:
        estilo.append(("BACKGROUND", (0, 0), (-1, 0), CINZA))
    if destaque_ultima:
        estilo.append(("BACKGROUND", (0, -1), (-1, -1), AMARELO))
    t.setStyle(TableStyle(estilo))
    return t


def bullets(itens):
    return [Paragraph(i, S["b"], bulletText="•") for i in itens]


def cabecalho(titulo, numero):
    return [
        Paragraph("CARTÓRIO DE DESCOBERTO/MG", S["t"]),
        Paragraph("Tabelionato de Notas · Tabelião Jorge Arantes · "
                  "0800 591 4458 · (32) 3142-0642 (WhatsApp) · "
                  "cartoriodescoberto.com", S["st"]),
        Spacer(1, 8),
        Paragraph(titulo, ParagraphStyle("tt", parent=S["t"], fontSize=12.5)),
        Spacer(1, 4),
        tabela([
            ["Cotação nº", numero, "Data", "22/09/2026"],
            ["Solicitante", "Dr. Sandro Borges (Advogado – Power Mind, BH)",
             "Validade", "30 dias ou até reajuste da tabela"],
        ], [24 * mm, 80 * mm, 20 * mm, 46 * mm], header=False),
    ]


def rodape(canvas, doc):
    canvas.saveState()
    canvas.setFont("DV", 7)
    canvas.setFillColor(colors.grey)
    canvas.drawString(18 * mm, 10 * mm,
                      "Cotação estimativa, sem valor de recibo. Valores definitivos "
                      "após análise documental e avaliações fiscais (SEF/MG e Prefeitura).")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Página {doc.page}")
    canvas.restoreState()


def gerar(nome, story):
    doc = SimpleDocTemplate(str(OUT / nome), pagesize=A4, leftMargin=18 * mm,
                            rightMargin=18 * mm, topMargin=14 * mm, bottomMargin=16 * mm,
                            title=nome[:-4], author="Cartório de Descoberto/MG")
    doc.build(story, onFirstPage=rodape, onLaterPages=rodape)


# ---------------------------------------------------------------- parâmetros
VALOR_MERCADO = 450_000.00
VALOR_IPTU = 300_000.00
FRACAO_INVENTARIO = 0.50
BASE_ITCD = VALOR_MERCADO * FRACAO_INVENTARIO
ALIQ_ITCD = 0.05
ITCD = BASE_ITCD * ALIQ_ITCD
ALIQ_ITBI_REF = 0.02
ITBI = VALOR_MERCADO * ALIQ_ITBI_REF
MULTA_MAX_ESPONTANEA = 0.12

W = [60 * mm, 40 * mm, 74 * mm]

# ================================================================ INVENTÁRIO
inv = cabecalho("Escritura Pública de Inventário e Partilha<br/>"
                "<font size=9>(extrajudicial – fração de 50% do imóvel pertencente à falecida)</font>",
                "2026/09-SB-01")
inv += [
    Paragraph("1. Objeto", S["h"]),
    Paragraph(
        "Inventário extrajudicial e partilha dos direitos da falecida (nome a informar) sobre o "
        "imóvel prometido à venda ao Dr. Sandro Borges em dezembro/1993, com preço quitado em "
        "janeiro/1994. Como não há prova inequívoca de quitação em vida (recibo com firma "
        "reconhecida, comprovante bancário ou documento equivalente), é preciso inventariar a "
        "parte dela para, em seguida, lavrar a compra e venda (Cotação 2026/09-SB-02). "
        "As duas escrituras podem ser lavradas no mesmo dia, inclusive de forma eletrônica "
        "(e-Notariado, por videoconferência).", S["p"]),

    Paragraph("2. Parâmetros considerados", S["h"]),
    tabela([
        ["Parâmetro", "Valor considerado", "Fonte / observação"],
        ["Valor de mercado do imóvel (100%)", brl(VALOR_MERCADO),
         "Informado pelo solicitante. Usado no lugar do valor do IPTU "
         f"(≈ {brl(VALOR_IPTU)}) porque é o parâmetro que SEF/MG e Prefeitura tendem a adotar."],
        ["Fração inventariada", "50% (meação da falecida)",
         "Presume casamento em comunhão (universal, ou parcial com aquisição onerosa "
         "na constância). A outra metade é do cônjuge sobrevivente e não é inventariada."],
        ["Base de cálculo do ITCD", brl(BASE_ITCD),
         "50% × valor de mercado. Prevalece a avaliação da SEF/MG."],
        ["Alíquota do ITCD/MG", "5%", "Lei Estadual 14.941/2003, art. 10."],
        ["Herdeiros", "Não informados",
         "Presume-se que são todos maiores, capazes e concordes. Número e qualificação "
         "não alteram o ITCD total, mas afetam certidões e procuração."],
        ["Data do óbito", "Não informada", "Define se há multa e juros sobre o ITCD (item 5)."],
        ["ISSQN", "Não incide", "O Município de Descoberto não cobra ISSQN sobre atos notariais."],
    ], W),

    Paragraph("3. Quadro de custos", S["h"]),
    tabela([
        ["Item", "Valor", "Observação"],
        ["ITCD (5% × " + brl(BASE_ITCD) + ")", brl(ITCD),
         "Recolhido à SEF/MG antes da escritura. Valor sem multa/juros."],
        ["Multa e juros de mora sobre o ITCD", "Depende da data do óbito",
         f"Referência: multa espontânea de até 12% ({brl(ITCD * MULTA_MAX_ESPONTANEA)}) + SELIC. Ver item 5."],
        ["Emolumentos – escritura de inventário e partilha", A_PREENCHER,
         "Tabela 2026 (Lei 15.424/2004), sobre a base de " + brl(BASE_ITCD)
         + " ou a avaliação fiscal, se maior."],
        ["Taxa de Fiscalização Judiciária (TFJ)", A_PREENCHER, "Vinculada à faixa da escritura."],
        ["Recompe", A_PREENCHER, "Vinculado à faixa da escritura."],
        ["Arquivamentos, traslado, certidões e comunicações (CENSEC/DOI/CNIB)", A_PREENCHER,
         "Conforme quantidade de documentos e de partes."],
        ["Total estimado", brl(ITCD) + " + emolumentos",
         "Sem multa/juros do ITCD e sem o registro no Cartório de Imóveis."],
    ], W, destaque_ultima=True),
    Paragraph("Não incluídos: registro da partilha no Cartório de Registro de Imóveis, "
              "honorários advocatícios e certidões pedidas fora do cartório.", S["sm"]),

    Paragraph("4. Ressalvas quanto aos herdeiros e à via extrajudicial", S["h"]),
    *bullets([
        "É preciso saber <b>se o casal teve filhos</b> e se todos são <b>maiores e capazes</b>. "
        "Se não houver descendentes, herdam os ascendentes vivos e/ou o cônjuge (CC, art. 1.829). "
        "Se algum herdeiro já tiver falecido, entram os sucessores dele por representação.",
        "Havendo herdeiro menor ou incapaz, a via extrajudicial só é possível nas hipóteses da "
        "Resolução CNJ 35/2007 (com as alterações da Res. CNJ 571/2024), que exigem partilha em "
        "partes ideais e manifestação do Ministério Público. Caso contrário, o inventário é judicial.",
        "Todos os herdeiros e o cônjuge sobrevivente devem concordar com a partilha e estar "
        "assistidos por advogado. <b>Como o Dr. Sandro é o comprador, convém avaliar se ele "
        "pode, sem conflito de interesses, assistir os herdeiros</b> (pode ser preciso outro "
        "advogado).",
        "O <b>cônjuge sobrevivente</b> precisa estar vivo e capaz. Se também tiver falecido, "
        "será preciso outro inventário (do meeiro), o que aumenta o custo.",
        "Se a falecida deixou <b>outros bens</b>, eles entram na Declaração de ITCD. A escritura "
        "pode tratar só deste imóvel, deixando os demais para sobrepartilha, conforme a análise.",
        "Herdeiros casados comparecem com o cônjuge, salvo no regime de separação total de bens.",
    ]),

    Paragraph("5. Ressalva sobre multa e juros do ITCD", S["h"]),
    *bullets([
        "Em MG, o ITCD <i>causa mortis</i> vence em <b>180 dias contados do óbito</b> "
        "(Lei 14.941/2003, art. 13). Pagamento após o prazo tem <b>multa de mora</b> "
        "(Lei 6.763/1975, art. 56: 0,15% ao dia até 30 dias, 9% do 31º ao 90º dia e 12% após "
        "90 dias, quando o pagamento é espontâneo) e <b>juros pela SELIC</b> desde o vencimento.",
        "Como a compra foi em 1993 e o óbito pode ser antigo, <b>é provável que haja multa e juros</b>. "
        f"Referência: 12% de {brl(ITCD)} = {brl(ITCD * MULTA_MAX_ESPONTANEA)}, mais a SELIC acumulada, "
        "que pode ser relevante se o óbito for antigo.",
        "Se o fisco lavrar auto de infração antes do pagamento espontâneo, a penalidade é maior "
        "(multa de revalidação). Por isso, recomenda-se declarar e recolher espontaneamente.",
        "Aplicam-se a lei e a alíquota <b>vigentes na data do óbito</b> (STF, Súmula 112). "
        "Se o óbito for anterior à Lei 14.941/2003, as regras de alíquota e multa devem ser conferidas.",
        "O valor exato será calculado pela SEF/MG na Declaração de Bens e Direitos (DBD), com base "
        "na data do óbito e na avaliação do imóvel.",
    ]),

    Paragraph("6. Documentos necessários (verificação prévia)", S["h"]),
    *bullets([
        "<b>Falecida:</b> certidão de óbito; RG/CPF; certidão de casamento atualizada (até 90 dias) "
        "e pacto antenupcial, se houver; CND de tributos federais (Receita/PGFN) em nome dela.",
        "<b>Cônjuge sobrevivente e herdeiros:</b> RG, CPF, comprovante de endereço, profissão; "
        "certidões de nascimento/casamento atualizadas; dados dos cônjuges dos herdeiros.",
        "<b>Imóvel:</b> certidão de inteiro teor da matrícula com ônus reais e ações reipersecutórias "
        "(até 30 dias); CND de IPTU/débitos municipais; espelho do IPTU. Se rural: CCIR, ITR (5 anos), "
        "CAR e georreferenciamento, quando exigido.",
        "<b>Tributário:</b> Declaração de Bens e Direitos (DBD) do ITCD na SEF/MG, DAE pago e "
        "Certidão de Pagamento/Desoneração do ITCD.",
        "<b>A cargo do cartório:</b> busca de testamento (CENSEC), consulta à CNIB (indisponibilidade), "
        "DOI e demais comunicações.",
        "<b>Advogado:</b> OAB e minuta/esboço da partilha.",
        "A lista pode aumentar após a análise da matrícula (por exemplo, se o imóvel não estiver em "
        "nome do casal ou houver averbações pendentes).",
    ]),
    Spacer(1, 8),
    Paragraph("Cartório de Descoberto/MG – Jorge Arantes, Tabelião e Registrador Civil.", S["sm"]),
]
gerar("Cotacao_01_Inventario_Proporcional_Sandro_Borges.pdf", inv)

# ================================================================ COMPRA E VENDA
cv = cabecalho("Escritura Pública de Compra e Venda<br/>"
               "<font size=9>(100% do imóvel – adquirente: Dr. Sandro Borges)</font>",
               "2026/09-SB-02")
cv += [
    Paragraph("1. Objeto", S["h"]),
    Paragraph(
        "Compra e venda do imóvel adquirido pelo Dr. Sandro Borges em dezembro/1993 (entrada + "
        "duas parcelas pagas em janeiro/1994). Os vendedores são o cônjuge sobrevivente (meação "
        "de 50%) e os herdeiros da falecida (50% recebidos na partilha, Cotação 2026/09-SB-01). "
        "O preço é declarado como já pago, com quitação dada pelos vendedores na própria escritura.",
        S["p"]),

    Paragraph("2. Parâmetros considerados", S["h"]),
    tabela([
        ["Parâmetro", "Valor considerado", "Fonte / observação"],
        ["Valor de mercado do imóvel (100%)", brl(VALOR_MERCADO),
         f"Informado pelo solicitante. Não foi usado o valor do IPTU (≈ {brl(VALOR_IPTU)})."],
        ["Fração transmitida", "100%", "50% do meeiro + 50% dos herdeiros."],
        ["Base de cálculo (ITBI e emolumentos)", brl(VALOR_MERCADO),
         "O maior valor entre o preço declarado e a avaliação fiscal. Como o preço histórico "
         "(1993) é baixo, a base tende a ser a avaliação da Prefeitura."],
        ["Alíquota do ITBI", "2% (referência)",
         "<b>Município do imóvel a confirmar.</b> A alíquota e eventuais isenções dependem do "
         "Código Tributário Municipal (em BH, por exemplo, é 3%)."],
        ["ISSQN", "Não incide", "O Município de Descoberto não cobra ISSQN sobre atos notariais."],
    ], W),

    Paragraph("3. Quadro de custos", S["h"]),
    tabela([
        ["Item", "Valor", "Observação"],
        ["ITBI (2% × " + brl(VALOR_MERCADO) + ")", brl(ITBI),
         "Referência. Recolhido à Prefeitura do imóvel antes da escritura. "
         f"A 3%, seria {brl(VALOR_MERCADO * 0.03)}."],
        ["Emolumentos – escritura de compra e venda", A_PREENCHER,
         "Tabela 2026 (Lei 15.424/2004), sobre " + brl(VALOR_MERCADO)
         + " ou a avaliação fiscal, se maior."],
        ["Taxa de Fiscalização Judiciária (TFJ)", A_PREENCHER, "Vinculada à faixa da escritura."],
        ["Recompe", A_PREENCHER, "Vinculado à faixa da escritura."],
        ["Arquivamentos, traslado, certidões e comunicações (DOI/CNIB)", A_PREENCHER,
         "Conforme quantidade de documentos e de partes."],
        ["Total estimado", brl(ITBI) + " + emolumentos",
         "Sem o registro no Cartório de Imóveis."],
    ], W, destaque_ultima=True),
    Paragraph("Não incluídos: registro da compra e venda no Cartório de Registro de Imóveis e "
              "honorários advocatícios.", S["sm"]),

    Paragraph("4. Custo consolidado das duas escrituras (impostos)", S["h"]),
    tabela([
        ["Imposto", "Valor", "Observação"],
        ["ITCD – inventário (50%)", brl(ITCD), "Sem multa/juros (dependem da data do óbito)."],
        ["ITBI – compra e venda (100%)", brl(ITBI), "Referência de 2%. Depende do município."],
        ["Total de impostos estimado", brl(ITCD + ITBI),
         "Somam-se os emolumentos, a TFJ e o Recompe das duas escrituras, a lançar pelo sistema."],
    ], W, destaque_ultima=True),

    Paragraph("5. Ressalvas", S["h"]),
    *bullets([
        "A compra e venda depende do <b>inventário lavrado antes ou no mesmo ato</b>: sem a partilha, "
        "os herdeiros não têm título para vender a fração da falecida.",
        "<b>Todos os vendedores</b> (meeiro, herdeiros e seus cônjuges, salvo separação total) "
        "precisam assinar, pessoalmente, por videoconferência (e-Notariado) ou por procurador com "
        "procuração pública.",
        "Idade avançada do vendedor não impede o ato, mas o tabelião verifica a capacidade e a "
        "livre manifestação de vontade na assinatura.",
        "Alternativa possível: <b>cessão de direitos hereditários</b> do bem ao Dr. Sandro seguida de "
        "adjudicação, no mesmo ato. Essa via também tem ITCD e ITBI (a cessão onerosa gera ITBI); "
        "a comparação de custos pode ser feita se houver interesse.",
        "Se o imóvel for rural, somam-se CCIR, ITR, CAR e georreferenciamento, e a base de cálculo "
        "segue a avaliação do imóvel rural.",
        "Os valores de ITBI e ITCD podem mudar com as avaliações da Prefeitura e da SEF/MG, "
        "que prevalecem sobre o valor informado.",
    ]),

    Paragraph("6. Documentos necessários (verificação prévia)", S["h"]),
    *bullets([
        "<b>Vendedores:</b> RG, CPF, certidão de casamento/nascimento atualizada (até 90 dias), "
        "comprovante de endereço e profissão; dados dos cônjuges.",
        "<b>Comprador (Dr. Sandro):</b> RG, CPF, certidão de casamento/nascimento atualizada, "
        "comprovante de endereço, profissão e dados do cônjuge, se casado.",
        "<b>Imóvel:</b> matrícula atualizada com ônus reais (até 30 dias); CND de IPTU; guia do ITBI "
        "paga; certidão de quitação condominial, se for condomínio.",
        "<b>Certidões dos vendedores (recomendadas):</b> CNDT, certidões de feitos cíveis e "
        "fiscais; consulta à CNIB feita pelo cartório.",
        "Documentos do contrato de 1993/1994 (promessa, recibos, se houver): não são indispensáveis, "
        "mas ajudam a descrever o histórico do negócio na escritura.",
    ]),
    Spacer(1, 8),
    Paragraph("Cartório de Descoberto/MG – Jorge Arantes, Tabelião e Registrador Civil.", S["sm"]),
]
gerar("Cotacao_02_Compra_e_Venda_Sandro_Borges.pdf", cv)
print("ok", ITCD, ITBI)
