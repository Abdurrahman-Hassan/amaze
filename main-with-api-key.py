"""
Example: Adding API Key Authentication to your QR Code Microservice

This adds a simple API key check to prevent unauthorized direct API access.
The API key should be stored as an environment variable in Appwrite.
"""

# Add this to your imports in main.py
from fastapi import FastAPI, Form, File, UploadFile, HTTPException, Request, Header
from typing import Optional
import os

# Add this after your configuration constants
API_KEY = os.getenv("API_KEY", "your-secret-api-key-here")  # Set in Appwrite environment variables

# Add this middleware BEFORE the rate limiting middleware
@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    """Check API key for all requests except health check"""
    
    # Skip API key check for health endpoint
    if request.url.path == "/health":
        return await call_next(request)
    
    # Get API key from header
    api_key = request.headers.get("X-API-Key") or request.headers.get("Authorization")
    
    # Check if API key is valid
    if not api_key or api_key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key"
        )
    
    return await call_next(request)


# Alternative: Check API key in the endpoint directly
@app.post("/qr")
async def generate_qr(
    words: str = Form(..., description="Text to encode in QR code"),
    version: int = Form(1, ge=1, le=40, description="QR code version (1-40)"),
    level: str = Form('H', description="Error correction level (L, M, Q, H)"),
    picture: Optional[UploadFile] = File(None, description="Background image (PNG/JPG/GIF/WebP)"),
    colorized: bool = Form(False, description="Colorize the QR code"),
    contrast: float = Form(1.0, ge=0.1, le=10.0, description="Image contrast"),
    brightness: float = Form(1.0, ge=0.1, le=10.0, description="Image brightness"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")  # Add this parameter
):
    """Generate QR code with API key authentication"""
    
    # Check API key (if using endpoint-level check instead of middleware)
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    
    # Rest of your existing code...
    pass


# How to use from your website (JavaScript):

"""
// In your frontend JavaScript:
const API_KEY = 'your-secret-api-key-here'; // Store this securely

async function generateQR(text) {
    const formData = new FormData();
    formData.append('words', text);
    formData.append('version', '1');
    formData.append('level', 'H');
    
    const response = await fetch('YOUR_APPWRITE_FUNCTION_URL/qr', {
        method: 'POST',
        headers: {
            'X-API-Key': API_KEY  // Add API key header
        },
        body: formData
    });
    
    if (response.ok) {
        const blob = await response.blob();
        return URL.createObjectURL(blob);
    } else {
        throw new Error('Failed to generate QR code');
    }
}
"""

# How to test with curl:
"""
curl -X POST "YOUR_APPWRITE_FUNCTION_URL/qr" \
  -H "X-API-Key: your-secret-api-key-here" \
  -F "words=https://qrcartoon.com" \
  -F "version=1" \
  -F "level=H" \
  -o qr-code.png
"""

# How to test with Postman:
"""
1. Add header: X-API-Key: your-secret-api-key-here
2. Make your POST request as usual
3. Without the header, you'll get 401 Unauthorized
"""

# Setting API key in Appwrite:
"""
1. Go to your Appwrite Function settings
2. Navigate to "Settings" > "Environment Variables"
3. Add variable:
   - Key: API_KEY
   - Value: your-secret-api-key-here (generate a strong random string)
4. Redeploy your function
"""

# Generate a secure API key:
"""
import secrets
api_key = secrets.token_urlsafe(32)
print(api_key)  # Use this as your API_KEY
"""
