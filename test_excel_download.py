#!/usr/bin/env python3
"""
Test script for Excel match download functionality
"""

import requests
import json
import time
import os

def test_excel_download():
    """Test the Excel match download functionality"""
    
    base_url = "http://localhost:5000"
    
    print("🧪 Testing Excel Match Download Functionality")
    print("=" * 50)
    
    # Step 1: Upload test files
    print("\n1️⃣ Uploading test files...")
    
    test_files = [
        ("Input_Files/Interunit Steel.xlsx", "Sheet7"),
        ("Input_Files/Interunit GeoTex.xlsx", "Sheet8")
    ]
    
    for file_path, sheet_name in test_files:
        if os.path.exists(file_path):
            print(f"   📤 Uploading {file_path} with sheet {sheet_name}")
            
            with open(file_path, 'rb') as f:
                files = {'file': f}
                data = {'sheet_name': sheet_name}
                
                response = requests.post(f"{base_url}/api/upload", files=files, data=data)
                
                if response.status_code == 200:
                    print(f"   ✅ Successfully uploaded {file_path}")
                else:
                    print(f"   ❌ Failed to upload {file_path}: {response.text}")
                    return False
        else:
            print(f"   ⚠️  File not found: {file_path}")
    
    # Step 2: Run reconciliation
    print("\n2️⃣ Running reconciliation...")
    
    response = requests.post(f"{base_url}/api/reconcile", json={})
    
    if response.status_code == 200:
        result = response.json()
        print(f"   ✅ Reconciliation complete: {result.get('matches_found', 0)} matches found")
    else:
        print(f"   ❌ Reconciliation failed: {response.text}")
        return False
    
    # Step 3: Get matches
    print("\n3️⃣ Getting matches...")
    
    response = requests.get(f"{base_url}/api/matches")
    
    if response.status_code == 200:
        result = response.json()
        matches = result.get('matches', [])
        print(f"   ✅ Found {len(matches)} matches")
        
        if len(matches) == 0:
            print("   ⚠️  No matches found - cannot test Excel download")
            return False
    else:
        print(f"   ❌ Failed to get matches: {response.text}")
        return False
    
    # Step 4: Test Excel download
    print("\n4️⃣ Testing Excel download...")
    
    response = requests.get(f"{base_url}/api/download-matches")
    
    if response.status_code == 200:
        # Check if response has content
        if len(response.content) > 0:
            print("   ✅ Excel download successful!")
            print(f"   📊 File size: {len(response.content)} bytes")
            
            # Save the file for inspection
            filename = f"test_matched_transactions_{int(time.time())}.xlsx"
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f"   💾 Saved as: {filename}")
            
            return True
        else:
            print("   ❌ Excel download returned empty file")
            return False
    else:
        print(f"   ❌ Excel download failed: {response.text}")
        return False

if __name__ == "__main__":
    try:
        success = test_excel_download()
        if success:
            print("\n🎉 All tests passed! Excel match download is working correctly.")
        else:
            print("\n❌ Tests failed! Please check the errors above.")
    except requests.exceptions.ConnectionError:
        print("\n❌ Cannot connect to Flask app. Make sure it's running on http://localhost:5000")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}") 