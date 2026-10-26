import configparser
import os

APP_CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".RoboRede")
CONFIG_FILE = os.path.join(APP_CONFIG_DIR, "config.ini")

DEFAULTS = {
    "PastaBase": r"M:\Remuneração e Benefícios\SINDICAIS",
    "PastaDestinoBase": r"M:\Remuneração e Benefícios\SINDICAIS\CONVENÇÕES_COLETIVAS",
    "PastaLogs": r"M:\Remuneração e Benefícios\SINDICAIS\Robô CCTS Rede\Logs",
}


def app_dir():
    return APP_CONFIG_DIR


def config_path():
    return CONFIG_FILE


def _ler_config():
    config = configparser.ConfigParser(interpolation=None)

    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE, encoding="utf-8")

    return config


def _gravar_config(config):
    os.makedirs(APP_CONFIG_DIR, exist_ok=True)

    with open(CONFIG_FILE, "w", encoding="utf-8") as arquivo:
        config.write(arquivo)


def garantir_config_inicial():
    os.makedirs(APP_CONFIG_DIR, exist_ok=True)

    config = _ler_config()
    alterado = False

    if "Settings" not in config:
        config["Settings"] = {}
        alterado = True

    for chave, valor in DEFAULTS.items():
        if chave not in config["Settings"]:
            config["Settings"][chave] = valor
            alterado = True

    if "Email" not in config:
        config["Email"] = {}
        alterado = True

    for chave in ("EmailRemetente", "SenhaApp", "EmailDestinatario"):
        if chave not in config["Email"]:
            config["Email"][chave] = ""
            alterado = True

    if alterado:
        _gravar_config(config)


def carregar_config():
    garantir_config_inicial()
    return _ler_config()


def carregar_settings():
    config = carregar_config()

    return {
        "PastaBase": config.get("Settings", "PastaBase", fallback=DEFAULTS["PastaBase"]).strip(),
        "PastaDestinoBase": config.get(
            "Settings", "PastaDestinoBase", fallback=DEFAULTS["PastaDestinoBase"]
        ).strip(),
        "PastaLogs": config.get("Settings", "PastaLogs", fallback=DEFAULTS["PastaLogs"]).strip(),
    }


garantir_config_inicial()
