# Image Steganography

A small Python project that hides encrypted text inside images using **Least Significant Bit (LSB) steganography** — usable from the command line *or* through a tiny Flask web UI.

## Features

- **Encryption** — message is encrypted with **Fernet** (AES-128-CBC + HMAC-SHA256) using a key derived from your password via PBKDF2 (200 000 iterations).
- **LSB embedding** — encrypted bytes are written into the LSBs of the R/G/B channels with a 32-bit length header for unambiguous extraction.
- **Round-trip safe** — exact byte-for-byte recovery, including Unicode.
- **Quality metrics** — PSNR + SSIM via scikit-image; difference-map visualization via matplotlib.
- **Two interfaces:**
  - **CLI** (`encode.py` / `decode.py` / `main.py`) — for scripting and metrics reports.
  - **Web app** (Flask, single page) — upload, type, click, download.

## How It Works

```
encode:  message  →  Fernet(password)  →  ciphertext (b64)  →  LSBs of cover image  →  stego PNG
decode:  stego PNG  →  read LSBs  →  ciphertext (b64)  →  Fernet(password)  →  message
```

- Each bit of ciphertext overwrites the least-significant bit of one channel byte. Visually invisible (PSNR ≈ 75 dB).
- A 32-bit length header tells the extractor exactly how many bits to read.
- The salt for key derivation is embedded in the ciphertext, so the user only manages the password.

## Project Structure

```
.
├── main.py                   # CLI: end-to-end demo (preprocess + metrics)
├── encode.py                 # CLI: embed
├── decode.py                 # CLI: extract
├── requirements.txt
├── steganography/            # core library (framework-free)
│   ├── lsb.py                #   embed / extract
│   ├── utils.py              #   I/O + preprocessing
│   ├── metrics.py            #   PSNR, SSIM, visualization
│   └── crypto.py             #   Fernet encrypt / decrypt
├── app/                      # web layer
│   ├── __init__.py           #   Flask app factory + error handlers
│   ├── routes.py             #   /, /encode, /decode
│   └── service.py            #   bytes-in / bytes-out bridge to the library
├── templates/index.html      # single-page UI
├── static/
│   ├── style.css
│   └── app.js
├── scripts/download_sipi.py  # fetch USC-SIPI sample images
├── data/                     # cover images
└── results/                  # CLI outputs (stego + reports)
```

## Tech Stack

Python 3.9+ (verified on 3.13) · OpenCV · NumPy · scikit-image · matplotlib · cryptography · Flask · vanilla HTML/CSS/JS.

## Run Locally

```bash
pip install -r requirements.txt
```

### Web app
```bash
flask --app app run
```
Then open http://127.0.0.1:5000.

The page has two cards:
1. **Encrypt & Hide** — pick a cover image, type the secret, type a password, click. `stego.png` downloads automatically.
2. **Extract & Decrypt** — upload the stego image, type the password, click. The recovered message appears below.

### CLI

```bash
# get sample images
python scripts/download_sipi.py --convert-png

# embed
python encode.py --input data/4.2.07.png --output results/stego.png --message "secret"

# extract
python decode.py --input results/stego.png

# end-to-end demo with PSNR/SSIM and visualization
python main.py --input data/4.2.07.png --message "hello"
```

The CLI works on plaintext (no Fernet wrapping) — the encryption layer is web-only by design. If you want encrypted CLI use, call `steganography.crypto.encrypt` first and feed the result to `encode.py --message-file`.

## API (Flask)

| Method | Path     | Body (multipart)                        | Response                         |
| ------ | -------- | --------------------------------------- | -------------------------------- |
| GET    | `/`      | —                                       | HTML page                        |
| POST   | `/encode`| `image` (file), `message`, `password`   | `image/png` download (`stego.png`) |
| POST   | `/decode`| `image` (file), `password`              | `{"message": "..."}` JSON        |

Errors always return `{"error": "..."}` with HTTP 400 (bad input) or 413 (over 8 MB upload).

## Limitations

- Cover must be 3-channel color; grayscale rejected.
- Stego images **must** stay PNG/BMP. JPEG re-saves destroy the LSBs.
- Sequential LSB embedding is detectable by statistical steganalysis (chi-squared, etc.). This is an MVP, not a steganalysis-resistant system.
- 8 MB upload cap on the web endpoint.
