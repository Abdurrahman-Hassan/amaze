"""
Simple Appwrite Function wrapper for QR microservice
This provides a basic entry point that Appwrite can call
"""

def main(context):
    """
    Appwrite Function entry point
    Returns basic info about the QR service
    """
    import json
    
    # Get request details
    method = context.req.method
    path = context.req.path
    
    # Simple routing
    if path == "/health" or path == "/" or not path:
        # Health check
        return context.res.json({
            "status": "healthy",
            "service": "qr-microservice",
            "version": "1.0.0",
            "endpoints": {
                "health": "GET /health",
                "generate_qr": "POST /qr"
            }
        })
    
    elif path == "/qr" and method == "POST":
        # QR generation endpoint
        try:
            # Import the QR generation logic
            from main_logic import generate_qr_code
            
            # Get form data from request
            body = context.req.body
            
            # Parse multipart form data
            # Note: Appwrite handles this differently
            words = body.get('words', 'https://example.com')
            
            # Generate QR code
            qr_data = generate_qr_code(words)
            
            # Return QR code image
            return context.res.send(
                qr_data,
                200,
                {
                    'Content-Type': 'image/png',
                    'Content-Disposition': 'attachment; filename="qrcode.png"'
                }
            )
            
        except Exception as e:
            return context.res.json({
                "error": str(e),
                "message": "Error generating QR code"
            }, 500)
    
    else:
        # Unknown endpoint
        return context.res.json({
            "error": "Not Found",
            "message": f"Endpoint {path} not found",
            "available_endpoints": {
                "health": "GET /health",
                "generate_qr": "POST /qr"
            }
        }, 404)
