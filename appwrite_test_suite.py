"""
Test script for deployed Appwrite QR microservice
Tests multiple scenarios with different parameters
"""

import requests
import os
from pathlib import Path

# Appwrite deployment URL
BASE_URL = "https://694fc500001210ea5496.fra.appwrite.run"

def test_health_check():
    """Test 1: Health check endpoint"""
    print("\n" + "="*60)
    print("TEST 1: Health Check")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Health check PASSED")
            return True
        else:
            print("❌ Health check FAILED")
            return False
    except Exception as e:
        print(f"❌ Health check ERROR: {e}")
        return False

def test_simple_qr():
    """Test 2: Simple QR code without image"""
    print("\n" + "="*60)
    print("TEST 2: Simple QR Code (text only)")
    print("="*60)
    
    try:
        data = {
            'words': 'https://github.com/appwrite',
            'version': '1',
            'level': 'H'
        }
        
        print(f"Sending data: {data}")
        response = requests.post(f"{BASE_URL}/qr", data=data, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        print(f"Content-Length: {len(response.content)} bytes")
        
        if response.status_code == 200 and 'image/' in response.headers.get('content-type', ''):
            # Save the QR code
            output_file = "test_simple_qr.png"
            with open(output_file, 'wb') as f:
                f.write(response.content)
            print(f"✅ Simple QR code PASSED - Saved to {output_file}")
            return True
        else:
            print(f"❌ Simple QR code FAILED")
            print(f"Response: {response.text[:500]}")
            return False
    except Exception as e:
        print(f"❌ Simple QR code ERROR: {e}")
        return False

def test_qr_with_image():
    """Test 3: QR code with background image"""
    print("\n" + "="*60)
    print("TEST 3: QR Code with Background Image")
    print("="*60)
    
    try:
        # Create a simple test image if it doesn't exist
        test_image_path = "test_background.png"
        
        if not os.path.exists(test_image_path):
            print("Creating test image...")
            from PIL import Image
            img = Image.new('RGB', (300, 300), color=(73, 109, 137))
            img.save(test_image_path)
            print(f"Test image created: {test_image_path}")
        
        data = {
            'words': 'https://appwrite.io',
            'version': '1',
            'level': 'H',
            'colorized': 'true',
            'contrast': '1.0',
            'brightness': '1.0'
        }
        
        files = {
            'picture': ('background.png', open(test_image_path, 'rb'), 'image/png')
        }
        
        print(f"Sending data: {data}")
        print(f"Sending file: {test_image_path}")
        
        response = requests.post(f"{BASE_URL}/qr", data=data, files=files, timeout=60)
        
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        print(f"Content-Length: {len(response.content)} bytes")
        
        if response.status_code == 200 and 'image/' in response.headers.get('content-type', ''):
            # Save the QR code
            output_file = "test_qr_with_image.png"
            with open(output_file, 'wb') as f:
                f.write(response.content)
            print(f"✅ QR with image PASSED - Saved to {output_file}")
            return True
        else:
            print(f"❌ QR with image FAILED")
            print(f"Response: {response.text[:500]}")
            return False
    except Exception as e:
        print(f"❌ QR with image ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_qr_with_gif():
    """Test 4: QR code with animated GIF"""
    print("\n" + "="*60)
    print("TEST 4: QR Code with Animated GIF")
    print("="*60)
    
    try:
        # Create a simple test GIF if it doesn't exist
        test_gif_path = "test_animation.gif"
        
        if not os.path.exists(test_gif_path):
            print("Creating test GIF...")
            from PIL import Image
            
            frames = []
            colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
            for color in colors:
                img = Image.new('RGB', (200, 200), color=color)
                frames.append(img)
            
            frames[0].save(
                test_gif_path,
                save_all=True,
                append_images=frames[1:],
                duration=200,
                loop=0
            )
            print(f"Test GIF created: {test_gif_path}")
        
        data = {
            'words': 'https://github.com',
            'version': '1',
            'level': 'H',
            'colorized': 'true'
        }
        
        files = {
            'picture': ('animation.gif', open(test_gif_path, 'rb'), 'image/gif')
        }
        
        print(f"Sending data: {data}")
        print(f"Sending file: {test_gif_path}")
        
        response = requests.post(f"{BASE_URL}/qr", data=data, files=files, timeout=90)
        
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        print(f"Content-Length: {len(response.content)} bytes")
        
        if response.status_code == 200 and 'image/' in response.headers.get('content-type', ''):
            # Save the QR code
            output_file = "test_qr_with_gif.gif"
            with open(output_file, 'wb') as f:
                f.write(response.content)
            print(f"✅ QR with GIF PASSED - Saved to {output_file}")
            return True
        else:
            print(f"❌ QR with GIF FAILED")
            print(f"Response: {response.text[:500]}")
            return False
    except Exception as e:
        print(f"❌ QR with GIF ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_different_error_levels():
    """Test 5: Different error correction levels"""
    print("\n" + "="*60)
    print("TEST 5: Different Error Correction Levels")
    print("="*60)
    
    levels = ['L', 'M', 'Q', 'H']
    results = []
    
    for level in levels:
        try:
            data = {
                'words': f'Testing level {level}',
                'version': '1',
                'level': level
            }
            
            print(f"\nTesting level {level}...")
            response = requests.post(f"{BASE_URL}/qr", data=data, timeout=30)
            
            if response.status_code == 200 and 'image/' in response.headers.get('content-type', ''):
                output_file = f"test_qr_level_{level}.png"
                with open(output_file, 'wb') as f:
                    f.write(response.content)
                print(f"  ✅ Level {level} PASSED - {len(response.content)} bytes")
                results.append(True)
            else:
                print(f"  ❌ Level {level} FAILED - Status: {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"  ❌ Level {level} ERROR: {e}")
            results.append(False)
    
    if all(results):
        print("\n✅ All error correction levels PASSED")
        return True
    else:
        print(f"\n❌ Some error correction levels FAILED ({sum(results)}/{len(results)} passed)")
        return False

def test_long_text():
    """Test 6: QR code with long text"""
    print("\n" + "="*60)
    print("TEST 6: QR Code with Long Text")
    print("="*60)
    
    try:
        long_text = "https://example.com/very/long/path/with/many/segments/and/parameters?param1=value1&param2=value2&param3=value3"
        
        data = {
            'words': long_text,
            'version': '5',  # Higher version for more data
            'level': 'M'
        }
        
        print(f"Text length: {len(long_text)} characters")
        response = requests.post(f"{BASE_URL}/qr", data=data, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        
        if response.status_code == 200 and 'image/' in response.headers.get('content-type', ''):
            output_file = "test_qr_long_text.png"
            with open(output_file, 'wb') as f:
                f.write(response.content)
            print(f"✅ Long text QR PASSED - Saved to {output_file}")
            return True
        else:
            print(f"❌ Long text QR FAILED")
            print(f"Response: {response.text[:500]}")
            return False
    except Exception as e:
        print(f"❌ Long text QR ERROR: {e}")
        return False

def test_invalid_endpoint():
    """Test 7: Invalid endpoint (should return 404)"""
    print("\n" + "="*60)
    print("TEST 7: Invalid Endpoint (Error Handling)")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/invalid-endpoint", timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 404:
            print(f"Response: {response.json()}")
            print("✅ Error handling PASSED (404 returned as expected)")
            return True
        else:
            print(f"❌ Error handling FAILED (expected 404, got {response.status_code})")
            return False
    except Exception as e:
        print(f"❌ Error handling test ERROR: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "🚀"*30)
    print("APPWRITE QR MICROSERVICE TEST SUITE")
    print(f"Testing deployment at: {BASE_URL}")
    print("🚀"*30)
    
    tests = [
        ("Health Check", test_health_check),
        ("Simple QR Code", test_simple_qr),
        ("QR with Image", test_qr_with_image),
        ("QR with GIF", test_qr_with_gif),
        ("Error Correction Levels", test_different_error_levels),
        ("Long Text QR", test_long_text),
        ("Error Handling", test_invalid_endpoint),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:.<40} {status}")
    
    print("="*60)
    print(f"Total: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print("="*60)
    
    if passed == total:
        print("\n🎉 All tests PASSED! Your Appwrite deployment is working perfectly!")
    elif passed > 0:
        print(f"\n⚠️  Some tests failed. Please review the output above.")
    else:
        print(f"\n❌ All tests failed. There may be a deployment issue.")

if __name__ == "__main__":
    main()
