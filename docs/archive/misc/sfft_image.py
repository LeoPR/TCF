# Re-run: 2D-STFT (image "slots" like audio) + log-polar (mel-like) scaling + reconstruction
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from pathlib import Path

# Diretórios locais para organização
script_dir = Path(__file__).parent
data_dir = script_dir / "data"
images_dir = script_dir / "images"

data_dir.mkdir(parents=True, exist_ok=True)
images_dir.mkdir(parents=True, exist_ok=True)

# Reprodutibilidade / flags de artefatos
SEED = 42
import random
random.seed(SEED)

# Flags para possíveis artefatos/ruídos (desligados por padrão)
APPLY_NOISE = False
APPLY_SALT_PEPPER = False
APPLY_BLUR = False
# parâmetros padrão (usados quando flags ativadas)
NOISE_PARAMS = {"sigma": 0.02}
SALT_PEPPER_PARAMS = {"amount": 0.01}
BLUR_PARAMS = {"radius": 1}

from PIL import ImageDraw, ImageFilter

def add_gaussian_noise(img, sigma=0.02, rng=None):
    if rng is None:
        rng = np.random.default_rng(SEED)
    noise = rng.normal(0, sigma, img.shape)
    return np.clip(img + noise, 0, 1)

def add_salt_and_pepper(img, amount=0.01, rng=None):
    if rng is None:
        rng = np.random.default_rng(SEED)
    out = img.copy()
    n = img.size
    k = int(n * amount)
    ys = rng.integers(0, img.shape[0], size=k)
    xs = rng.integers(0, img.shape[1], size=k)
    for y, x in zip(ys, xs):
        out[y, x] = rng.choice([0.0, 1.0])
    return out

def add_blur_pil(img, radius=1):
    # img: numpy float [0,1]
    pil = Image.fromarray((img*255).astype(np.uint8))
    pil = pil.filter(ImageFilter.GaussianBlur(radius=radius))
    return np.array(pil).astype(np.float32) / 255.0

def draw_circle(draw, center, radius, fill=255):
    x, y = center
    bbox = [x-radius, y-radius, x+radius, y+radius]
    draw.ellipse(bbox, fill=fill)

def draw_square(draw, center, size, fill=255):
    x, y = center
    half = size//2
    bbox = [x-half, y-half, x+half, y+half]
    draw.rectangle(bbox, fill=fill)

def draw_triangle(draw, center, size, fill=255):
    x, y = center
    h = int(size * 0.866)  # altura do triângulo equilátero
    pts = [(x, y - 2*h//3), (x - size//2, y + h//3), (x + size//2, y + h//3)]
    draw.polygon(pts, fill=fill)

def make_simple_shapes_image(H, W, seed=SEED):
    # Cria uma imagem simples com 3 círculos, 3 quadrados, 3 triângulos em grade 3x3
    rng = np.random.default_rng(seed)
    pil = Image.new('L', (W, H), 0)
    draw = ImageDraw.Draw(pil)
    # posições em 3x3
    ys = [int(H * 1/6), int(H * 3/6), int(H * 5/6)]
    xs = [int(W * 1/4), int(W * 2/4), int(W * 3/4)]
    size = min(H, W) // 8
    # primeira linha: círculos
    for ix, x in enumerate(xs):
        draw_circle(draw, (x, ys[0]), size)
    # segunda linha: quadrados
    for ix, x in enumerate(xs):
        draw_square(draw, (x, ys[1]), size)
    # terceira linha: triângulos
    for ix, x in enumerate(xs):
        draw_triangle(draw, (x, ys[2]), size)
    return np.array(pil).astype(np.float32) / 255.0
 
def make_random_shapes_image(H, W, n_circles=3, n_squares=3, n_triangles=3, seed=SEED,
                             min_size_ratio=0.06, max_size_ratio=0.12):
    rng = np.random.default_rng(seed)
    pil = Image.new('L', (W, H), 0)
    draw = ImageDraw.Draw(pil)
    min_size = max(6, int(min(H, W) * min_size_ratio))
    max_size = max(min_size+1, int(min(H, W) * max_size_ratio))

    def rand_center(margin):
        return (rng.integers(margin, W - margin), rng.integers(margin, H - margin))

    # círculos
    for _ in range(n_circles):
        r = int(rng.integers(min_size, max_size))
        cx, cy = rand_center(r+2)
        draw_circle(draw, (cx, cy), r)
    # quadrados
    for _ in range(n_squares):
        s = int(rng.integers(min_size, max_size))
        cx, cy = rand_center(s//2+2)
        draw_square(draw, (cx, cy), s)
    # triângulos
    for _ in range(n_triangles):
        s = int(rng.integers(min_size, max_size))
        cx, cy = rand_center(int(0.9*s)+2)
        draw_triangle(draw, (cx, cy), s)
    return np.array(pil).astype(np.float32) / 255.0

def np_to_pil_gray(img):
    img8 = (np.clip(img, 0, 1) * 255).astype(np.uint8)
    return Image.fromarray(img8, mode='L')

def make_grid_shapes_image(H, W, n_circles=3, n_squares=3, n_triangles=3, seed=SEED,
                           size_ratio=0.12, margin_ratio=0.05):
    """Gera formas em linhas (círculos, quadrados, triângulos) respeitando quantidades.
    Cada tipo ocupa uma linha; elementos são espaçados horizontalmente de forma uniforme.
    """
    rng = np.random.default_rng(seed)
    pil = Image.new('L', (W, H), 0)
    draw = ImageDraw.Draw(pil)
    rows = []
    if n_circles > 0: rows.append(('circle', n_circles))
    if n_squares > 0: rows.append(('square', n_squares))
    if n_triangles > 0: rows.append(('triangle', n_triangles))
    n_rows = len(rows)
    if n_rows == 0:
        return np.array(pil).astype(np.float32)
    size = int(min(H, W) * size_ratio)
    size = max(size, 8)
    y_positions = np.linspace(margin_ratio*H + size, H - margin_ratio*H - size, n_rows).astype(int)
    for row_idx, (kind, count) in enumerate(rows):
        xs = np.linspace(margin_ratio*W + size, W - margin_ratio*W - size, count).astype(int)
        y = y_positions[row_idx]
        for x in xs:
            if kind == 'circle':
                draw_circle(draw, (x, y), size)
            elif kind == 'square':
                draw_square(draw, (x, y), size)
            elif kind == 'triangle':
                draw_triangle(draw, (x, y), size)
    return np.array(pil).astype(np.float32) / 255.0

from functools import lru_cache

@lru_cache(maxsize=None)
def _precompute_masks(Kh, Kw, n_radial, n_theta, log_base):
    cy, cx = Kh//2, Kw//2
    Y, X = np.ogrid[:Kh, :Kw]
    dy = Y - cy
    dx = X - cx
    R = np.sqrt(dx*dx + dy*dy)
    Theta = np.mod(np.arctan2(dy, dx), 2*np.pi)
    r_max = R.max()
    edges = [0.0]
    v = 1.0
    while v < r_max:
        edges.append(v)
        v *= log_base
    edges.append(r_max+1)
    idxs = np.linspace(0, len(edges)-1, n_radial+1).round().astype(int)
    r_edges = np.array([edges[i] for i in idxs])
    r_edges[-1] = r_max+1
    t_edges = np.linspace(0, 2*np.pi, n_theta+1)
    masks = []  # list of (radial_index, theta_index, mask)
    for i in range(n_radial):
        rmin, rmax = r_edges[i], r_edges[i+1]
        rmask = (R >= rmin) & (R < rmax)
        if not rmask.any():
            continue
        for j in range(n_theta):
            tmin, tmax = t_edges[j], t_edges[j+1]
            if j < n_theta-1:
                tmask = (Theta >= tmin) & (Theta < tmax)
            else:
                tmask = (Theta >= tmin) | (Theta < tmax)
            mask = rmask & tmask
            if mask.any():
                masks.append((i, j, mask))
    return masks, r_edges, t_edges
def hann2d(h, w):
    wy = np.hanning(h)
    wx = np.hanning(w)
    return wy[:, None] * wx[None, :]

def stft2d(x, win, hop_y, hop_x):
    H, W = x.shape
    Kh, Kw = win.shape
    Ys = list(range(0, max(H-Kh,0)+1, hop_y))
    Xs = list(range(0, max(W-Kw,0)+1, hop_x))
    S = np.empty((len(Ys), len(Xs), Kh, Kw), dtype=complex)
    for iy, y in enumerate(Ys):
        for ix, x0 in enumerate(Xs):
            patch = x[y:y+Kh, x0:x0+Kw] * win
            S[iy, ix] = np.fft.fft2(patch)
    return S, Ys, Xs

def istft2d(S, win, H, W, hop_y, hop_x):
    Kh, Kw = win.shape
    nY, nX = S.shape[:2]
    recon = np.zeros((H, W), dtype=float)
    weight = np.zeros((H, W), dtype=float)
    for iy in range(nY):
        for ix in range(nX):
            patch = np.fft.ifft2(S[iy, ix]).real * win
            y = iy*hop_y
            x0 = ix*hop_x
            recon[y:y+Kh, x0:x0+Kw] += patch
            weight[y:y+Kh, x0:x0+Kw] += win**2
    eps = 1e-8
    recon = recon / (weight + eps)
    return np.clip(recon, 0, 1)

def radial_orientation_bins(Fshift, n_radial=16, n_theta=8, log_base=1.5):
    H, W = Fshift.shape
    cy, cx = H//2, W//2
    Y, X = np.ogrid[:H, :W]
    dy = Y - cy
    dx = X - cx
    R = np.sqrt(dx*dx + dy*dy)
    Theta = np.mod(np.arctan2(dy, dx), 2*np.pi)
    mag = np.abs(Fshift)

    r_max = R.max()
    # build geometric edges
    edges = [0.0]
    v = 1.0
    while v < r_max:
        edges.append(v)
        v *= log_base
    edges.append(r_max+1)
    idxs = np.linspace(0, len(edges)-1, n_radial+1).round().astype(int)
    r_edges = np.array([edges[i] for i in idxs])
    r_edges[-1] = r_max+1

    t_edges = np.linspace(0, 2*np.pi, n_theta+1)
    bins = np.zeros((n_radial, n_theta), dtype=float)
    for i in range(n_radial):
        rmin, rmax = r_edges[i], r_edges[i+1]
        rmask = (R >= rmin) & (R < rmax)
        if not rmask.any():
            continue
        for j in range(n_theta):
            tmin, tmax = t_edges[j], t_edges[j+1]
            if j < n_theta-1:
                tmask = (Theta >= tmin) & (Theta < tmax)
            else:
                tmask = (Theta >= tmin) | (Theta < tmax)
            mask = rmask & tmask
            if mask.any():
                bins[i, j] = mag[mask].mean()
    return bins, r_edges, t_edges

def run_stft_pipeline(img,
                      Kh=128, Kw=128,
                      hop_y=None, hop_x=None,
                      n_radial=18, n_theta=12, log_base=1.4,
                      use_fast=False):
    H, W = img.shape
    if hop_y is None:
        hop_y = Kh//2
    if hop_x is None:
        hop_x = Kw//2
    win = hann2d(Kh, Kw)
    S, Ys, Xs = stft2d(img, win, hop_y, hop_x)
    nY, nX = S.shape[:2]
    energy_map = np.zeros((nY, nX))
    for iy in range(nY):
        for ix in range(nX):
            F = np.fft.fftshift(S[iy, ix])
            energy_map[iy, ix] = np.abs(F).mean()
    bins_accum = np.zeros((n_radial, n_theta))
    if use_fast:
        masks, r_edges, t_edges = _precompute_masks(Kh, Kw, n_radial, n_theta, log_base)
        for iy in range(nY):
            for ix in range(nX):
                F = np.fft.fftshift(S[iy, ix])
                mag = np.abs(F)
                # acumular por máscaras precomputadas
                for i, j, mask in masks:
                    if mask.any():
                        bins_accum[i, j] += mag[mask].mean()
    else:
        for iy in range(nY):
            for ix in range(nX):
                F = np.fft.fftshift(S[iy, ix])
                bins, r_edges, t_edges = radial_orientation_bins(
                    F, n_radial=n_radial, n_theta=n_theta, log_base=log_base
                )
                bins_accum += bins
    bins_mean = bins_accum / (nY * nX)
    img_rec = istft2d(S, win, H, W, hop_y, hop_x)
    return {
        "S": S,
        "energy_map": energy_map,
        "bins_mean": bins_mean,
        "img_rec": img_rec,
        "params": {
            "Kh": Kh, "Kw": Kw, "hop_y": hop_y, "hop_x": hop_x,
            "n_radial": n_radial, "n_theta": n_theta, "log_base": log_base,
            "nY": nY, "nX": nX
        }
    }

def save_and_plot_sequence(img, results, prefix_dir=images_dir, create_composite=True):
    # img input
    plt.figure(); plt.title("Input"); plt.imshow(img, cmap='gray', vmin=0, vmax=1); plt.axis('off'); plt.tight_layout(); plt.savefig(prefix_dir/"01_input.png"); plt.close()
    # params
    p = results['params']
    params_str = "\n".join([
        f"Window: {p['Kh']}x{p['Kw']}",
        f"Hop: {p['hop_y']}x{p['hop_x']}",
        f"n_radial: {p['n_radial']}",
        f"n_theta: {p['n_theta']}",
        f"log_base: {p['log_base']}",
        f"n_patches: {p['nY']}x{p['nX']}"
    ])
    plt.figure(figsize=(6,3)); plt.axis('off'); plt.text(0,0.9,"Parâmetros",fontsize=12,weight='bold'); plt.text(0,0.6,params_str,fontsize=10,family='monospace'); plt.tight_layout(); plt.savefig(prefix_dir/"02_params.png"); plt.close()
    # energy
    plt.figure(); plt.title("Mapa de energia 2D-STFT"); plt.imshow(results['energy_map'], interpolation='nearest'); plt.colorbar(); plt.tight_layout(); plt.savefig(prefix_dir/"03_energy_map.png"); plt.close()
    # log-polar
    plt.figure(); plt.title("Log-Polar média"); plt.imshow(results['bins_mean'], aspect='auto', interpolation='nearest'); plt.colorbar(); plt.tight_layout(); plt.savefig(prefix_dir/"04_logpolar.png"); plt.close()
    # reconstrução
    plt.figure(); plt.title("Reconstrução (iSTFT)"); plt.imshow(results['img_rec'], cmap='gray', vmin=0, vmax=1); plt.axis('off'); plt.tight_layout(); plt.savefig(prefix_dir/"05_reconstruction.png"); plt.close()
    if create_composite:
        try:
            seq_files = [prefix_dir/"01_input.png", prefix_dir/"02_params.png", prefix_dir/"03_energy_map.png", prefix_dir/"04_logpolar.png", prefix_dir/"05_reconstruction.png"]
            imgs = []
            for f in seq_files:
                if f.exists():
                    imgs.append(Image.open(f).convert('RGB'))
            if imgs:
                thumb_w, thumb_h = 512, 512
                processed = []
                for im in imgs:
                    im = im.copy(); im.thumbnail((thumb_w, thumb_h), Image.LANCZOS)
                    bg = Image.new('RGB', (thumb_w, thumb_h), (255,255,255))
                    x = (thumb_w - im.width)//2; y = (thumb_h - im.height)//2
                    bg.paste(im, (x,y)); processed.append(bg)
                cols = 2; rows = (len(processed)+cols-1)//cols; margin = 10
                out_w = cols*thumb_w + (cols+1)*margin; out_h = rows*thumb_h + (rows+1)*margin
                out = Image.new('RGB', (out_w, out_h), (240,240,240))
                for idx, im in enumerate(processed):
                    r = idx//cols; c = idx%cols
                    x = margin + c*(thumb_w+margin); y = margin + r*(thumb_h+margin)
                    out.paste(im, (x,y))
                draw = ImageDraw.Draw(out)
                labels = ["01 Input","02 Params","03 Energy","04 LogPolar","05 Recon"]
                try:
                    from PIL import ImageFont
                    font = ImageFont.truetype("arial.ttf", 16)
                except Exception:
                    font = None
                for idx, label in enumerate(labels[:len(processed)]):
                    r = idx//cols; c = idx%cols
                    x = margin + c*(thumb_w+margin); y = margin + r*(thumb_h+margin) + thumb_h + 4
                    draw.text((x,y), label, fill=(0,0,0), font=font)
                out.save(prefix_dir/"06_sequence.png")
        except Exception as e:
            print("Falha composite:", e)
    return prefix_dir/"06_sequence.png"

def apply_artifacts(img):
    modified = img
    if APPLY_NOISE:
        modified = add_gaussian_noise(modified, sigma=NOISE_PARAMS.get('sigma',0.02))
    if APPLY_SALT_PEPPER:
        modified = add_salt_and_pepper(modified, amount=SALT_PEPPER_PARAMS.get('amount',0.01))
    if APPLY_BLUR:
        modified = add_blur_pil(modified, radius=BLUR_PARAMS.get('radius',1))
    return modified

def main():
    # load or synth image
    candidates = [images_dir/"input.jpg", images_dir/"input.png"]
    img_path = None
    for c in candidates:
        if c.exists():
            img_path = c
            break
    if img_path is None:
        H, W = 512, 512
        img = make_simple_shapes_image(H, W, seed=SEED)
        Image.fromarray((img*255).astype(np.uint8)).save(images_dir/"01_input_used_stft.png")
        # exibir e salvar input
        plt.figure(); plt.title("Input (simple shapes)"); plt.imshow(img, cmap='gray', vmin=0, vmax=1); plt.axis('off'); plt.tight_layout(); plt.savefig(images_dir/"01_input.png"); plt.close()
        img = apply_artifacts(img)
    else:
        img = Image.open(img_path).convert("L")
        img = np.array(img).astype(np.float32) / 255.0
        Image.fromarray((img*255).astype(np.uint8)).save(images_dir/"01_input_used_stft.png")

    # run pipeline com defaults atuais
    results = run_stft_pipeline(img, Kh=128, Kw=128, hop_y=64, hop_x=64, n_radial=18, n_theta=12, log_base=1.4)
    # salvar numpy
    np.save(data_dir/"stft2d_complex.npy", results['S'])
    np.save(data_dir/"stft2d_energy_map.npy", results['energy_map'])
    np.save(data_dir/"stft2d_logpolar_bins.npy", results['bins_mean'])
    # salvar sequência e imagens finais
    seq_path = save_and_plot_sequence(img, results, prefix_dir=images_dir, create_composite=True)
    Image.fromarray((img*255).astype(np.uint8)).save(images_dir/"stft2d_original.png")
    Image.fromarray((results['img_rec']*255).astype(np.uint8)).save(images_dir/"stft2d_reconstruction.png")
    print("Arquivos salvos:")
    print(f"- {images_dir}/input_used_stft.png")
    print(f"- {images_dir}/stft2d_original.png")
    print(f"- {images_dir}/stft2d_reconstruction.png")
    print(f"- {data_dir}/stft2d_complex.npy")
    print(f"- {data_dir}/stft2d_energy_map.npy")
    print(f"- {data_dir}/stft2d_logpolar_bins.npy")
    if seq_path:
        print(f"Sequência final salva: {seq_path}")

if __name__ == "__main__":
    main()
