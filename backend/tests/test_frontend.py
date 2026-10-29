from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.frontend import setup_frontend


def make_site(tmp_path):
    """Un `dist` mínimo: index.html, un asset y un archivo de public/."""
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<html>app</html>")
    (tmp_path / "assets" / "index-abc.js").write_text("console.log(1)")
    (tmp_path / "favicon.svg").write_text("<svg/>")
    (tmp_path.parent / "secreto.txt").write_text("no")
    app = FastAPI()

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    setup_frontend(app, tmp_path)
    return TestClient(app)


def test_raiz_y_rutas_de_react_devuelven_index(tmp_path):
    client = make_site(tmp_path)
    for path in ["/", "/w/123/hoja", "/invite/abc", "/recuperar/tok"]:
        response = client.get(path)
        assert response.status_code == 200
        assert response.text == "<html>app</html>"


def test_assets_y_archivos_de_public(tmp_path):
    client = make_site(tmp_path)
    assert client.get("/assets/index-abc.js").text == "console.log(1)"
    assert client.get("/favicon.svg").text == "<svg/>"
    assert client.get("/assets/no-existe.js").status_code == 404


def test_la_api_tiene_prioridad_y_sus_404_no_son_la_web(tmp_path):
    client = make_site(tmp_path)
    assert client.get("/api/health").json() == {"status": "ok"}
    response = client.get("/api/no-existe")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_no_se_sale_de_la_carpeta(tmp_path):
    client = make_site(tmp_path)
    response = client.get("/..%2Fsecreto.txt")
    assert response.text == "<html>app</html>"
