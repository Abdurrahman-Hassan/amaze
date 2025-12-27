# QR Generator Function

A serverless function for generating artistic and animated QR codes.

## Deployment

This function is designed to run on Appwrite Functions.

### Requirements

- Python 3.11
- Timeout: 30 seconds (for GIF support)

### Environment Variables

Optional configuration:
- `MAX_FILE_SIZE`: Maximum upload size in bytes (default: 10485760 = 10MB)
- `MAX_GIF_FRAMES`: Maximum GIF frames (default: 50)

### Endpoints

- `GET /health` - Health check
- `POST /qr` - Generate QR code

### Usage

See main README.md for API documentation.
