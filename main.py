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
def main(context):
    """
    Appwrite Function entry point
    This function is called by Appwrite when the function is executed
    """
    try:
        from mangum import Mangum
        
        # Create Mangum handler to wrap FastAPI for serverless
        handler = Mangum(app, lifespan="off")
        
        # Convert Appwrite context to ASGI event
        event = {
            "httpMethod": context.req.method,
            "path": context.req.path,
            "headers": dict(context.req.headers),
            "body": context.req.body,
            "isBase64Encoded": False,
        }
        
        # Call the handler
        response = handler(event, {})
        
        # Return response
        return context.res.send(
            response.get("body", ""),
            response.get("statusCode", 200),
            response.get("headers", {})
        )
        
    except ImportError:
        # Mangum not available, return simple response
        logger.warning("Mangum not installed, returning basic response")
        return context.res.json({
            "message": "QR Generator is running!",
            "note": "Install 'mangum' for full FastAPI support",
            "endpoints": {
                "health": "/health",
                "generate": "/qr"
            }
        })
    except Exception as e:
        logger.error(f"Error in Appwrite function: {e}", exc_info=True)
        return context.res.json({
            "error": str(e)
        }, 500)
