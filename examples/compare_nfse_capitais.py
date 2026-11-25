"""Mosaico nota real × sintética por capital (precisa dos PDFs reais baixados em --real-dir).

    python examples/compare_nfse_capitais.py --real-dir <pasta com cap_all.json e nfse_pdfs/> --out <png>
Os PDFs reais não são versionados; só os moldes numéricos em renderers/nfse_cidades_specs/.
"""
import argparse, json, sys, warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import fitz  # noqa: E402
from PIL import Image  # noqa: E402

from generator.nfse_legado import generate_nfse_legado  # noqa: E402
from renderers.nfse_legado import NfseLegado  # noqa: E402

ap = argparse.ArgumentParser(); ap.add_argument("--real-dir", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--dpi", type=int, default=62)
a = ap.parse_args()
real = Path(a.real_dir); caps = json.load(open(real / "cap_all.json"))
rows = []
for city, files in caps.items():
    xml, fv = generate_nfse_legado(seed=5, city_layout=city)
    syn = bytes(NfseLegado(xml, fv["razao_social_prestador"], fv["municipality_name"], city).output())
    ims = []
    for data in (open(real / files[0], "rb").read(), syn):
        pm = fitz.open(stream=data, filetype="pdf")[0].get_pixmap(dpi=a.dpi)
        ims.append(Image.frombytes("RGB", (pm.width, pm.height), pm.samples))
    rows.append(ims)
m = Image.new("RGB", (sum(i.width for r in rows for i in r), max(i.height for r in rows for i in r)), "white"); x = 0
for r in rows:
    for i in r: m.paste(i, (x, 0)); x += i.width
m.save(a.out); print(m.size, [c for c in caps])
