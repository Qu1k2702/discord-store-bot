def parse_price(price: str) -> float:
    """Converte um preço em formato brasileiro ('29,90' ou 'R$ 1.234,56')
    para float (29.90 / 1234.56)."""
    cleaned = price.replace("R$", "").strip()
    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError as exc:
        raise ValueError(f"Não foi possível interpretar o preço '{price}' como número.") from exc