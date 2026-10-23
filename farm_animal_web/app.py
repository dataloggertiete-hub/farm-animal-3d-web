#!/usr/bin/env python3
"""
Aplicação Web Flask para Gerar Modelos 3D de Animais de Fazenda
================================================================
Endpoint web que permite gerar STL (sólido ou articulado) e baixar como ZIP.
"""

import os
import shutil
import zipfile
import uuid
from pathlib import Path
from flask import Flask, render_template, request, send_file, redirect, url_for, flash
from gerador import gerar_solido, gerar_articulado, SOLID_GENERATORS, ARTICULATED_GENERATORS

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Pasta temporária para arquivos gerados
BASE_OUT = Path(__file__).parent / "generated"
BASE_OUT.mkdir(exist_ok=True)


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        animal = request.form.get("animal", "bovino")
        tipo = request.form.get("tipo", "solido")
        escala = request.form.get("scale", type=float)
        joint_d = request.form.get("joint", type=float) or 3.0

        if animal not in SOLID_GENERATORS:
            flash("Espécie desconhecida.", "danger")
            return redirect(url_for("index"))

        # Criar diretório único para esta execução
        run_id = uuid.uuid4().hex
        out_dir = BASE_OUT / run_id
        out_dir.mkdir(parents=True)

        try:
            if tipo == "solido":
                stl_path = gerar_solido(animal, escala, str(out_dir))
                # Criar ZIP com o STL único
                zip_path = out_dir / f"{animal}_solido.zip"
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
                    z.write(stl_path, arcname=Path(stl_path).name)
                download_path = zip_path

            else:  # articulado
                piece_dir = gerar_articulado(animal, escala, joint_d, str(out_dir))
                # ZIP com TODAS as peças + guia
                zip_path = out_dir / f"{animal}_articulado.zip"
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
                    for root, _, files in os.walk(piece_dir):
                        for f in files:
                            full = Path(root) / f
                            rel = full.relative_to(piece_dir.parent)
                            z.write(full, arcname=rel)
                download_path = zip_path

        except Exception as e:
            flash(f"Erro ao gerar o modelo: {e}", "danger")
            shutil.rmtree(out_dir, ignore_errors=True)
            return redirect(url_for("index"))

        # Redireciona para download
        return redirect(url_for("download", token=run_id))

    # GET - mostra formulário
    return render_template(
        "index.html",
        especies=list(SOLID_GENERATORS.keys()),
        default_scale=10.0,
        default_joint=3.0,
    )


@app.route("/download/<token>")
def download(token):
    """Entrega o ZIP gerado."""
    zip_path = next(BASE_OUT.glob(f"{token}/*_*.zip"), None)
    if not zip_path or not zip_path.is_file():
        flash("Arquivo não encontrado ou expirado.", "warning")
        return redirect(url_for("index"))

    return send_file(
        zip_path,
        as_attachment=True,
        download_name=zip_path.name,
        mimetype="application/zip",
    )


if __name__ == "__main__":
    # Modo desenvolvimento
    app.run(host="0.0.0.0", port=5000, debug=True)