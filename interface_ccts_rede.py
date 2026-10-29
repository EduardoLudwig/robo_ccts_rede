import os
import sys
import threading
from datetime import datetime
from tkinter import filedialog, messagebox

import customtkinter as ctk

import config_rede
from ccts_rede import (
    descobrir_diretorios_automaticos,
    gerar_caminho_log,
    limpar_logs_antigos,
    processar_arquivos,
)

AUTO_CLOSE_MS = 4000
APP_TITLE = "Robô CCTS Rede"

COR_AZUL = "#1F6F78"
COR_AZUL_HOVER = "#2A8A95"
COR_FUNDO = "#0F1A1C"
COR_CARD = "#152427"
COR_CARD_HOVER = "#1B3034"
COR_BORDA = "#2A4A4F"
COR_TEXTO = "#EAF4F3"
COR_TEXTO_SECUNDARIO = "#A8BCBE"
COR_SUCESSO = "#5FBF83"
COR_ERRO = "#E05A4F"
COR_NEUTRO = "#A8BCBE"


def resource_path(nome_arquivo):
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, nome_arquivo)


class App:
    def __init__(self, root, auto_start=False):
        self.root = root
        self.auto_start = auto_start
        self.settings = config_rede.carregar_settings()
        self.diretorio_ccts = None
        self.processando = False
        self.thread = None
        self.log_path = None
        self.historico_atividade = []

        self.root.title(APP_TITLE)
        self.root.geometry("960x660")
        self.root.minsize(860, 640)
        self.root.configure(fg_color=COR_FUNDO)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        try:
            self.root.iconbitmap(resource_path("icone_rede.ico"))
        except Exception:
            pass

        self._montar_layout()
        self._configurar_estado_inicial()
        self.root.after(50, self._centralizar)

    def _montar_layout(self):
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.container = ctk.CTkFrame(self.root, fg_color="transparent")
        self.container.grid(row=0, column=0, sticky="nsew", padx=30, pady=26)
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(3, weight=1)

        self._montar_cabecalho()
        self._montar_card_origem()
        self._montar_card_status()
        self._montar_card_atividade()
        self._montar_rodape()

    def _montar_cabecalho(self):
        self.header = ctk.CTkFrame(self.container, fg_color="transparent")
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.grid_columnconfigure(0, weight=1)

        self.label_titulo = ctk.CTkLabel(
            self.header,
            text=APP_TITLE,
            font=("Segoe UI", 24, "bold"),
            text_color=COR_TEXTO,
            anchor="w",
        )
        self.label_titulo.grid(row=0, column=0, sticky="w")

        self.botao_ajuda = ctk.CTkButton(
            self.header,
            text="Como usar",
            width=104,
            height=34,
            fg_color="transparent",
            hover_color=COR_CARD_HOVER,
            text_color=COR_TEXTO_SECUNDARIO,
            font=("Segoe UI", 12, "bold"),
            command=self.mostrar_guia,
        )
        self.botao_ajuda.grid(row=0, column=1, sticky="e")

    def _montar_card_origem(self):
        self.card_origem = ctk.CTkFrame(self.container, fg_color="transparent")
        self.card_origem.grid(row=1, column=0, sticky="ew", pady=(24, 20))
        self.card_origem.grid_columnconfigure(0, weight=1)

        self.label_origem = ctk.CTkLabel(
            self.card_origem,
            text="ORIGEM DOS DOCUMENTOS",
            font=("Segoe UI", 11, "bold"),
            text_color=COR_TEXTO_SECUNDARIO,
            anchor="w",
        )
        self.label_origem.grid(row=0, column=0, columnspan=2, sticky="w", padx=0)

        self.label_origem_desc = ctk.CTkLabel(
            self.card_origem,
            text="Selecione a pasta que contém os arquivos que serão distribuídos.",
            font=("Segoe UI", 13),
            text_color=COR_TEXTO,
            anchor="w",
        )
        self.label_origem_desc.grid(row=1, column=0, columnspan=2, sticky="w", padx=0, pady=(4, 0))

        self.path_frame = ctk.CTkFrame(
            self.card_origem,
            fg_color=COR_FUNDO,
            border_width=1,
            border_color=COR_BORDA,
            corner_radius=8,
        )
        self.path_frame.grid(row=2, column=0, sticky="ew", padx=(0, 12), pady=(12, 0))
        self.path_frame.grid_columnconfigure(0, weight=1)

        self.label_caminho = ctk.CTkLabel(
            self.path_frame,
            text="Nenhuma pasta selecionada",
            font=("Segoe UI", 13),
            text_color=COR_TEXTO_SECUNDARIO,
            anchor="w",
            justify="left",
            wraplength=520,
        )
        self.label_caminho.grid(row=0, column=0, sticky="ew", padx=14, pady=12)

        self.botao_caminho = ctk.CTkButton(
            self.card_origem,
            text="Selecionar pasta",
            width=158,
            height=34,
            fg_color=COR_CARD_HOVER,
            hover_color=COR_BORDA,
            border_width=1,
            border_color=COR_AZUL,
            text_color=COR_TEXTO,
            font=("Segoe UI", 12, "bold"),
            command=self.selecionar_diretorio,
        )
        self.botao_caminho.grid(row=2, column=1, sticky="e", pady=(12, 0))

    def _montar_card_status(self):
        self.card_status = ctk.CTkFrame(self.container, fg_color="transparent")
        self.card_status.grid(row=2, column=0, sticky="ew", pady=(0, 20))
        self.card_status.grid_columnconfigure(0, weight=1)

        self.label_status_titulo = ctk.CTkLabel(
            self.card_status,
            text="STATUS DA EXECUÇÃO",
            font=("Segoe UI", 11, "bold"),
            text_color=COR_TEXTO_SECUNDARIO,
            anchor="w",
        )
        self.label_status_titulo.grid(row=0, column=0, sticky="w", padx=0)

        self.status_line = ctk.CTkFrame(self.card_status, fg_color="transparent")
        self.status_line.grid(row=1, column=0, sticky="ew", padx=0, pady=(6, 0))
        self.status_line.grid_columnconfigure(1, weight=1)

        self.status_dot = ctk.CTkLabel(
            self.status_line,
            text="●",
            width=18,
            font=("Segoe UI", 18),
            text_color=COR_NEUTRO,
        )
        self.status_dot.grid(row=0, column=0, sticky="w", padx=(0, 8))

        self.label_status = ctk.CTkLabel(
            self.status_line,
            text="Selecione a pasta de origem para começar",
            font=("Segoe UI", 15, "bold"),
            text_color=COR_TEXTO,
            anchor="w",
        )
        self.label_status.grid(row=0, column=1, sticky="w")

        self.label_detalhe = ctk.CTkLabel(
            self.card_status,
            text="",
            font=("Segoe UI", 12),
            text_color=COR_TEXTO_SECUNDARIO,
            anchor="w",
            justify="left",
            wraplength=760,
        )
        self.label_detalhe.grid(row=2, column=0, sticky="w", padx=0, pady=(2, 0))

        self.progress = ctk.CTkProgressBar(
            self.card_status,
            height=6,
            corner_radius=3,
            mode="indeterminate",
            fg_color=COR_BORDA,
            progress_color=COR_AZUL,
            border_width=0,
        )
        self.progress.grid(row=3, column=0, sticky="ew", padx=0, pady=(10, 0))
        self.progress.grid_remove()

        self.actions = ctk.CTkFrame(self.card_status, fg_color="transparent")
        self.actions.grid(row=4, column=0, sticky="ew", padx=0, pady=(14, 0))
        self.actions.grid_columnconfigure(0, weight=0)
        self.actions.grid_columnconfigure(1, weight=0)
        self.actions.grid_columnconfigure(2, weight=1)

        self.botao_inicia = ctk.CTkButton(
            self.actions,
            text="Iniciar processamento",
            width=210,
            height=38,
            fg_color=COR_AZUL,
            hover_color=COR_AZUL_HOVER,
            text_color="#FFFFFF",
            font=("Segoe UI", 13, "bold"),
            corner_radius=8,
            command=self.iniciar_processo,
        )
        self.botao_inicia.grid(row=0, column=0, sticky="w")

        self.botao_logs = ctk.CTkButton(
            self.actions,
            text="Abrir logs",
            width=132,
            height=38,
            fg_color="transparent",
            hover_color=COR_CARD_HOVER,
            border_width=1,
            border_color=COR_BORDA,
            text_color=COR_TEXTO,
            font=("Segoe UI", 12, "bold"),
            corner_radius=8,
            command=self.abrir_logs,
        )
        self.botao_logs.grid(row=0, column=1, sticky="w", padx=(10, 0))

    def _montar_card_atividade(self):
        self.card_atividade = ctk.CTkFrame(self.container, fg_color="transparent")
        self.card_atividade.grid(row=3, column=0, sticky="nsew", pady=(0, 8))
        self.card_atividade.grid_columnconfigure(0, weight=1)
        self.card_atividade.grid_rowconfigure(4, weight=1)

        self.label_atividade_titulo = ctk.CTkLabel(
            self.card_atividade,
            text="ATIVIDADE",
            height=16,
            font=("Segoe UI", 11, "bold"),
            text_color=COR_TEXTO_SECUNDARIO,
            anchor="w",
        )
        self.label_atividade_titulo.grid(row=0, column=0, sticky="w", padx=0)

        self.label_loja_atual = ctk.CTkLabel(
            self.card_atividade,
            text="Aguardando início",
            height=26,
            font=("Segoe UI", 17, "bold"),
            text_color=COR_TEXTO,
            anchor="w",
            justify="left",
            wraplength=800,
        )
        self.label_loja_atual.grid(row=1, column=0, sticky="ew", padx=0, pady=(4, 0))

        self.label_detalhe_atividade = ctk.CTkLabel(
            self.card_atividade,
            text="",
            height=18,
            font=("Segoe UI", 11),
            text_color=COR_TEXTO_SECUNDARIO,
            anchor="w",
            justify="left",
            wraplength=800,
        )
        self.label_detalhe_atividade.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=0,
            pady=(2, 8),
        )

        self.label_historico_titulo = ctk.CTkLabel(
            self.card_atividade,
            text="ÚLTIMAS AÇÕES",
            height=14,
            font=("Segoe UI", 9, "bold"),
            text_color=COR_TEXTO_SECUNDARIO,
            anchor="w",
        )
        self.label_historico_titulo.grid(
            row=3,
            column=0,
            sticky="w",
            padx=0,
            pady=(0, 3),
        )

        self.historico_box = ctk.CTkTextbox(
            self.card_atividade,
            height=54,
            fg_color=COR_FUNDO,
            border_width=1,
            border_color=COR_BORDA,
            corner_radius=6,
            text_color=COR_TEXTO_SECUNDARIO,
            font=("Segoe UI", 10),
            activate_scrollbars=False,
        )
        self.historico_box.grid(
            row=4,
            column=0,
            sticky="nsew",
            padx=0,
        )
        self.historico_box.insert("1.0", "Aguardando o início da execução.")
        self.historico_box.configure(state="disabled")

    def _montar_rodape(self):
        self.footer = ctk.CTkFrame(self.container, fg_color="transparent")
        self.footer.grid(row=4, column=0, sticky="ew", pady=(12, 0))
        self.footer.grid_columnconfigure(0, weight=1)

        self.label_destino = ctk.CTkLabel(
            self.footer,
            text=f"Destino: {self.settings['PastaDestinoBase']}",
            font=("Segoe UI", 11),
            text_color=COR_TEXTO_SECUNDARIO,
            anchor="w",
            justify="left",
            wraplength=860,
        )
        self.label_destino.grid(row=0, column=0, sticky="ew")

    def _configurar_estado_inicial(self):
        if self.auto_start:
            self.label_caminho.configure(
                text="Meses atual e anterior",
                text_color=COR_TEXTO_SECUNDARIO,
            )
            self.botao_caminho.configure(state="disabled")
            self.botao_inicia.configure(state="disabled")
            self.botao_logs.configure(state="disabled")
            self._definir_status(
                "Execução automática",
                COR_AZUL,
                "Preparando processamento dos meses atual e anterior.",
            )
            self.label_atividade_titulo.configure(text="EM EXECUÇÃO")
            self._definir_atividade(
                "Preparando execução automática",
                "Localizando os documentos dos meses atual e anterior.",
            )
        else:
            self._definir_status(
                "Selecione a pasta de origem para começar",
                COR_NEUTRO,
                "",
            )
            self.label_atividade_titulo.configure(text="ATIVIDADE")
            self._definir_atividade(
                "Aguardando início",
                "",
            )
            self._atualizar_botao_iniciar()

    def _centralizar(self):
        largura = self.root.winfo_width()
        altura = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (largura // 3)
        y = (self.root.winfo_screenheight() // 2) - (altura // 2)
        self.root.geometry(f"+{x}+{y}")

    def _definir_status(self, titulo, cor, detalhe):
        self.status_dot.configure(text_color=cor)
        self.label_status.configure(text=titulo)
        self.label_detalhe.configure(text=detalhe)
        if detalhe:
            self.label_detalhe.grid()
        else:
            self.label_detalhe.grid_remove()

    def _definir_atividade(self, loja, detalhe):
        self.label_loja_atual.configure(text=loja or "—")
        self.label_detalhe_atividade.configure(text=detalhe or "")

    def _limpar_historico(self):
        self.historico_atividade = []
        self.historico_box.configure(state="normal")
        self.historico_box.delete("1.0", "end")
        self.historico_box.configure(state="disabled")

    def _registrar_historico(self, texto):
        self.historico_atividade.append(
            f"{datetime.now().strftime('%H:%M:%S')}  {texto}"
        )
        self.historico_atividade = self.historico_atividade[-4:]
        self.historico_box.configure(state="normal")
        self.historico_box.delete("1.0", "end")
        self.historico_box.insert("1.0", "\n".join(self.historico_atividade))
        self.historico_box.configure(state="disabled")

    def _atualizar_botao_iniciar(self):
        if self.processando or not self.diretorio_ccts:
            self.botao_inicia.configure(state="disabled")
        else:
            self.botao_inicia.configure(state="normal")

    def _set_processing_state(self, ativo):
        self.processando = ativo
        estado = "disabled" if ativo else "normal"
        self.botao_caminho.configure(state=estado)
        self.botao_inicia.configure(
            state=estado,
            text="Processando..." if ativo else "Iniciar processamento",
        )
        self.botao_logs.configure(state=estado)

        if ativo:
            self.progress.grid()
            self.progress.start()
        else:
            self._atualizar_botao_iniciar()

    def selecionar_diretorio(self):
        pasta = filedialog.askdirectory(title="Selecione a pasta de origem")
        if not pasta:
            return

        self.diretorio_ccts = os.path.normpath(pasta)
        self.label_caminho.configure(text=self.diretorio_ccts, text_color=COR_TEXTO)
        self._definir_status(
            "Pasta de origem selecionada",
            COR_NEUTRO,
            "",
        )
        self._atualizar_botao_iniciar()

    def iniciar_processo(self):
        if self.processando:
            return

        if not self.diretorio_ccts:
            messagebox.showwarning(
                "Pasta de origem",
                "Selecione a pasta de origem antes de iniciar.",
            )
            return

        self._iniciar_processamento([self.diretorio_ccts])

    def iniciar_processo_automatico(self):
        if self.processando:
            return

        self._definir_status(
            "Execução automática",
            COR_AZUL,
            "Localizando documentos dos meses atual e anterior.",
        )

        try:
            diretorios = descobrir_diretorios_automaticos(self.settings)
        except Exception as erro:
            self._finalizar_processamento(None, str(erro))
            return

        self._iniciar_processamento(diretorios)

    def _iniciar_processamento(self, diretorios):
        if self.processando:
            return

        self._set_processing_state(True)
        self._definir_status(
            "Processando...",
            COR_AZUL,
            "Copiando documentos e preparando o relatório.",
        )
        self.label_atividade_titulo.configure(text="EM EXECUÇÃO")
        self._definir_atividade(
            "Preparando...",
            "Lendo os documentos de origem e indexando as lojas.",
        )
        self._limpar_historico()
        self._registrar_historico("Execução iniciada.")

        def executar():
            log_path = None
            erro = None
            try:
                log_path = gerar_caminho_log(self.settings)
                processar_arquivos(
                    diretorios,
                    self.settings["PastaDestinoBase"],
                    log_path,
                    self.settings,
                    progresso_callback=self._receber_progresso,
                )
            except Exception as exc:
                erro = str(exc)

            self.root.after(0, self._finalizar_processamento, log_path, erro)

        self.thread = threading.Thread(target=executar, daemon=True)
        self.thread.start()

    def _receber_progresso(self, dados):
        self.root.after(0, self._atualizar_atividade, dados)

    def _atualizar_atividade(self, dados):
        etapa = dados.get("etapa")

        if etapa == "inicio":
            total = dados.get("total_pastas", 0)
            self._definir_atividade(
                "Pastas localizadas",
                f"{total} pasta(s) de origem serão avaliadas.",
            )
            self._registrar_historico("Análise das pastas iniciada.")
        elif etapa == "indexando":
            self._definir_atividade(
                "Preparando destino",
                "Lendo a estrutura de lojas do destino.",
            )
            self._registrar_historico("Indexando lojas no destino.")
        elif etapa == "raiz":
            total = dados.get("total_arquivos", 0)
            raiz = dados.get("raiz", "")
            self._definir_atividade(
                "Analisando origem",
                f"{total} arquivo(s) em {raiz}",
            )
            self._registrar_historico(f"Analisando {os.path.basename(raiz)}.")
        elif etapa == "arquivo":
            arquivo = dados.get("arquivo", "")
            total = dados.get("total_lojas", 0)
            self._definir_atividade(
                "Avaliando arquivo",
                f"{arquivo} — {total} destino(s) de loja",
            )
            self._registrar_historico(f"Avaliando {arquivo}.")
        elif etapa == "loja":
            loja = dados.get("loja", "")
            arquivo = dados.get("arquivo", "")
            indice = dados.get("indice_loja", 0)
            total = dados.get("total_lojas", 0)
            origem = dados.get("origem", "")

            partes = [arquivo] if arquivo else []
            if indice and total:
                partes.append(f"Loja {indice} de {total}")
            if origem:
                partes.append(f"Origem: {origem}")

            self._definir_atividade(
                loja,
                " | ".join(partes) or "Loja em processamento.",
            )
            self._registrar_historico(f"Percorrendo {loja}.")
        elif etapa == "loja_sem_destino":
            loja = dados.get("loja", "")
            arquivo = dados.get("arquivo", "")
            self._definir_atividade(
                f"Código {loja}",
                f"{arquivo} | Nenhuma pasta de destino encontrada.",
            )
            self._registrar_historico(f"Sem pasta para a loja {loja}.")
        elif etapa == "arquivo_finalizado":
            arquivo = dados.get("arquivo", "")
            resultado = dados.get("resultado", "")
            motivo = dados.get("motivo") or ""
            detalhe = f"{arquivo} | Resultado: {resultado}"
            if motivo:
                detalhe += f" | {motivo}"
            self._definir_atividade("Arquivo concluído", detalhe)
            self._registrar_historico(f"{arquivo}: {resultado}.")
        elif etapa in ("relatorio", "email"):
            mensagem = dados.get("mensagem", "Finalizando a execução.")
            self._definir_atividade("Finalizando execução", mensagem)
            self._registrar_historico(mensagem)

    def _finalizar_processamento(self, log_path, erro):
        self.processando = False
        try:
            self.progress.stop()
        except Exception:
            pass
        self.progress.grid_remove()
        self.label_atividade_titulo.configure(text="ÚLTIMA ATIVIDADE")
        self._registrar_historico(
            "Execução interrompida." if erro else "Execução concluída."
        )

        if erro:
            if log_path:
                detalhe = f"{erro}. Log: {log_path}"
                try:
                    with open(log_path, "a", encoding="utf-8") as log_handle:
                        log_handle.write(f"\n[ERRO FATAL NA APLICACAO] {erro}\n")
                    limpar_logs_antigos(os.path.dirname(log_path), log_path)
                except Exception:
                    pass
            else:
                detalhe = f"{erro}. Consulte o log para mais detalhes."

            self._definir_status("Erro ao processar", COR_ERRO, detalhe)
        else:
            self.log_path = log_path
            detalhe = f"Log: {log_path}" if log_path else "Processamento concluído."
            self._definir_status("Execução concluída", COR_SUCESSO, detalhe)

        if self.auto_start:
            self.root.after(AUTO_CLOSE_MS, self.root.destroy)
        else:
            self._set_processing_state(False)

    def abrir_logs(self):
        pasta = self.settings["PastaLogs"]
        try:
            os.makedirs(pasta, exist_ok=True)
            os.startfile(pasta)
        except Exception as erro:
            messagebox.showerror(
                "Abrir logs",
                f"Não foi possível abrir a pasta de logs.\n\n{erro}",
            )

    def mostrar_guia(self):
        janela = ctk.CTkToplevel(self.root)
        janela.title("Como usar")
        janela.geometry("680x480")
        janela.minsize(560, 400)
        janela.configure(fg_color=COR_FUNDO)
        janela.transient(self.root)
        janela.grid_rowconfigure(1, weight=1)
        janela.grid_columnconfigure(0, weight=1)

        titulo = ctk.CTkLabel(
            janela,
            text="Como usar o robô",
            font=("Segoe UI", 19, "bold"),
            text_color=COR_TEXTO,
            anchor="w",
        )
        titulo.grid(row=0, column=0, sticky="w", padx=24, pady=(20, 10))

        texto = ctk.CTkTextbox(
            janela,
            fg_color=COR_CARD,
            border_width=1,
            border_color=COR_BORDA,
            text_color=COR_TEXTO,
            font=("Segoe UI", 13),
            corner_radius=10,
        )
        texto.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 14))
        texto.insert(
            "1.0",
            "Os documentos da pasta selecionada devem seguir o seguinte padrão de nomenclatura:\n\n"
            "- Número das lojas_cidade_código do sindicato_vigência\n\n"
            "Exemplos:\n"
            "- 160,310_LAJEADO_SIND0088_2026\n"
            "- 642,285,187,259_VIAMAO_SIND0173_2024-2026\n\n"
            "Observações:\n"
            "- Se necessário, pode-se adicionar complementos após a vigência, como: "
            "_ADITIVOS, _FERIADOS, _TRABALHO NO DIA X, etc.\n\n"
            "  Exemplo:\n"
            "- 127,139,140,155_LAJEADO_SIND0077_2025-2027_ADITIVOS\n"
            "- 503,631,659,671_UMUARAMA_SIND0180_2025-2027_TRABALHO NO DIA 19.04.2025",
        )
        texto.configure(state="disabled")

        botao_fechar = ctk.CTkButton(
            janela,
            text="Fechar",
            width=112,
            height=38,
            fg_color=COR_AZUL,
            hover_color=COR_AZUL_HOVER,
            text_color="#FFFFFF",
            font=("Segoe UI", 12, "bold"),
            corner_radius=8,
            command=janela.destroy,
        )
        botao_fechar.grid(row=2, column=0, sticky="e", padx=24, pady=(0, 20))

        janela.grab_set()
        janela.after(60, janela.lift)

    def on_closing(self):
        if self.processando:
            messagebox.showwarning(
                "Processamento em andamento",
                "Aguarde a execução terminar antes de fechar.",
            )
            return
        self.root.destroy()


def main():
    auto_start = "--auto-start" in sys.argv

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme(resource_path("marsh.json"))

    root = ctk.CTk()
    app = App(root, auto_start=auto_start)

    if auto_start:
        root.after(300, app.iniciar_processo_automatico)

    root.mainloop()


if __name__ == "__main__":
    main()
