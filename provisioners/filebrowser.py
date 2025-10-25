import secrets
import string
import time
from pathlib import Path
from ssh_utils import create_ssh_client, exec_command_with_output, check_container_running

def generate_password(length=16):
    """Generate secure random password"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def setup_filebrowser(ip, username, password, custom_domain=None, job_id=None):
    """Install FileBrowser - Lightweight file manager"""
    
    print(f"📦 Setting up FileBrowser on {ip}...")
    
    # Read installation script
    script_path = Path(__file__).parent.parent / 'templates' / 'filebrowser_install.sh'
    with open(script_path, 'r') as f:
        install_script = f.read()
    
    # Generate credentials
    admin_password = generate_password()
    
    # Replace variables
    install_script = install_script.replace('{{ADMIN_PASSWORD}}', admin_password)
    
    # Connect SSH
    ssh = create_ssh_client(ip, username, password)
    
    try:
        # Check if already installed
        if check_container_running(ssh, 'filebrowser'):
            print("✅ FileBrowser already running")
            
            # Try to get existing password
            stdin, stdout, stderr = ssh.exec_command('cat /opt/filebrowser/admin_password.txt 2>/dev/null')
            existing_password = stdout.read().decode().strip()
            
            url = f"https://{custom_domain}" if custom_domain else f"http://{ip}:8081"
            
            return {
                "status": "success",
                "app": "filebrowser",
                "url": url,
                "credentials": {
                    "username": "admin",
                    "password": existing_password or "check /opt/filebrowser/admin_password.txt"
                },
                "notes": "FileBrowser was already installed"
            }
        
        print("📤 Uploading installation script...")
        
        create_script_cmd = f"""cat > /root/install_filebrowser.sh << 'EOFSCRIPT'
{install_script}
EOFSCRIPT
chmod +x /root/install_filebrowser.sh
"""
        
        stdin, stdout, stderr = ssh.exec_command(create_script_cmd)
        stdout.channel.recv_exit_status()
        
        print("⚙️  Running installation (3-5 minutes)...")
        
        # Run installation
        exit_code, output_lines = exec_command_with_output(
            ssh,
            'bash /root/install_filebrowser.sh 2>&1'
        )
        
        # Save logs
        log_file = Path(f'/tmp/filebrowser_install_{ip.replace(".", "_")}.log')
        with open(log_file, 'w') as f:
            f.write("\n".join(output_lines))
            f.write(f"\n\nExit status: {exit_code}")
        
        print(f"📝 Logs saved: {log_file}")
        
        if exit_code != 0:
            raise Exception(f"""FileBrowser installation failed!

Exit code: {exit_code}

Last 20 lines:
{chr(10).join(output_lines[-20:])}

Full logs: {log_file}
""")
        
        # Verify running
        print("🔍 Verifying FileBrowser is running...")
        
        if not check_container_running(ssh, 'filebrowser'):
            raise Exception("FileBrowser container not running!")
        
        # Wait for service
        print("⏳ Waiting for FileBrowser to start...")
        time.sleep(5)
        
        # Check HTTP
        stdin, stdout, stderr = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost:8081')
        http_code = stdout.read().decode().strip()
        
        print(f"🌐 FileBrowser HTTP status: {http_code}")
        
        # Format URL
        url = f"https://{custom_domain}" if custom_domain else f"http://{ip}:8081"
        
        print(f"✅ FileBrowser installed successfully!")
        print(f"   URL: {url}")
        print(f"   Username: admin")
        print(f"   Password: {admin_password}")
        
        return {
            "status": "success",
            "app": "filebrowser",
            "url": url,
            "credentials": {
                "username": "admin",
                "password": admin_password
            },
            "storage_path": "/srv",
            "notes": "FileBrowser is ready! Upload, manage, and share files.",
            "features": [
                "File upload/download",
                "File sharing with links",
                "User management",
                "Mobile friendly"
            ],
            "installation_log": str(log_file)
        }
    
    finally:
        ssh.close()
