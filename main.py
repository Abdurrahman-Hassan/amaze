"""
QR Code Microservice for Appwrite Functions
Generates static, artistic, and animated GIF QR codes
"""

import os
import logging
from fastapi import FastAPI, Form, File, UploadFile, HTTPException, Request, Header
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from amzqr import amzqr
from typing import Optional
from PIL import Image
from io import BytesIO
import tempfile
import time
from collections import defaultdict
from datetime import datetime, timedelta
import hashlib
import hmac

# Load .env file for local development (not needed in Appwrite)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, using environment variables directly

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security Configuration
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB (reduced for bandwidth optimization)
MAX_REQUESTS_PER_MINUTE = 20  # Rate limit per IP (reduced from 30 for better protection)
MAX_REQUESTS_PER_MINUTE_NO_KEY = 5  # Stricter limit without API key
MAX_QR_TEXT_LENGTH = 1000  # Maximum characters in QR code (reduced for faster processing)

# API Key Configuration (set in Appwrite environment variables)
API_KEY = os.getenv("API_KEY", "")  # Set this in Appwrite Function settings
API_SECRET = os.getenv("API_SECRET", "")  # For request signing (optional, more secure)

# Allowed domains for referer check
ALLOWED_DOMAINS = ["qrcartoon.com", "www.qrcartoon.com"]

# Log API key status on startup (for debugging)
if API_KEY:
    logger.info(f"✓ API_KEY loaded: {API_KEY[:10]}...")
else:
    logger.warning("⚠ WARNING: API_KEY not set! API will reject all requests.")

# Optimization Configuration
MAX_IMAGE_SIZE = 400  # Maximum dimension for uploaded images (reduced from 600)
MAX_GIF_FRAMES = 20  # Maximum GIF frames (reduced from 40)
MAX_GIF_SIZE = 300  # Maximum GIF dimension (reduced from 400)
JPEG_QUALITY = 65  # JPEG compression quality (reduced from 75)

# Rate limiting storage (in-memory, use Redis for production)
rate_limit_storage = defaultdict(list)

app = FastAPI(
    title="QR Code Microservice",
    description="Generate artistic and animated QR codes using amazing-qr",
    version="1.0.0",
    docs_url=None,  # Disable docs in production for security
    redoc_url=None,  # Disable redoc in production for security
    openapi_url=None,  # Disable OpenAPI schema for bandwidth savings
)

# Security Middleware
# Add trusted host middleware to prevent host header attacks
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["qrcartoon.com", "www.qrcartoon.com", "localhost", "127.0.0.1", "*"]
)

# Add GZip compression for responses (aggressive compression for bandwidth savings)
app.add_middleware(GZipMiddleware, minimum_size=500, compresslevel=9)

# Add CORS middleware - restricted to specific domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://qrcartoon.com",
        "https://www.qrcartoon.com", 
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key", "x-api-key"],
    max_age=3600,  # Cache preflight requests for 1 hour
)

# Rate limiting middleware
@app.middleware("http")
async def security_validation_middleware(request: Request, call_next):
    """Strict API key authentication - REQUIRES API key for all requests"""
    client_ip = request.client.host if request.client else "unknown"

    # Skip security for health check
    if request.url.path == "/health":
        return await call_next(request)

    # REQUIRE API Key for ALL requests (no exceptions)
    api_key = request.headers.get("X-API-Key") or request.headers.get("x-api-key")

    # Check if API key is valid
    if not api_key or not API_KEY or api_key != API_KEY:
        return JSONResponse(
            status_code=401,
            content={"detail": "Unauthorized. Valid API key required in X-API-Key header."}
        )

    # Rate limiting (with valid API key)
    current_time = datetime.now()
    rate_limit_storage[client_ip] = [
        timestamp for timestamp in rate_limit_storage[client_ip]
        if current_time - timestamp < timedelta(minutes=1)
    ]

    if len(rate_limit_storage[client_ip]) >= MAX_REQUESTS_PER_MINUTE:
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please try again later."}
        )

    rate_limit_storage[client_ip].append(current_time)

    # Process request
    response = await call_next(request)

    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"

    return response


@app.get("/health")
async def health_check():
    """Lightweight health check endpoint"""
    return {"ok": 1}

@app.post("/qr")
async def generate_qr(
    words: str = Form(..., description="Text to encode in QR code"),
    version: int = Form(1, ge=1, le=40, description="QR code version (1-40)"),
    level: str = Form('H', description="Error correction level (L, M, Q, H)"),
    picture: Optional[UploadFile] = File(None, description="Background image (PNG/JPG/GIF/WebP)"),
    colorized: bool = Form(False, description="Colorize the QR code"),
    contrast: float = Form(1.0, ge=0.1, le=10.0, description="Image contrast"),
    brightness: float = Form(1.0, ge=0.1, le=10.0, description="Image brightness"),
):
    """
    Generate a QR code with optional artistic background or animated GIF.
    
    **Parameters:**
    - **words**: The data to be encoded in the QR code
    - **version**: QR code version (1-40), higher = more data capacity
    - **level**: Error correction level (L=7%, M=15%, Q=25%, H=30%)
    - **picture**: Optional background image (PNG/JPG/GIF/WebP - auto-converted)
    - **colorized**: Whether to colorize the QR code (only with picture)
    - **contrast**: Adjust image contrast (0.1-10.0)
    - **brightness**: Adjust image brightness (0.1-10.0)
    
    **Returns:**
    - QR code image (PNG for static, GIF for animated)
    """
    
    # Security validations
    if not words or not words.strip():
        raise HTTPException(status_code=400, detail="QR code text cannot be empty")
    
    if len(words) > MAX_QR_TEXT_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Text too long. Maximum length is {MAX_QR_TEXT_LENGTH} characters"
        )
    
    # Validate error correction level
    if level not in ['L', 'M', 'Q', 'H']:
        raise HTTPException(status_code=400, detail="Level must be one of: L, M, Q, H")
    
    # Validate file type if picture is provided
    if picture:
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        file_ext = os.path.splitext(picture.filename)[1].lower()
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
            )
    
    # Use system temp directory - automatically cleaned by OS
    temp_dir = tempfile.mkdtemp()
    picture_path = None
    output_file = None
    
    try:
        # Handle file upload
        if picture:
            # Validate file size
            contents = await picture.read()
            if len(contents) > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=400, 
                    detail=f"File too large. Maximum size is {MAX_FILE_SIZE / 1024 / 1024}MB"
                )
            
            # Save uploaded file to temp
            original_path = os.path.join(temp_dir, picture.filename)
            with open(original_path, "wb") as buffer:
                buffer.write(contents)
            
            # Convert unsupported formats to PNG/GIF
            # amzqr supports: .jpg, .png, .bmp, .gif
            file_ext = os.path.splitext(picture.filename)[1].lower()
            supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.gif']
            
            # Optimize image before processing
            is_gif = file_ext == '.gif'
            
            if file_ext not in supported_formats:
                try:
                    img = Image.open(original_path)
                    # Convert to RGB if necessary (for formats like WebP with transparency)
                    if img.mode in ('RGBA', 'LA', 'P'):
                        # Create white background for transparency
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                        img = background
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Aggressive resize for bandwidth optimization
                    if img.width > MAX_IMAGE_SIZE or img.height > MAX_IMAGE_SIZE:
                        img.thumbnail((MAX_IMAGE_SIZE, MAX_IMAGE_SIZE), Image.Resampling.LANCZOS)
                    
                    # Save as JPEG for better compression (smaller file size)
                    converted_path = os.path.join(temp_dir, "converted_image.jpg")
                    img.save(converted_path, 'JPEG', quality=JPEG_QUALITY, optimize=True)
                    picture_path = converted_path
                except Exception as e:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unable to process image format {file_ext}. Supported: JPG, PNG, BMP, GIF, WebP"
                    )
            elif is_gif:
                # Optimize GIF - reduce frames and resize for faster processing
                try:
                    from PIL import ImageSequence
                    
                    gif = Image.open(original_path)
                    frames = []
                    durations = []
                    
                    # Extract and optimize frames
                    frame_count = 0
                    
                    for i, frame in enumerate(ImageSequence.Iterator(gif)):
                        # Skip every 3rd frame for bandwidth optimization (keep 2, skip 1)
                        if i % 3 == 2:
                            continue
                        
                        if frame_count >= MAX_GIF_FRAMES:
                            break
                        
                        # Convert frame to RGB
                        frame_rgb = frame.convert('RGB')
                        
                        # Aggressive resize for bandwidth savings
                        if frame_rgb.width > MAX_GIF_SIZE or frame_rgb.height > MAX_GIF_SIZE:
                            frame_rgb.thumbnail((MAX_GIF_SIZE, MAX_GIF_SIZE), Image.Resampling.BILINEAR)  # BILINEAR is faster than LANCZOS
                        
                        frames.append(frame_rgb)
                        
                        # Get frame duration and adjust (since we're skipping frames)
                        try:
                            duration = frame.info.get('duration', 100)
                        except:
                            duration = 100
                        durations.append(duration * 1.5)  # Adjust duration for skipped frames
                        
                        frame_count += 1
                    
                    # Save optimized GIF with aggressive compression
                    optimized_path = os.path.join(temp_dir, "optimized.gif")
                    frames[0].save(
                        optimized_path,
                        save_all=True,
                        append_images=frames[1:],
                        duration=durations,
                        loop=0,
                        optimize=True,
                        quality=20  # Lower quality for smaller file size
                    )
                    
                    picture_path = optimized_path
                    
                except Exception as e:
                    # Fall back to original if optimization fails
                    picture_path = original_path
            else:
                # Optimize static images (PNG, JPG, BMP)
                try:
                    img = Image.open(original_path)
                    
                    # Aggressive resize for bandwidth optimization
                    if img.width > MAX_IMAGE_SIZE or img.height > MAX_IMAGE_SIZE:
                        img.thumbnail((MAX_IMAGE_SIZE, MAX_IMAGE_SIZE), Image.Resampling.BILINEAR)  # Faster than LANCZOS
                    
                    # Convert to RGB if needed
                    if img.mode in ('RGBA', 'LA', 'P'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                        img = background
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Save as JPEG with aggressive compression for bandwidth savings
                    optimized_path = os.path.join(temp_dir, "optimized.jpg")
                    img.save(optimized_path, 'JPEG', quality=JPEG_QUALITY, optimize=True)
                    picture_path = optimized_path
                    
                except Exception as e:
                    # Fall back to original if optimization fails
                    picture_path = original_path
        
        # Determine output file name and format
        safe_name = "qr"  # Simplified filename to reduce processing
        if picture and picture.filename.lower().endswith('.gif'):
            save_name = f"{safe_name}.gif"
        else:
            save_name = f"{safe_name}.png"
        
        # Generate the QR code
        version_out, level_out, qr_name = amzqr.run(
            words=words,
            version=version,
            level=level,
            picture=picture_path,
            colorized=colorized,
            contrast=contrast,
            brightness=brightness,
            save_name=save_name,
            save_dir=temp_dir,
        )
        
        output_file = os.path.join(temp_dir, qr_name)
        
        if not os.path.exists(output_file):
            raise HTTPException(status_code=500, detail="Failed")
        
        # Read and optimize output file
        with open(output_file, "rb") as f:
            qr_data = f.read()
        
        # Further optimize PNG output for bandwidth savings
        if qr_name.endswith('.png'):
            try:
                img = Image.open(output_file)
                # Reduce colors for smaller file size
                img = img.convert('P', palette=Image.ADAPTIVE, colors=128)
                buffer = BytesIO()
                img.save(buffer, 'PNG', optimize=True)
                qr_data = buffer.getvalue()
            except:
                pass  # Use original if optimization fails
        
        # Determine media type
        media_type = "image/gif" if qr_name.endswith('.gif') else "image/png"
        
        # Return as streaming response with cache headers for bandwidth optimization
        return StreamingResponse(
            BytesIO(qr_data),
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{qr_name}"',
                "Cache-Control": "public, max-age=86400",  # Cache for 24 hours
                "Content-Length": str(len(qr_data))
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Generation failed")
    finally:
        # Clean up temp directory immediately
        try:
            import shutil
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        except:
            pass  # Ignore cleanup errors to save execution time



# Appwrite Function entry point
# Appwrite Function entry point
def main(context):
    """
    Appwrite Function entry point
    Routes requests to the FastAPI app
    """
    import json
    try:
        from fastapi.testclient import TestClient
        
        # Get request details
        method = context.req.method
        path = context.req.path or "/"
        headers = dict(context.req.headers) if hasattr(context.req, 'headers') else {}
        
        # Get body - prioritize binary for file uploads
        body = b""
        
        # Try body_binary first (raw bytes - best for multipart/form-data)
        if hasattr(context.req, 'body_binary'):
            body = context.req.body_binary
            context.log("Using body_binary")
        # Try bodyBinary (camelCase variant)
        elif hasattr(context.req, 'bodyBinary'):
            body = context.req.bodyBinary
            context.log("Using bodyBinary")
        # Try body_raw (raw bytes - deprecated but might exist)
        elif hasattr(context.req, 'body_raw'):
            body = context.req.body_raw
            context.log("Using body_raw")
        elif hasattr(context.req, 'bodyRaw'):
            body = context.req.bodyRaw
            context.log("Using bodyRaw")
        # Only use text/json variants if binary not available
        elif hasattr(context.req, 'body_text') and context.req.body_text:
            body = context.req.body_text.encode('utf-8')
            context.log("Using body_text")
        elif hasattr(context.req, 'bodyText') and context.req.bodyText:
            body = context.req.bodyText.encode('utf-8')
            context.log("Using bodyText")
        elif hasattr(context.req, 'body_json') and context.req.body_json:
            body = json.dumps(context.req.body_json).encode('utf-8')
            context.log("Using body_json")
        elif hasattr(context.req, 'bodyJson') and context.req.bodyJson:
            body = json.dumps(context.req.bodyJson).encode('utf-8')
            context.log("Using bodyJson")
        # Avoid using 'body' directly as it might try to decode binary as UTF-8
        # Only use as last resort
        elif hasattr(context.req, 'body'):
            try:
                # Try to use it as-is if it's already bytes
                if isinstance(context.req.body, bytes):
                    body = context.req.body
                    context.log("Using body (bytes)")
                elif isinstance(context.req.body, str):
                    body = context.req.body.encode('utf-8')
                    context.log("Using body (string)")
                else:
                    # Unknown type, try to convert
                    body = str(context.req.body).encode('utf-8')
                    context.log("Using body (converted)")
            except Exception as body_err:
                context.error(f"Error accessing body: {body_err}")
                body = b""
        
        
        
        # Reduced logging for faster execution
        if path != "/health":
            context.log(f"{method} {path}")
        
        # Handle CORS preflight OPTIONS requests
        if method == 'OPTIONS':
            origin = headers.get('origin', '')
            allowed_origin = 'https://qrcartoon.com'
            
            # Allow localhost for development
            if origin in ['https://qrcartoon.com', 'https://www.qrcartoon.com'] or \
               origin.startswith('http://localhost') or \
               origin.startswith('http://127.0.0.1'):
                allowed_origin = origin
                
            return context.res.empty(
                200,
                {
                    'Access-Control-Allow-Origin': allowed_origin,
                    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-API-Key, x-api-key',
                    'Access-Control-Max-Age': '3600',
                    'Vary': 'Origin'
                }
            )
        
        # Create test client to call FastAPI app
        client = TestClient(app)
        
        # Prepare kwargs for the request
        kwargs = {}
        
        # Forward headers 
        # Filter out headers that might cause issues with internal routing
        blocked_headers = {'host', 'content-length', 'connection'} 
        req_headers = {k: v for k, v in headers.items() if k.lower() not in blocked_headers}
        kwargs['headers'] = req_headers
        kwargs['content'] = body
        
        # Call the FastAPI endpoint
        try:
            response = client.request(method, path, **kwargs)
        except Exception as route_err:
            # If explicit routing failed, try to handle simple cases manually or return error
            context.error(f"Routing error: {route_err}")
            raise
            
        # Handle the response
        content_type = response.headers.get('content-type', '')
        
        # CORS headers - restricted to qrcartoon.com domains and localhost
        origin = headers.get('origin', '')
        allowed_origin = 'https://qrcartoon.com'
        if origin in ['https://qrcartoon.com', 'https://www.qrcartoon.com'] or \
           origin.startswith('http://localhost') or \
           origin.startswith('http://127.0.0.1'):
            allowed_origin = origin
        
        cors_headers = {
            'Access-Control-Allow-Origin': allowed_origin,
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-API-Key, x-api-key',
            'Access-Control-Max-Age': '3600',
            'Vary': 'Origin',
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block'
        }
        
        # Binary response (Images) - check both header and content
        # FastAPI StreamingResponse should have image/* content-type
        is_image = 'image/' in content_type or 'application/octet-stream' in content_type
        
        # Also check if content looks like an image (PNG/GIF/JPEG magic bytes)
        if not is_image and len(response.content) > 4:
            # Check for image magic bytes
            magic = response.content[:4]
            if magic[:3] == b'\x89PNG' or magic[:3] == b'GIF' or magic[:2] == b'\xff\xd8':
                is_image = True
                # Fix content-type if it's wrong
                if 'image/' not in content_type:
                    if magic[:3] == b'\x89PNG':
                        content_type = 'image/png'
                    elif magic[:3] == b'GIF':
                        content_type = 'image/gif'
                    elif magic[:2] == b'\xff\xd8':
                        content_type = 'image/jpeg'
        
        if is_image:
            # Use send() instead of binary() to properly set headers
            headers = {**cors_headers, 'Content-Type': content_type}
            return context.res.send(
                response.content,
                response.status_code,
                headers
            )
            
        # JSON response
        elif 'application/json' in content_type:
            try:
                json_data = response.json()
                headers = {**cors_headers, **dict(response.headers)}
                return context.res.json(json_data, response.status_code, headers)
            except:
                # Fallback if json parse fails
                headers = {**cors_headers, **dict(response.headers)}
                return context.res.text(response.text, response.status_code, headers)
                
        # Text/HTML/Other response
        else:
            headers = {**cors_headers, **dict(response.headers)}
            return context.res.text(
                response.text, 
                response.status_code, 
                headers
            )
        
    except Exception as e:
        context.error(f"Error in Appwrite function: {e}")
        return context.res.json({
            "error": str(e),
            "message": "Error in QR microservice",
            "type": type(e).__name__,
            "req_keys": dir(context.req) if hasattr(context, 'req') else []
        }, 500)


