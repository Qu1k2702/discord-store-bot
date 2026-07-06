import json
from pathlib import Path
from threading import Lock

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

PRODUCTS_FILE = DATA_DIR / "products.json"
TICKETS_FILE = DATA_DIR / "tickets.json"

_lock = Lock()


def _load(path: Path, default):
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()
        return json.loads(content) if content else default


def _save(path: Path, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_products() -> dict:
    """Retorna {product_id: {name, description, price, image, stock, channel_id, message_id}}"""
    with _lock:
        return _load(PRODUCTS_FILE, {})


def save_products(products: dict) -> None:
    with _lock:
        _save(PRODUCTS_FILE, products)


def load_tickets() -> dict:
    """Retorna {"user_id": {"channel_id": int, "product_id": str}}

    Um usuário só pode ter UMA entrada aqui por vez (regra de negócio:
    apenas uma solicitação/ticket aberto por usuário simultaneamente).
    """
    with _lock:
        return _load(TICKETS_FILE, {})


def save_tickets(tickets: dict) -> None:
    with _lock:
        _save(TICKETS_FILE, tickets)


def next_product_id(products: dict) -> str:
    if not products:
        return "1"
    return str(max(int(k) for k in products.keys()) + 1)
