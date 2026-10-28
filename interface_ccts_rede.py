import customtkinter as ctk
from tkinter import filedialog, messagebox
import sys
import os

import config_rede
from ccts_rede import (
    descobrir_diretorios_automaticos,
    gerar_caminho_log,
    limpar_logs_antigos,
    processar_arquivos,
)

AUTO_CLOSE_MS = 4000


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

theme_path = resource_path("marsh.json")

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme(theme_path)

class App:
    def __init__(self, root, auto_start=False):
        self.root = root
        self.auto_start = auto_start
        self.diretorio_ccts = None
        self.settings = config_rede.carregar_settings()
        self.root.title("Robô CCTS para rede")
        self.root.geometry("1000x400")

        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=1)

        self.mainframe = ctk.CTkFrame(root)
        self.mainframe.grid(row=0, column=0, padx=(5,5), pady=(12,12), sticky="nsew")

        for i in range(4):
            self.mainframe.grid_columnconfigure(i, weight=1)

        for j in range(4):
            self.mainframe.grid_rowconfigure(j, weight=1)

        self.label = ctk.CTkLabel(
            self.mainframe,
            text="Escolha a pasta com os documentos. Eles serão renomeados e copiados automaticamente.",
            font=("Inter", 14, "bold"),
            fg_color="#397F5A",
            corner_radius=15
        )
        self.label.grid(row=0, column=0, columnspan=4, sticky="n", padx=15, pady=(20,0))

        self.botao_caminho = ctk.CTkButton(
            self.mainframe,
            text="Selecionar o caminho",
            text_color="white",
            font=("Inter", 12, "bold"),
            width=130,   
            height=30,   
            command=self.seleciona_diretorio_ccts 
        )
        self.botao_caminho.grid(row=1, column=1, sticky="w", padx=5, pady=(0,5))

        self.botao_inicia = ctk.CTkButton(
            self.mainframe,
            text="Iniciar o processo",
            text_color="white",
            font=("Inter", 12, "bold"),
            width=130,   
            height=30,    
            command=self.iniciar_processo
        )
        self.botao_inicia.grid(row=1, column=2, sticky="e", padx=5, pady=(0,5))

        self.botao_ajuda = ctk.CTkButton(
            self.mainframe,
            text="Ajuda",
            text_color="white",
            font=("Inter", 12, "bold"),
            width=130,   
            height=30,    
            command=self.mostra_guia
        )
        self.botao_ajuda.grid(row=4, columnspan=4, sticky="s", padx=20, pady=(15))

        self.label_status = ctk.CTkLabel(
            self.mainframe,
            text="",
            font=("arial", 14, "bold"),
            fg_color="#333333",
            corner_radius=10,
            wraplength=700
        )
        self.label_status.grid(row=3, column=1, columnspan=2, sticky="ew", padx=15, pady=(10, 5))

    def seleciona_diretorio_ccts(self):
        arquivos = filedialog.askopenfilenames(title="Selecione um arquivo na pasta desejada")
        if arquivos:
            self.diretorio_ccts = os.path.dirname(arquivos[0])
            self.label_status.configure(text=f"PASTA SELECIONADA: {self.diretorio_ccts}")
        else:
            messagebox.showwarning("Aviso", "Nenhum arquivo selecionado.")

    def iniciar_processo(self):
        if self.diretorio_ccts is None:
            messagebox.showwarning("Aviso", "Por favor, selecione um arquivo da pasta dos CCTs antes de iniciar.")
            return

        self._processar([self.diretorio_ccts])

    def iniciar_processo_automatico(self):
        diretorios = descobrir_diretorios_automaticos(self.settings)
        self._processar(diretorios)

    def _processar(self, diretorios):
        log_path = None

        try:
            self.label_status.configure(text="Processando...")
            self.root.update_idletasks()

            log_path = gerar_caminho_log(self.settings)

            processar_arquivos(
                diretorios,
                self.settings["PastaDestinoBase"],
                log_path,
                self.settings,
            )
            self.label_status.configure(text=f"Processo concluído! Log gerado em: {log_path}")
        except Exception as e:
            self.label_status.configure(text=f"Erro durante o processo: {e}")

            if log_path:
                try:
                    with open(log_path, 'a', encoding='utf-8') as f:
                        f.write(f"\n[ERRO FATAL NA APLICAÇÃO]: {e}\n")
                    limpar_logs_antigos(os.path.dirname(os.path.abspath(log_path)), log_path)
                except Exception as log_e:
                    print(f"Não foi possível gravar o erro no log: {log_e}")

            if not self.auto_start:
                messagebox.showerror("Erro", f"Ocorreu um erro durante o processamento: {e}. Verifique o log para mais detalhes.")
        finally:
            if self.auto_start:
                self.root.after(AUTO_CLOSE_MS, self.root.destroy)

    def mostra_guia(self):
        guia = (
            "Os documentos da pasta selecionada devem seguir o seguinte padrão de nomenclatura:\n\n"
            "- Número das lojas_cidade_código do sindicato_vigência\n\n"
            "Exemplos:\n"
            "- 160,310_LAJEADO_SIND0088_2026\n"
            "- 642,285,187,259_VIAMAO_SIND0173_2024-2026\n\n"
            "Observações:\n"
            "- Se necessário, pode-se adicionar complementos após a vigência, como: _ADITIVOS, _FERIADOS, _TRABALHO NO DIA X, etc.\n\n"
            "  Exemplo:\n"
            "- 127,139,140,155_LAJEADO_SIND0077_2025-2027_ADITIVOS\n"
            "- 503,631,659,671_UMUARAMA_SIND0180_2025-2027_TRABALHO NO DIA 19.04.2025"
        )
        messagebox.showinfo("Padrão necessário", guia)

if __name__ == "__main__":
    auto_start = "--auto-start" in sys.argv

    root = ctk.CTk()
    app = App(root, auto_start=auto_start)

    if auto_start:
        root.after(200, app.iniciar_processo_automatico)

    root.mainloop()