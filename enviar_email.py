import html
import os
import smtplib
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import config_rede

TIMEOUT_SMTP = 180
SEPARADOR = "=" * 60


def carregar_config_email():
    return config_rede.carregar_email()


def _log_erro_email(arquivo_log, mensagem):
    print(mensagem)

    if arquivo_log and os.path.exists(arquivo_log):
        try:
            with open(arquivo_log, "a", encoding="utf-8") as arquivo:
                arquivo.write(f"\n[EMAIL] {mensagem}\n")
        except OSError:
            pass


def mensagem_da_loja(resultado):
    if resultado == "SUCESSO":
        return "copiado com sucesso"
    if resultado == "JA_EXISTE":
        return "o arquivo já estava na pasta da loja (nada foi copiado)"
    if resultado == "FALHA_SEM_PASTA":
        return "NÃO COPIADO - a pasta da loja não foi encontrada no destino"
    if resultado == "FALHA_COPIA":
        return "NÃO COPIADO - falha ao copiar para a pasta da loja"
    return "NÃO COPIADO - ocorreu um erro na cópia"


def linha_com_pontos(texto, numero):
    pontos = "." * (40 - len(texto))
    return f"   {texto} {pontos} {numero}"


def linhas_do_arquivo(item):
    linhas = [item["arquivo"]]

    for numero, resultado in sorted(item.get("lojas", {}).items()):
        linhas.append(f"   Loja {numero}: {mensagem_da_loja(resultado)}")

    linhas.append("")
    return linhas


def linhas_da_secao(titulo, explicacao, itens):
    linhas = [SEPARADOR, f"{titulo} ({len(itens)})"]
    linhas.extend(explicacao)
    linhas.append("")

    if not itens:
        linhas.append("Nenhum arquivo.")
        linhas.append("")

    for item in itens:
        linhas.extend(linhas_do_arquivo(item))

    return linhas


def montar_relatorio(resumo, data_ref):
    sucesso = resumo.get("sucesso", [])
    ja_existe = resumo.get("ja_existe", [])
    pendentes = resumo.get("pendentes", [])
    fora_do_padrao = resumo.get("fora_do_padrao", [])

    linhas = [
        "RELATÓRIO DO ROBÔ CCTS REDE",
        "Cópia das Convenções Coletivas de Trabalho para as pastas das lojas na rede",
        f"Data de execução: {data_ref.strftime('%d/%m/%Y às %H:%M')}",
        "",
    ]

    if resumo.get("pasta"):
        linhas.append(f"Pasta analisada: {resumo['pasta']}")

    if resumo.get("destino"):
        linhas.append(f"Pasta de destino: {resumo['destino']}")

    linhas.append("")

    if resumo.get("erro_fatal"):
        linhas.append("ATENÇÃO: a execução não foi concluída.")
        linhas.append(f"Motivo: {str(resumo['erro_fatal']).splitlines()[0]}")
        linhas.append("")

    if not resumo.get("arquivos") and not resumo.get("erro_fatal"):
        linhas.append("Nenhum arquivo foi processado nesta execução.")
        linhas.append("")

    linhas.append(SEPARADOR)
    linhas.append("RESUMO")
    linhas.append(linha_com_pontos("Arquivos copiados", len(sucesso)))
    linhas.append(linha_com_pontos("Já estavam no destino", len(ja_existe)))
    linhas.append(linha_com_pontos("Pendentes", len(pendentes)))
    linhas.append(linha_com_pontos("Fora do padrão", len(fora_do_padrao)))
    linhas.append("")

    linhas.extend(linhas_da_secao(
        "ARQUIVOS COPIADOS",
        ["Copiados para todas as lojas correspondentes."],
        sucesso,
    ))
    linhas.extend(linhas_da_secao(
        "JÁ ESTAVAM NO DESTINO",
        ["O arquivo já existia em todas as lojas; nada foi copiado."],
        ja_existe,
    ))
    linhas.extend(linhas_da_secao(
        "PENDENTES",
        ["Houve falha para ao menos uma loja. O arquivo será tentado de novo na próxima execução."],
        pendentes,
    ))

    linhas.append(SEPARADOR)
    linhas.append(f"FORA DO PADRÃO ({len(fora_do_padrao)})")
    linhas.append("Não foram copiados. Renomeie seguindo o padrão")
    linhas.append("lojas_cidade_sindicato_vigência para que sejam copiados.")
    linhas.append("")

    if not fora_do_padrao:
        linhas.append("Nenhum arquivo.")

    for nome in fora_do_padrao:
        linhas.append(f"   - {nome}")

    return "\n".join(linhas)


FONTE = "font-family: Arial, sans-serif;"


def caixa_aviso(texto, cor_borda, cor_fundo):
    return f"""
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td bgcolor="{cor_fundo}" style="background-color: {cor_fundo}; border-left: 5px solid {cor_borda}; padding: 10px 14px; {FONTE} font-size: 14px; color: #333333;">{texto}</td>
        </tr>
      </table>"""


def linha_resumo(titulo, explicacao, numero, cor):
    return f"""
        <tr>
          <td style="padding: 10px 0; border-bottom: 1px solid #eeeeee; {FONTE}">
            <div style="font-size: 15px; font-weight: bold; color: #333333;">{titulo}</div>
            <div style="font-size: 13px; color: #666666;">{explicacao}</div>
          </td>
          <td width="60" align="right" style="padding: 10px 0; border-bottom: 1px solid #eeeeee; {FONTE} font-size: 22px; font-weight: bold; color: {cor};">{numero}</td>
        </tr>"""


def montar_corpo_html(resumo, data_ref):
    sucesso = len(resumo.get("sucesso", []))
    ja_existe = len(resumo.get("ja_existe", []))
    pendentes = len(resumo.get("pendentes", []))
    fora_do_padrao = len(resumo.get("fora_do_padrao", []))

    verde = "#1A412C"
    cinza = "#666666"
    laranja = "#D9730D"
    vermelho = "#C0392B"

    cor_pendentes = laranja if pendentes > 0 else cinza
    cor_fora_do_padrao = laranja if fora_do_padrao > 0 else cinza

    partes = []
    if resumo.get("pasta"):
        partes.append(f"<div>{html.escape(resumo['pasta'])}</div>")

    if resumo.get("destino"):
        partes.append(f"<div>{html.escape(resumo['destino'])} (destino)</div>")

    pastas_html = "".join(partes) or "<div>Pastas não informadas</div>"

    avisos_html = ""
    if resumo.get("erro_fatal"):
        motivo = str(resumo["erro_fatal"]).splitlines()[0]
        avisos_html += caixa_aviso(
            f"<b>ATENÇÃO:</b> a execução não foi concluída. Motivo: {html.escape(motivo)}",
            vermelho,
            "#FDECEA",
        )

    if not resumo.get("arquivos") and not resumo.get("erro_fatal"):
        avisos_html += caixa_aviso(
            "Não foram localizados arquivos para processamento nesta execução.",
            cinza,
            "#F2F2F2",
        )

    tabela = ""
    tabela += linha_resumo(
        "Arquivos copiados",
        "Documentos copiados com sucesso para todas as lojas correspondentes.",
        sucesso,
        verde,
    )
    tabela += linha_resumo(
        "Arquivos já existentes no destino",
        "Documentos que já constavam em todas as lojas; nenhuma cópia foi necessária.",
        ja_existe,
        cinza,
    )
    tabela += linha_resumo(
        "Arquivos pendentes",
        "Houve falha em ao menos uma loja; o arquivo será tentado de novo na próxima execução.",
        pendentes,
        cor_pendentes,
    )
    tabela += linha_resumo(
        "Arquivos fora do padrão de nomenclatura",
        "Documentos não copiados em razão do nome do arquivo.",
        fora_do_padrao,
        cor_fora_do_padrao,
    )

    if fora_do_padrao > 0:
        aviso = (
            "<b>ATENÇÃO:</b> foram identificados arquivos fora do padrão de nomenclatura. Revise a pasta para a renomeação.<br>"
            "Padrão: <b>lojas_cidade_sindicato_vigência</b>"
        )
        tabela += f'<tr><td colspan="2" style="padding: 8px 0;">{caixa_aviso(aviso, laranja, "#FFF4E5")}</td></tr>'

    return f"""
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width: 600px; max-width: 100%; border: 1px solid #dddddd;">
  <tr>
    <td bgcolor="{verde}" style="background-color: {verde}; padding: 18px 24px; {FONTE}">
      <div style="font-size: 20px; font-weight: bold; color: #ffffff;">Relatório do Robô CCTs Rede</div>
      <div style="font-size: 14px; color: #E3F1E8; padding-top: 6px;">Cópia das Convenções Coletivas de Trabalho para as pastas das lojas na rede</div>
      <div style="font-size: 14px; color: #E3F1E8;">{data_ref.strftime('%d/%m/%Y às %H:%M')}</div>
    </td>
  </tr>
  <tr>
    <td style="padding: 20px 24px; {FONTE} color: #333333;">
      <div style="font-size: 13px; color: #666666;">Pastas:</div>
      <div style="font-size: 13px; color: #333333;">{pastas_html}</div>
      <p style="margin: 16px 0 8px 0; font-size: 15px; color: #333333;">Olá,</p>
      <p style="margin: 0 0 12px 0; font-size: 15px; color: #333333;">Segue o resumo da execução. Os detalhes de cada arquivo estão no relatório em anexo.</p>
      {avisos_html}
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{tabela}
      </table>
      <p style="margin: 24px 0 0 0; font-size: 15px; color: #333333;">Att,<br>Robô CCTs Rede</p>
    </td>
  </tr>
</table>
"""


def enviar_relatorio(resumo, data_execucao=None, arquivo_log=None, arquivo_relatorio=None):
    try:
        remetente, senha, destinatarios = carregar_config_email()
    except (ValueError, FileNotFoundError, KeyError) as e:
        _log_erro_email(arquivo_log, f"[EMAIL] Erro ao carregar configuração: {e}")
        return False

    data_ref = data_execucao or datetime.now()
    assunto = f"Relatório Robô CCTs Rede - {data_ref.strftime('%d/%m/%Y')}"

    msg = MIMEMultipart()
    msg["From"] = remetente
    msg["To"] = ", ".join(destinatarios)
    msg["Subject"] = assunto
    msg.attach(MIMEText(montar_corpo_html(resumo, data_ref), "html", "utf-8"))

    if arquivo_relatorio and os.path.exists(arquivo_relatorio):
        try:
            with open(arquivo_relatorio, "rb") as arquivo:
                parte = MIMEBase("text", "plain")
                parte.set_payload(arquivo.read())
                encoders.encode_base64(parte)
                parte.add_header(
                    "Content-Disposition",
                    f"attachment; filename=\"{os.path.basename(arquivo_relatorio)}\"",
                )
                msg.attach(parte)
        except Exception as e:
            _log_erro_email(
                arquivo_log,
                f"[EMAIL] Erro ao anexar o relatório (email segue sem anexo): {e}",
            )

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=TIMEOUT_SMTP) as servidor:
            servidor.starttls()
            servidor.login(remetente, senha)
            servidor.sendmail(remetente, destinatarios, msg.as_string())

        print(f"[EMAIL] Email enviado com sucesso para {', '.join(destinatarios)}")
        return True

    except smtplib.SMTPAuthenticationError:
        _log_erro_email(
            arquivo_log,
            "[EMAIL] Erro de autenticação. Verifique o email e a senha de app no config.ini",
        )
        return False

    except Exception as e:
        _log_erro_email(arquivo_log, f"[EMAIL] Erro ao enviar email: {e}")
        return False
