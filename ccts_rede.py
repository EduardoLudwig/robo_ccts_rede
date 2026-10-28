import os
import re
import shutil
from datetime import datetime

import config_rede
import enviar_email

EXTENSOES_PERMITIDAS = (".pdf", ".doc", ".docx")
RE_MARCADOR_CONCLUIDO = re.compile(r"_(?:\[FEITO\]|\[JA_EXISTE\])$", re.IGNORECASE)
RE_MARCADOR_LIMPEZA = re.compile(r"_(?:\[FEITO\]|\[JA_EXISTE\]|\[FALHA_MANUAL\])$", re.IGNORECASE)
MAX_LOGS_TXT = 30

MESES_PT = {
    1: "JANEIRO",
    2: "FEVEREIRO",
    3: "MARÇO",
    4: "ABRIL",
    5: "MAIO",
    6: "JUNHO",
    7: "JULHO",
    8: "AGOSTO",
    9: "SETEMBRO",
    10: "OUTUBRO",
    11: "NOVEMBRO",
    12: "DEZEMBRO",
}


def log(message, log_file, espacamento=False):
    if espacamento:
        print("\n" + "-" * 80)
        log_file.write("\n" + "-" * 80 + "\n")

    print(message.strip())
    log_file.write(message + "\n")
    log_file.flush()


def _caminho_log_unico(pasta_logs, timestamp):
    nome = f"log_{timestamp}.txt"
    caminho = os.path.join(pasta_logs, nome)
    contador = 1

    while os.path.exists(caminho):
        nome = f"log_{timestamp}_{contador}.txt"
        caminho = os.path.join(pasta_logs, nome)
        contador += 1

    return caminho


def _renomear_log_legado(pasta_logs):
    legado = os.path.join(pasta_logs, "log_movimentacao.txt")

    if not os.path.exists(legado):
        return

    try:
        timestamp = datetime.fromtimestamp(os.path.getmtime(legado)).strftime(
            "%Y-%m-%d_%H-%M-%S"
        )
        os.rename(legado, _caminho_log_unico(pasta_logs, timestamp))
    except OSError as e:
        print(f"[AVISO] Não foi possível renomear o log antigo: {e}")


def gerar_caminho_log(settings):
    pasta_logs = settings["PastaLogs"]

    if not pasta_logs:
        raise ValueError("A pasta de logs (PastaLogs) não está configurada.")

    os.makedirs(pasta_logs, exist_ok=True)
    _renomear_log_legado(pasta_logs)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return _caminho_log_unico(pasta_logs, timestamp)


def limpar_logs_antigos(pasta_logs, log_atual):
    nome_atual = os.path.basename(log_atual)

    try:
        arquivos = sorted(
            nome
            for nome in os.listdir(pasta_logs)
            if nome != nome_atual
            and nome.lower().startswith("log_")
            and nome.lower().endswith(".txt")
            and os.path.isfile(os.path.join(pasta_logs, nome))
        )
    except OSError as e:
        print(f"[AVISO] Não foi possível listar os logs antigos: {e}")
        return

    while len(arquivos) > MAX_LOGS_TXT - 1:
        nome = arquivos.pop(0)
        try:
            os.remove(os.path.join(pasta_logs, nome))
        except OSError as e:
            print(f"[AVISO] Não foi possível remover o log antigo '{nome}': {e}")


def tem_marcador_concluido(nome_arquivo):
    nome_base, _ = os.path.splitext(nome_arquivo)
    return bool(RE_MARCADOR_CONCLUIDO.search(nome_base))


def remover_marcador(nome_arquivo):
    nome_base, extensao = os.path.splitext(nome_arquivo)
    return RE_MARCADOR_LIMPEZA.sub("", nome_base) + extensao


def extrair_numeros_loja(nome_arquivo):
    primeira_parte = nome_arquivo.split("_")[0]
    return re.findall(r"\b\d{1,3}\b", primeira_parte)


def extrair_dados_nome(nome_arquivo_limpo):
    nome_sem_extensao, extensao = os.path.splitext(nome_arquivo_limpo)
    match = re.search(r"_(\d{4}(?:-\d{4})?)(?:_(.*))?$", nome_sem_extensao)

    if not match:
        return None, "", extensao

    vigencia = match.group(1)
    complemento = (match.group(2) or "").strip().strip("_").strip()

    return vigencia, complemento, extensao


def nome_no_padrao(nome_arquivo):
    if not extrair_numeros_loja(nome_arquivo):
        return False

    vigencia, _, _ = extrair_dados_nome(nome_arquivo)
    return vigencia is not None


def indexar_lojas(destino_base):
    indice = {}

    if not os.path.isdir(destino_base):
        return indice

    for pasta in sorted(os.listdir(destino_base)):
        caminho = os.path.join(destino_base, pasta)

        if not os.path.isdir(caminho):
            continue

        match = re.match(r"^(\d{3})\s*-\s*", pasta)
        if match:
            indice.setdefault(int(match.group(1)), []).append(caminho)

    return indice


def coletar_arquivos(raiz, log_file):
    prioridades = {"raiz": 0, "reprocessar": 1, "sucesso": 2}
    pastas = (
        ("sucesso", os.path.join(raiz, "Sucesso")),
        ("reprocessar", os.path.join(raiz, "Reprocessar")),
        ("raiz", raiz),
    )

    candidatos = {}
    fora_do_padrao = []

    for origem, pasta in pastas:
        if not os.path.isdir(pasta):
            continue

        for nome in os.listdir(pasta):
            caminho = os.path.join(pasta, nome)

            if not os.path.isfile(caminho):
                continue

            _, extensao = os.path.splitext(nome)
            if extensao.lower() not in EXTENSOES_PERMITIDAS:
                log(
                    f"[IGNORADO] Arquivo {nome} não é um tipo de documento permitido "
                    f"(extensão: {extensao}).",
                    log_file,
                )
                continue

            if origem in ("raiz", "reprocessar") and tem_marcador_concluido(nome):
                log(f"[IGNORADO] '{nome}' já foi processado (marcador).", log_file)
                continue

            nome_limpo = remover_marcador(nome)

            if not nome_no_padrao(nome_limpo):
                if nome_limpo not in fora_do_padrao:
                    fora_do_padrao.append(nome_limpo)
                    log(
                        f"[IGNORADO] '{nome}' está fora do padrão de nome; "
                        "não será processado.",
                        log_file,
                    )
                continue

            try:
                tamanho = os.path.getsize(caminho)
            except OSError as e:
                log(f"[AVISO] Não foi possível ler '{caminho}': {e}", log_file)
                continue

            chave = f"{nome_limpo.lower()}|{tamanho}"
            existente = candidatos.get(chave)

            if existente and existente["prioridade"] >= prioridades[origem]:
                continue

            vigencia, complemento, _ = extrair_dados_nome(nome_limpo)

            candidatos[chave] = {
                "nome": nome,
                "nome_limpo": nome_limpo,
                "caminho": caminho,
                "origem": origem,
                "prioridade": prioridades[origem],
                "numeros": list(dict.fromkeys(extrair_numeros_loja(nome_limpo))),
                "vigencia": vigencia,
                "complemento": complemento,
            }

    return sorted(candidatos.values(), key=lambda item: item["nome_limpo"].lower()), fora_do_padrao


def copiar_arquivo(item, indice_lojas, log_file):
    nome_limpo = item["nome_limpo"]
    numeros_loja = item["numeros"]
    vigencia = item["vigencia"]
    complemento = item["complemento"]
    extensao = os.path.splitext(nome_limpo)[1]
    sufixo_complemento = f"_{complemento.upper()}" if complemento else ""

    log(f"\n[PROCESSANDO] {item['nome']}", log_file, espacamento=True)
    log(f"[ORIGEM]: {item['origem']}", log_file)
    log(f"[NÚMEROS ENCONTRADOS]: {', '.join(numeros_loja)}", log_file)
    log(f"[VIGÊNCIA ENCONTRADA]: {vigencia}", log_file)

    if complemento:
        log(f"[COMPLEMENTO ENCONTRADO]: {complemento}", log_file)

    lojas_resultado = {}
    destinos = []
    houve_falha = False
    houve_copia = False

    for numero in numeros_loja:
        numero_formatado = f"{int(numero):03d}"
        diretorios = indice_lojas.get(int(numero), [])

        if not diretorios:
            log(
                f"[ERRO] Nenhum diretório de destino encontrado para loja {numero} "
                f"(formatado como {numero_formatado}).",
                log_file,
            )
            lojas_resultado[numero_formatado] = "FALHA_SEM_PASTA"
            houve_falha = True
            continue

        novo_nome = f"VIG.{numero_formatado}_{vigencia}{sufixo_complemento}{extensao}"
        copiou_loja = False
        existente_loja = False
        falhou_loja = False

        for destino_dir in diretorios:
            destino_completo = os.path.join(destino_dir, novo_nome)

            if os.path.exists(destino_completo):
                log(f"     [JA_EXISTE] Já existia no destino: {destino_completo}", log_file)
                existente_loja = True
                destinos.append(destino_completo)
                continue

            try:
                shutil.copy2(item["caminho"], destino_completo)
                log(f"     [OK] Copiado para: {destino_completo}", log_file)
                copiou_loja = True
                destinos.append(destino_completo)
            except Exception as e:
                log(f"[ERRO] Falha ao copiar para {destino_completo}: {e}", log_file)
                falhou_loja = True

        if falhou_loja:
            lojas_resultado[numero_formatado] = "FALHA_COPIA"
            houve_falha = True
        elif copiou_loja:
            lojas_resultado[numero_formatado] = "SUCESSO"
            houve_copia = True
        elif existente_loja:
            lojas_resultado[numero_formatado] = "JA_EXISTE"
        else:
            lojas_resultado[numero_formatado] = "FALHA_COPIA"
            houve_falha = True

    if houve_falha:
        resultado = "PENDENTE"
        motivo = "Falha ao copiar para uma ou mais lojas"
    elif houve_copia:
        resultado = "SUCESSO"
        motivo = None
    else:
        resultado = "JA_EXISTE"
        motivo = None

    if resultado == "PENDENTE":
        log(
            f"[PENDENTE] '{nome_limpo}' será tentado novamente na próxima execução.",
            log_file,
        )
    else:
        log(f"[{resultado}] '{nome_limpo}' concluído.", log_file)

    return {
        "arquivo": nome_limpo,
        "origem": item["origem"],
        "resultado": resultado,
        "motivo": motivo,
        "lojas": lojas_resultado,
        "destinos": destinos,
    }


def _localizar_pasta_mes(pasta_ano, mes):
    if not os.path.isdir(pasta_ano):
        return None

    for nome in sorted(os.listdir(pasta_ano)):
        match = re.match(r"^(\d{1,2})(?:[_\s-]|$)", nome)
        if not match or int(match.group(1)) != mes:
            continue

        caminho = os.path.join(pasta_ano, nome)
        if os.path.isdir(caminho):
            return caminho

    return None


def descobrir_diretorios_automaticos(settings, data_ref=None):
    data_ref = data_ref or datetime.now()
    ano, mes = data_ref.year, data_ref.month

    if mes == 1:
        ano_anterior, mes_anterior = ano - 1, 12
    else:
        ano_anterior, mes_anterior = ano, mes - 1

    destinos = []
    for ano_alvo, mes_alvo in ((ano, mes), (ano_anterior, mes_anterior)):
        pasta_ano = os.path.join(
            settings["PastaBase"], f"Análises sindicatos lojas {ano_alvo}"
        )
        caminho = _localizar_pasta_mes(pasta_ano, mes_alvo)
        destinos.append(
            caminho
            or os.path.join(pasta_ano, f"{mes_alvo:02d}_{MESES_PT[mes_alvo]}")
        )

    return destinos


def _normalizar_diretorios(diretorio_ccts):
    if not diretorio_ccts:
        return []

    if isinstance(diretorio_ccts, (str, bytes, os.PathLike)):
        return [os.fspath(diretorio_ccts)]

    return [os.fspath(diretorio) for diretorio in diretorio_ccts]


def processar_arquivos(diretorio_ccts, destino_rede=None, log_path=None, settings=None):
    settings = settings or config_rede.carregar_settings()
    destino_rede = destino_rede or settings["PastaDestinoBase"]
    diretorios_entrada = _normalizar_diretorios(diretorio_ccts)

    if not log_path:
        log_path = gerar_caminho_log(settings)

    pasta_log = os.path.dirname(os.path.abspath(log_path))
    os.makedirs(pasta_log, exist_ok=True)

    data_execucao = datetime.now()
    resumo = {
        "pastas": [],
        "destino": destino_rede,
        "sucesso": [],
        "ja_existe": [],
        "pendentes": [],
        "arquivos": [],
        "fora_do_padrao": [],
    }

    with open(log_path, "w", encoding="utf-8") as log_file:
        limpar_logs_antigos(pasta_log, log_path)

        try:
            if not os.path.isdir(destino_rede):
                raise FileNotFoundError(f"Diretório de destino base não encontrado: {destino_rede}")

            log(
                f"\n=== LOG {data_execucao.strftime('%Y-%m-%d %H:%M')} ===\n",
                log_file,
                espacamento=True,
            )
            log(f"[DESTINO]: {destino_rede}", log_file)

            raizes = []
            vistos = set()

            for diretorio in diretorios_entrada:
                if not diretorio or not os.path.isdir(diretorio):
                    log(f"[AVISO] Diretório de origem não encontrado: {diretorio}", log_file)
                    continue

                raiz = os.path.abspath(diretorio.rstrip("\\/"))
                if os.path.basename(raiz).lower() in ("sucesso", "reprocessar"):
                    raiz = os.path.dirname(raiz)

                if raiz in vistos:
                    continue

                vistos.add(raiz)
                raizes.append(raiz)
                log(f"[PASTA ANALISADA]: {raiz}", log_file)

            if not raizes:
                raise FileNotFoundError("Nenhum diretório de origem válido foi encontrado.")

            resumo["pastas"] = raizes

            indice_lojas = indexar_lojas(destino_rede)
            if not indice_lojas:
                log(
                    f"[AVISO] Nenhuma pasta de loja foi encontrada em '{destino_rede}'.",
                    log_file,
                )

            for raiz in raizes:
                candidatos, fora_do_padrao = coletar_arquivos(raiz, log_file)

                for nome in fora_do_padrao:
                    if nome not in resumo["fora_do_padrao"]:
                        resumo["fora_do_padrao"].append(nome)

                log(f"[INFO] {len(candidatos)} arquivo(s) para avaliar em '{raiz}'.", log_file)

                for item in candidatos:
                    resultado = copiar_arquivo(item, indice_lojas, log_file)
                    resumo["arquivos"].append(resultado)

                    if resultado["resultado"] == "SUCESSO":
                        resumo["sucesso"].append(resultado)
                    elif resultado["resultado"] == "JA_EXISTE":
                        resumo["ja_existe"].append(resultado)
                    else:
                        resumo["pendentes"].append(resultado)

            log("=== RESUMO ===", log_file, espacamento=True)
            log(f"Arquivos copiados: {len(resumo['sucesso'])}", log_file)
            log(f"Arquivos já completos no destino: {len(resumo['ja_existe'])}", log_file)
            log(f"Arquivos pendentes: {len(resumo['pendentes'])}", log_file)
            log(f"Arquivos fora do padrão: {len(resumo['fora_do_padrao'])}", log_file)
            log("\n Processamento concluído!", log_file, espacamento=True)

        except Exception as e:
            resumo["erro_fatal"] = f"{type(e).__name__}: {e}"
            log(f"\n[ERRO FATAL]: {type(e).__name__}: {e}", log_file, espacamento=True)

    relatorio_path = os.path.join(pasta_log, "relatorio.txt")
    with open(relatorio_path, "w", encoding="utf-8") as arquivo_relatorio:
        arquivo_relatorio.write(enviar_email.montar_relatorio(resumo, data_execucao))

    enviar_email.enviar_relatorio(resumo, data_execucao, log_path, relatorio_path)

    if resumo.get("erro_fatal"):
        raise RuntimeError(resumo["erro_fatal"])

    return resumo
