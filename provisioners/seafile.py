import secrets
import string
import time
from pathlib import Path
from ssh_utils import create_ssh_client, exec_command_with_output, check_container_running

def generate_password(length=16):
    """Generate secure random password"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def setup_seafile(ip, username, password, custom_domain=None, job_id=None):
    """Install Seafile - File sync and share platform"""
    
    print(f"📦 Setting up Seafile on {ip}...")
    
    # Read installation script
    script_path = Path(__file__).parent.parent / 'templates' / 'seafile_install.sh'
    with open(script_path, 'r') as f:
        install_script = f.read()
    
    # Generate credentials
    admin_email = "admin@seafile.local"
    admin_password = generate_password()
    db_password = generate_password(24)
    
    # Replace variables
    install_script = install_script.replace('{{ADMIN_EMAIL}}', admin_email)
    install_script = install_script.replace('{{ADMIN_PASSWORD}}', admin_password)
    install_script = install_script.replace('{{DB_PASSWORD}}', db_password)
    install_script = install_script.replace('{{SERVER_IP}}', ip)
    install_script = install_script.replace('{{DOMAIN}}', custom_domain or f'http://{ip}')
    
    # Connect SSH
    ssh = create_ssh_client(ip, username, password)
    
    try:
        # Check if already installed
        if check_container_running(ssh, 'seafile'):
            print("✅ Seafile already running")
            
            # Try to get existing credentials
            stdin, stdout, stderr = ssh.exec_command('cat /opt/seafile/credentials.txt 2>/dev/null')
            creds = stdout.read().decode().strip()
            
            url = f"https://{custom_domain}" if custom_domain else f"http://{ip}:8000"
            
            if creds:
                lines = creds.split('\n')
                existing_email = lines[0] if len(lines) > 0 else admin_email
                existing_password = lines[1] if len(lines) > 1 else "check /opt/seafile/credentials.txt"
            else:
                existing_email = admin_email
                existing_password = "check /opt/seafile/credentials.txt"
            
            return {
                "status": "success",
                "app": "seafile",
                "url": url,
                "credentials": {
                    "email": existing_email,
                    "password": existing_password
                },
                "notes": "Seafile was already installed and running",
                "mobile_apps": {
                    "ios": "https://apps.apple.com/app/seafile-pro/id639202512",
                    "android": "https://play.google.com/store/apps/details?id=com.seafile.seadroid2"
                }
            }
        
        print("📤 Uploading installation script...")
        
        create_script_cmd = f"""cat > /root/install_seafile.sh << 'EOFSCRIPT'
{install_script}
EOFSCRIPT
chmod +x /root/install_seafile.sh
"""
        
        stdin, stdout, stderr = ssh.exec_command(create_script_cmd)
        stdout.channel.recv_exit_status()
        
        print("⚙️  Running installation (10-15 minutes)...")
        print("   Installing: Seafile + MariaDB + Memcached")
        
        # Run installation with extended timeout
        exit_code, output_lines = exec_command_with_output(
            ssh,
            'bash /root/install_seafile.sh 2>&1',
            timeout=1200  # 20 minutes for Seafile
        )
        
        # Save logs
        log_file = Path(f'/tmp/seafile_install_{ip.replace(".", "_")}.log')
        with open(log_file, 'w') as f:
            f.write("\n".join(output_lines))
            f.write(f"\n\nExit status: {exit_code}")
        
        print(f"📝 Logs saved: {log_file}")
        
        if exit_code != 0:
            stdin, stdout, stderr = ssh.exec_command('docker ps -a 2>&1')
            docker_status = stdout.read().decode()
            
            raise Exception(f"""Seafile installation failed!

Exit code: {exit_code}

Last 30 lines:
{chr(10).join(output_lines[-30:])}

Docker status:
{docker_status}

Full logs: {log_file}
""")
        
        # Verify running
        print("🔍 Verifying Seafile services...")
        
        # Check all services
        stdin, stdout, stderr = ssh.exec_command('cd /opt/seafile && docker compose ps 2>&1')
        compose_status = stdout.read().decode()
        print(f"Services status:\n{compose_status}")
        
        if not check_container_running(ssh, 'seafile'):
            raise Exception(f"Seafile container not running!\n\nStatus:\n{compose_status}")
        
        # Wait for Seafile to be ready
        print("⏳ Waiting for Seafile to start (this can take 2-3 minutes)...")
        time.sleep(90)
        
        # Check HTTP
        stdin, stdout, stderr = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost:8000')
        http_code = stdout.read().decode().strip()
        
        print(f"🌐 Seafile HTTP status: {http_code}")
        
        # Format URL
        url = f"https://{custom_domain}" if custom_domain else f"http://{ip}:8000"
        
        print(f"✅ Seafile installed successfully!")
        print(f"   URL: {url}")
        print(f"   Email: {admin_email}")
        print(f"   Password: {admin_password}")
        
        return {
            "status": "success",
            "app": "seafile",
            "url": url,
            "credentials": {
                "email": admin_email,
                "password": admin_password
            },
            "notes": "Seafile is ready! Download mobile apps for auto photo upload.",
            "features": [
                "File sync and share",
                "Auto photo upload from mobile",
                "Version control",
                "File sharing with links",
                "Offline access",
                "Cross-platform: Windows, Mac, Linux, iOS, Android"
            ],
            "mobile_apps": {
                "ios": "https://apps.apple.com/app/seafile-pro/id639202512",
                "android": "https://play.google.com/store/apps/details?id=com.seafile.seadroid2",
                "note": "Both apps are FREE"
            },
            "next_steps": [
                "1. Login to web interface",
                "2. Download mobile app (iOS or Android)",
                "3. Add account in app using server URL",
                "4. Enable auto photo upload in app settings",
                "5. Your photos will automatically sync to server!"
            ],
            "installation_log": str(log_file)
        }
    
    finally:
        ssh.close()
