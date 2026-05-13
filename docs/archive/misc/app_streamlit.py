import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from PIL import Image
import io

# Import functions from sfft_image.py (safe due to __main__ guard)
from outros_projetos.sfft_image import (
    SEED, images_dir, data_dir,
    make_simple_shapes_image, make_random_shapes_image, make_grid_shapes_image,
    apply_artifacts, run_stft_pipeline, save_and_plot_sequence,
    np_to_pil_gray
)

st.set_page_config(page_title="2D-STFT (Imagem) - Painel", layout="wide")
st.title("Painel Dinâmico: Análise 2D-STFT de Imagens (estilo áudio)")

# Sidebar - parâmetros de entrada
with st.sidebar:
    st.header("Entrada & Formas")
    H = st.number_input("Altura (H)", min_value=64, max_value=2048, value=512, step=32, key="height")
    W = st.number_input("Largura (W)", min_value=64, max_value=2048, value=512, step=32, key="width")
    seed = st.number_input("Seed", min_value=0, max_value=10_000, value=SEED, step=1, key="seed")
    arrangement = st.selectbox("Arranjo das formas", ["grid", "random"], index=0, key="arrangement")
    n_circles = st.number_input("# Círculos", 0, 50, 3, key="circles")
    n_squares = st.number_input("# Quadrados", 0, 50, 3, key="squares")
    n_triangles = st.number_input("# Triângulos", 0, 50, 3, key="triangles")

    st.header("Artefatos (opcional)")
    apply_noise = st.checkbox("Ruído Gaussiano", value=False, key="noise_check")
    sigma = st.slider("Sigma do ruído", 0.0, 0.2, 0.02, 0.005, key="sigma")
    apply_sp = st.checkbox("Sal & Pimenta", value=False, key="sp_check")
    amount_sp = st.slider("Quantidade S&P", 0.0, 0.2, 0.01, 0.005, key="sp_amount")
    apply_blur = st.checkbox("Desfoque (Gaussian)", value=False, key="blur_check")
    radius_blur = st.slider("Raio blur", 0, 10, 1, 1, key="blur_radius")

    st.header("Parâmetros STFT")
    Kh = st.number_input("Janela (Kh)", 8, 512, 128, 8, key="kh")
    Kw = st.number_input("Janela (Kw)", 8, 512, 128, 8, key="kw")
    hop_y = st.number_input("Hop Y", 1, 512, Kh//2, 1, key="hopy")
    hop_x = st.number_input("Hop X", 1, 512, Kw//2, 1, key="hopx")
    n_radial = st.number_input("Bins radiais", 2, 64, 18, 1, key="radial")
    n_theta = st.number_input("Bins angulares", 2, 64, 12, 1, key="theta")
    log_base = st.slider("Base log-polar", 1.05, 2.5, 1.4, 0.01, key="logbase")
    use_fast = st.checkbox("Modo rápido (pré-computar máscaras log-polar)", value=True, key="usefast")

# Gerar imagem de entrada (sempre roda automaticamente com mudanças nos widgets)
if arrangement == "grid":
    # grid deve respeitar os counts informados
    img = make_grid_shapes_image(H, W, n_circles=n_circles, n_squares=n_squares, n_triangles=n_triangles, seed=seed)
else:
    img = make_random_shapes_image(H, W, n_circles=n_circles, n_squares=n_squares, n_triangles=n_triangles, seed=seed)

# Aplicar artefatos (apenas dentro do app)
if apply_noise:
    rng = np.random.default_rng(seed)
    img = np.clip(img + rng.normal(0, sigma, img.shape), 0, 1)
if apply_sp:
    rng = np.random.default_rng(seed+1)
    out = img.copy(); n = img.size; k = int(n*amount_sp)
    ys = rng.integers(0, img.shape[0], size=k); xs = rng.integers(0, img.shape[1], size=k)
    for y, x in zip(ys, xs): out[y, x] = rng.choice([0.0, 1.0])
    img = out
if apply_blur:
    from PIL import ImageFilter
    pil = Image.fromarray((img*255).astype(np.uint8))
    pil = pil.filter(ImageFilter.GaussianBlur(radius=radius_blur))
    img = np.array(pil).astype(np.float32) / 255.0

# Rodar pipeline STFT
res = run_stft_pipeline(img, Kh=Kh, Kw=Kw, hop_y=hop_y, hop_x=hop_x, n_radial=n_radial, n_theta=n_theta, log_base=log_base, use_fast=use_fast)

# Criar figura compacta com matplotlib (2x2 grid: original, energia, log-polar, reconstrução)
fig, axes = plt.subplots(2, 2, figsize=(12, 12))
fig.suptitle("Análise 2D-STFT (estilo áudio)", fontsize=16, weight='bold')

# Original
axes[0, 0].imshow(img, cmap='gray', vmin=0, vmax=1)
axes[0, 0].set_title("01 - Input (Original)")
axes[0, 0].axis('off')

# Energy map
im1 = axes[0, 1].imshow(res['energy_map'], interpolation='nearest', cmap='viridis')
axes[0, 1].set_title("03 - Mapa de Energia (2D-STFT)")
axes[0, 1].set_xlabel("Janela X")
axes[0, 1].set_ylabel("Janela Y")
plt.colorbar(im1, ax=axes[0, 1], fraction=0.046, pad=0.04)

# Log-polar
im2 = axes[1, 0].imshow(res['bins_mean'], aspect='auto', interpolation='nearest', cmap='plasma')
axes[1, 0].set_title("04 - Log-Polar (radial × orientação)")
axes[1, 0].set_xlabel("Bins de Orientação")
axes[1, 0].set_ylabel("Bins Radiais (baixo→alto, log)")
plt.colorbar(im2, ax=axes[1, 0], fraction=0.046, pad=0.04)

# Reconstrução
axes[1, 1].imshow(res['img_rec'], cmap='gray', vmin=0, vmax=1)
axes[1, 1].set_title("05 - Reconstrução (iSTFT 2D)")
axes[1, 1].axis('off')

plt.tight_layout()

# Converter figura matplotlib para imagem PIL para exibir no Streamlit
buf = io.BytesIO()
fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
buf.seek(0)
composite_img = Image.open(buf)
plt.close(fig)

# Exibir composite compacto
st.image(composite_img, caption="Visualização Completa", use_container_width=True)

# Parâmetros em expander
with st.expander("Ver parâmetros STFT"):
    st.json(res['params'])

# Botão para salvar
if st.button("Salvar composite em images/streamlit_composite.png"):
    out_path = Path(images_dir) / "streamlit_composite.png"
    composite_img.save(out_path)
    st.success(f"Salvo em {out_path}")
