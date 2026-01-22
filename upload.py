#!/usr/bin/env python3
"""
Upload departures image to display device
"""

import requests
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Device Configuration
DEVICE_URL = os.getenv('DEVICE_URL')
UPLOAD_DIR = os.getenv('UPLOAD_DIR', '/image/')
IMAGE_FILE = "departures.jpg"


def upload_image(image_path=IMAGE_FILE):
    """Upload image to the display device"""

    # Check if image exists
    if not os.path.exists(image_path):
        print(f"Error: Image file '{image_path}' not found")
        return False

    # Prepare the upload
    url = f"{DEVICE_URL}?dir={UPLOAD_DIR}"

    try:
        # Open and upload the file
        with open(image_path, 'rb') as f:
            files = {'file': (os.path.basename(image_path), f, 'image/jpeg')}

            print(f"Uploading {image_path} to {DEVICE_URL}...")
            response = requests.post(
                url, files=files, timeout=10)

            response.raise_for_status()

            print(f"Upload successful! Status: {response.status_code}")
            if response.text:
                print(f"Response: {response.text}")

            return True

    except requests.exceptions.RequestException as e:
        print(f"Upload failed: {e}")
        return False


def main():
    """Main execution function"""
    image_path = sys.argv[1] if len(sys.argv) > 1 else IMAGE_FILE

    success = upload_image(image_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
