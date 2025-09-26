import os
import shutil
import re
from datetime import datetime

def extrair_numeros_loja(numero_arquivo):
    numero_limpo = numero_arquivo.split("_")[0]
    
    return re.findall(r'\b\d{1,3}\b', numero_limpo)

def encontrar_diretorios(destino_base, numero_loja):
    diretorios_encontrados = []
    numero_loja_formatado = f"{int(numero_loja):03d}" 

    padrao_loja = re.compile(rf'^{numero_loja_formatado}\s*-\s*', re.IGNORECASE)

    if not os.path.exists(destino_base):
        print(f"[ERRO] Diretório de destino base não encontrado: {destino_base}")
        return []

    for pasta in os.listdir(destino_base):
        caminho_completo = os.path.join(destino_base, pasta)

        if os.path.isdir(caminho_completo) and padrao_loja.match(pasta):  
            diretorios_encontrados.append(caminho_completo)
    return diretorios_encontrados

def log(message, log_file, espacamento=False):
    if espacamento:
        print("\n" + "-" * 80)
        log_file.write("\n" + "-" * 80 + "\n")

    print(message.strip())
    log_file.write(message + "\n")

def copiar_arquivo(origem, destino_base, nome_arquivo, log_file):
    numeros_loja = extrair_numeros_loja(nome_arquivo)

    if not numeros_loja:
        log(f"[ERRO] Nenhum número de loja encontrado em: {nome_arquivo}\n", log_file, espacamento=True)
        return

    log(f"\n[PROCESSANDO] {nome_arquivo}", log_file, espacamento=True)
    log(f"", log_file)
    log(f"[NÚMEROS ENCONTRADOS]: {', '.join(numeros_loja)}", log_file)

    origem_completa = os.path.join(origem, nome_arquivo)

    match_dados = re.search(r'_(\d{4}(?:-\d{4})?)_?(.*?)(\.pdf|\.doc|\.docx)$', nome_arquivo, re.IGNORECASE)

    vigencia = ""
    sufixo_extra = ""
    extensao = os.path.splitext(nome_arquivo)[1]

    if match_dados:
        vigencia = match_dados.group(1)
        raw_sufixo = match_dados.group(2)
        if raw_sufixo:
            sufixo_extra = "_" + raw_sufixo.upper()

        log(f"[VIGÊNCIA ENCONTRADA]: {vigencia}", log_file)

    else:

        log(f"[ATENÇÃO] Período de vigência ou formato inesperado no nome: {nome_arquivo}. Arquivo será pulado.", log_file)
        return
    
    sucesso = False 
    for numero in numeros_loja:
        diretorios = encontrar_diretorios(destino_base, numero)
        
        if diretorios:
            
            numero_formatado_para_nome = f"{int(numero):03d}"

            for destino_dir in diretorios:
                novo_nome = f"VIG.{numero_formatado_para_nome}_{vigencia}{sufixo_extra}{extensao}"
                destino_completo = os.path.join(destino_dir, novo_nome)

                try:
                    shutil.copy2(origem_completa, destino_completo)
                    log(f"     [OK] Copiado para: {destino_completo}", log_file)
                    sucesso = True
                except Exception as e:
                    log(f"[ERRO] Falha ao copiar para {destino_completo}: {str(e)}", log_file)
        else:
            log(f"[ERRO] Nenhum diretório de destino encontrado para loja {numero} (formatado como {f'{int(numero):03d}'}).", log_file)

    if not sucesso:
         log(f"[FALHA] O arquivo {nome_arquivo} não pôde ser copiado para nenhum diretório correspondente ou não atendeu aos critérios de renomeação.\n", log_file)

def processar_arquivos(diretorio_ccts, destino_rede, log_path):
    
    if os.path.exists(log_path):
        os.remove(log_path)

    extensoes_permitidas = ['.pdf', '.doc', '.docx'] 

    with open(log_path, 'w', encoding='utf-8') as log_file:
        log(f"\n=== LOG {datetime.now().strftime('%Y-%m-%d %H:%M')} ===\n", log_file, espacamento=True)
        
        if not os.path.exists(diretorio_ccts):
            log(f"[ERRO] Diretório de origem não encontrado: {diretorio_ccts}", log_file, espacamento=True)
            log_file.close() 
            return

        for arquivo in os.listdir(diretorio_ccts):
            caminho_completo_arquivo = os.path.join(diretorio_ccts, arquivo)
            if os.path.isfile(caminho_completo_arquivo):
                _, extensao = os.path.splitext(arquivo) 
                if extensao.lower() in extensoes_permitidas: 
                    copiar_arquivo(diretorio_ccts, destino_rede, arquivo, log_file)
                else:
                    log(f"[IGNORADO] Arquivo {arquivo} não é um tipo de documento permitido (extensão: {extensao}).", log_file)

        log("\n Processamento concluído!", log_file, espacamento=True)