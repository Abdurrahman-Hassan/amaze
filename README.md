# QR Code Microservice

A microservice for generating artistic and animated QR codes using [amazing-qr](https://github.com/x-hw/amazing-qr).

## Features

- ✅ **Static QR Codes** - Generate standard QR codes
- 🎨 **Artistic QR Codes** - Create QR codes with custom background images
- 🎬 **Animated GIF QR Codes** - Generate animated QR codes from GIF images
- 🔧 **Customizable** - Adjust version, error correction, contrast, brightness, and colorization
- 🚀 **Fast & Lightweight** - Minimal dependencies
- 📊 **Health Check** - Built-in monitoring endpoint

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## Usage

### Start the server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### API Endpoints

#### Health Check
```bash
GET /health
```

#### Generate QR Code
```bash
POST /qr
```

**Parameters:**
- `words` (required): Text to encode in the QR code
- `version` (optional, default=1): QR code version (1-40)
- `level` (optional, default='H'): Error correction level (L, M, Q, H)
- `picture` (optional): Background image file (PNG/JPG/GIF)
- `colorized` (optional, default=false): Colorize the QR code
- `contrast` (optional, default=1.0): Image contrast (0.1-10.0)
- `brightness` (optional, default=1.0): Image brightness (0.1-10.0)

### Examples

#### 1. Static QR Code (text only)
```bash
curl -X POST "http://localhost:8000/qr" \
  -F "words=https://example.com" \
  -o qrcode.png
```

#### 2. Artistic QR Code (with image)
```bash
curl -X POST "http://localhost:8000/qr" \
  -F "words=https://example.com" \
  -F "picture=@background.png" \
  -F "colorized=true" \
  -o artistic_qr.png
```

#### 3. Animated GIF QR Code
```bash
curl -X POST "http://localhost:8000/qr" \
  -F "words=https://example.com" \
  -F "picture=@animation.gif" \
  -F "colorized=true" \
  -o animated_qr.gif
```

#### 4. Custom Parameters
```bash
curl -X POST "http://localhost:8000/qr" \
  -F "words=https://example.com" \
  -F "picture=@background.jpg" \
  -F "version=5" \
  -F "level=H" \
  -F "colorized=true" \
  -F "contrast=1.5" \
  -F "brightness=1.2" \
  -o custom_qr.png
```

## Error Correction Levels

- **L** - Low (7% error correction)
- **M** - Medium (15% error correction)
- **Q** - Quartile (25% error correction)
- **H** - High (30% error correction) - **Recommended**

## Deployment

### Appwrite Functions

This microservice is designed to work with Appwrite's serverless functions:

1. Create a new function in Appwrite
2. Upload the code
3. Set the entrypoint to `main.py`
4. Deploy

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## File Size Limits

- Maximum upload size: 10MB
- Recommended image size: 1000x1000 pixels or smaller

## Notes

- Temporary files are stored in the `temp/` directory with session isolation
- Files are automatically cleaned up on server shutdown
- CORS is enabled for all origins (configure as needed for production)
- All endpoints return proper HTTP status codes and error messages

## License

MIT
