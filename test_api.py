#!/usr/bin/env python3
"""
Test script for VPS Provisioner API
"""

import requests
import time
import sys

# Configuration
API_URL = "http://localhost:5001"
API_KEY = "CHANGE-ME-IN-PRODUCTION-XkP9mL2vQ8"  # Default dev key

def test_health():
    """Test health endpoint"""
    print("🏥 Testing health endpoint...")
    response = requests.get(f"{API_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_provision(ip, username, password, app):
    """Test provisioning"""
    print(f"🚀 Testing provision: {app} on {ip}...")
    
    response = requests.post(
        f"{API_URL}/provision",
        headers={
            "X-API-Key": API_KEY,
            "Content-Type": "application/json"
        },
        json={
            "ip_address": ip,
            "username": username,
            "password": password,
            "app": app
        }
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code != 202:
        print(f"Error: {response.json()}")
        return None
    
    data = response.json()
    job_id = data["job_id"]
    print(f"Job ID: {job_id}")
    print(f"Status URL: {data['status_url']}")
    print()
    
    return job_id

def poll_status(job_id, timeout=1800):
    """Poll job status until complete"""
    print(f"📊 Polling status for job {job_id}...")
    print()
    
    start_time = time.time()
    last_progress = -1
    
    while True:
        # Check timeout
        if time.time() - start_time > timeout:
            print("❌ Timeout reached!")
            return None
        
        # Get status
        response = requests.get(f"{API_URL}/status/{job_id}")
        
        if response.status_code != 200:
            print(f"Error getting status: {response.status_code}")
            return None
        
        status = response.json()
        
        # Print progress if changed
        current_progress = status.get('progress', 0)
        if current_progress != last_progress:
            print(f"[{current_progress}%] {status.get('message', '')}")
            last_progress = current_progress
        
        # Check if complete
        if status['status'] in ['completed', 'failed']:
            print()
            return status
        
        time.sleep(10)

def main():
    """Main test function"""
    
    if len(sys.argv) < 5:
        print("Usage: python test_api.py <ip> <username> <password> <app>")
        print()
        print("Example:")
        print("  python test_api.py 95.179.200.45 root mypassword n8n")
        print()
        print("Supported apps: n8n, wireguard, outline, vaultwarden, 3x-ui, filebrowser")
        sys.exit(1)
    
    ip = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]
    app = sys.argv[4]
    
    print("=" * 60)
    print("VPS PROVISIONER TEST")
    print("=" * 60)
    print()
    
    # Test health
    test_health()
    
    # Start provisioning
    job_id = test_provision(ip, username, password, app)
    
    if not job_id:
        print("❌ Failed to start provisioning")
        sys.exit(1)
    
    # Poll status
    result = poll_status(job_id)
    
    if not result:
        print("❌ Failed to get result")
        sys.exit(1)
    
    # Print result
    print("=" * 60)
    if result['status'] == 'completed':
        print("✅ PROVISIONING SUCCESSFUL!")
        print("=" * 60)
        print()
        
        app_result = result.get('result', {})
        print(f"App: {app_result.get('app')}")
        print(f"URL: {app_result.get('url')}")
        print()
        print("Credentials:")
        for key, value in app_result.get('credentials', {}).items():
            print(f"  {key}: {value}")
        print()
        print(f"Notes: {app_result.get('notes')}")
        
        if 'next_steps' in app_result:
            print()
            print("Next steps:")
            for step in app_result['next_steps']:
                print(f"  {step}")
    else:
        print("❌ PROVISIONING FAILED")
        print("=" * 60)
        print()
        print(f"Error: {result.get('error')}")
    
    print()

if __name__ == "__main__":
    main()
