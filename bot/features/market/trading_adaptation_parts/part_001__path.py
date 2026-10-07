# Auto-split part 1: _path
def _path():
    root = os.getenv("ALIMJ_DATA_DIR") or os.path.join(os.getcwd(), "data")
    os.makedirs(root, exist_ok=True)
    return os.path.join(root, "trading_adaptation.json")
