import importlib.util
from pathlib import Path
import base64


def load_module(path):
    spec = importlib.util.spec_from_file_location('web_pyscript', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_build_basic_auth_header():
    p = Path(__file__).parents[1] / 'web' / 'tradingui_pyscript.py'
    mod = load_module(str(p))

    hdr = mod.build_basic_auth_header('user', 'pass')
    assert hdr.startswith('Basic ')
    token = hdr.split(' ', 1)[1]
    assert base64.b64decode(token).decode('utf-8') == 'user:pass'
