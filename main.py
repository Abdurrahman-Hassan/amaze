"""
QR Code Microservice for Appwrite Functions
Generates static, artistic, and animated GIF QR codes
"""

import os
import logging
from fastapi import FastAPI, Form, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from amzqr import amzqr
from typing import Optional
from PIL import Image
from io import BytesIO
import tempfile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Maximum file size: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024

app = FastAPI(
    title="QR Code Microservice",
    description="Generate artistic and animated QR codes using amazing-qr",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this based on your needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {"status": "healthy", "service": "qr-microservice"}

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
    
    # Validate error correction level
    if level not in ['L', 'M', 'Q', 'H']:
        raise HTTPException(status_code=400, detail="Level must be one of: L, M, Q, H")
    
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
            
            logger.info(f"Uploaded file: {picture.filename}, size: {len(contents)} bytes")
            
            # Convert unsupported formats to PNG/GIF
            # amzqr supports: .jpg, .png, .bmp, .gif
            file_ext = os.path.splitext(picture.filename)[1].lower()
            supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.gif']
            
            # Optimize image before processing
            is_gif = file_ext == '.gif'
            
            if file_ext not in supported_formats:
                logger.info(f"Converting {file_ext} to PNG for compatibility")
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
                    
                    # Optimize size - resize to optimal dimensions
                    max_size = 600  # Reduced from 800 for faster processing
                    if img.width > max_size or img.height > max_size:
                        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                        logger.info(f"Resized image to {img.size}")
                    
                    # Save as PNG
                    converted_path = os.path.join(temp_dir, "converted_image.png")
                    img.save(converted_path, 'PNG', optimize=True)
                    picture_path = converted_path
                    logger.info(f"Successfully converted and optimized to PNG")
                except Exception as e:
                    logger.error(f"Error converting image: {e}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unable to process image format {file_ext}. Supported: JPG, PNG, BMP, GIF, WebP"
                    )
            elif is_gif:
                # Optimize GIF - reduce frames and resize for faster processing
                logger.info("Optimizing GIF for faster processing...")
                try:
                    from PIL import ImageSequence
                    
                    gif = Image.open(original_path)
                    frames = []
                    durations = []
                    
                    # Optimal size for GIF QR codes
                    max_gif_size = 600
                    
                    # Extract and optimize frames
                    frame_count = 0
                    max_frames = 50  # Limit frames for performance
                    
                    for i, frame in enumerate(ImageSequence.Iterator(gif)):
                        if i >= max_frames:
                            logger.info(f"Limited GIF to {max_frames} frames for performance")
                            break
                        
                        # Convert frame to RGB
                        frame_rgb = frame.convert('RGB')
                        
                        # Resize if too large
                        if frame_rgb.width > max_gif_size or frame_rgb.height > max_gif_size:
                            frame_rgb.thumbnail((max_gif_size, max_gif_size), Image.Resampling.LANCZOS)
                        
                        frames.append(frame_rgb)
                        
                        # Get frame duration
                        try:
                            duration = frame.info.get('duration', 100)
                        except:
                            duration = 100
                        durations.append(duration)
                        
                        frame_count += 1
                    
                    # Save optimized GIF
                    optimized_path = os.path.join(temp_dir, "optimized.gif")
                    frames[0].save(
                        optimized_path,
                        save_all=True,
                        append_images=frames[1:],
                        duration=durations,
                        loop=0,
                        optimize=True
                    )
                    
                    picture_path = optimized_path
                    logger.info(f"GIF optimized: {frame_count} frames, size: {frames[0].size}")
                    
                except Exception as e:
                    logger.error(f"Error optimizing GIF: {e}")
                    # Fall back to original if optimization fails
                    picture_path = original_path
                    logger.warning("Using original GIF without optimization")
            else:
                # Optimize static images (PNG, JPG, BMP)
                logger.info("Optimizing static image...")
                try:
                    img = Image.open(original_path)
                    
                    # Optimal size for static QR codes - reduced for speed
                    max_size = 600  # Reduced from 800 for faster processing
                    
                    if img.width > max_size or img.height > max_size:
                        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                        logger.info(f"Resized image from original to {img.size}")
                    
                    # Convert to RGB if needed
                    if img.mode in ('RGBA', 'LA', 'P'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                        img = background
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Save optimized version with lower quality for speed
                    optimized_path = os.path.join(temp_dir, f"optimized{file_ext}")
                    img.save(optimized_path, quality=75, optimize=True)  # Reduced quality from 85 to 75
                    picture_path = optimized_path
                    logger.info(f"Image optimized successfully")
                    
                except Exception as e:
                    logger.error(f"Error optimizing image: {e}")
                    # Fall back to original if optimization fails
                    picture_path = original_path
                    logger.warning("Using original image without optimization")
        
        # Determine output file name and format
        safe_name = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in words[:50])
        if picture and picture.filename.lower().endswith('.gif'):
            save_name = f"{safe_name}.gif"
        else:
            save_name = f"{safe_name}.png"
        
        logger.info(f"Generating QR code: {save_name}")
        
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
            raise HTTPException(status_code=500, detail="QR code generation failed")
        
        logger.info(f"QR code generated successfully: {qr_name}")
        
        # Read file into memory
        with open(output_file, "rb") as f:
            qr_data = f.read()
        
        # Determine media type
        media_type = "image/gif" if qr_name.endswith('.gif') else "image/png"
        
        # Return as streaming response with in-memory data
        return StreamingResponse(
            BytesIO(qr_data),
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{qr_name}"'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating QR code: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"QR code generation error: {str(e)}")
    finally:
        # Clean up temp directory immediately
        try:
            import shutil
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temp directory: {temp_dir}")
        except Exception as e:
            logger.error(f"Error cleaning up temp files: {e}")



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
        
        
        context.log(f"Appwrite request: {method} {path}")
        
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
        
        # Binary response (Images)
        if response.status_code == 200 and ('image/' in content_type or 'application/octet-stream' in content_type):
            return context.res.binary(
                response.content,
                response.status_code,
                {'Content-Type': content_type}
            )
            
        # JSON response
        elif 'application/json' in content_type:
            try:
                json_data = response.json()
                return context.res.json(json_data, response.status_code, dict(response.headers))
            except:
                # Fallback if json parse fails
                return context.res.text(response.text, response.status_code, dict(response.headers))
                
        # Text/HTML/Other response
        else:
            return context.res.text(
                response.text, 
                response.status_code, 
                dict(response.headers)
            )
        
    except Exception as e:
        context.error(f"Error in Appwrite function: {e}")
        return context.res.json({
            "error": str(e),
            "message": "Error in QR microservice",
            "type": type(e).__name__,
            "req_keys": dir(context.req) if hasattr(context, 'req') else []
        }, 500)


