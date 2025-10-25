import secrets
import string
import time
from pathlib import Path
from ssh_utils import create_ssh_client, exec_command_with_output, check_container_running

def generate_password(length=16):
    """Generate secure random password"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def setup_3x_ui(ip, username, password, custom_domain=None, job_id=None):
    """Install 3X-UI - Advanced VPN panel (VMess, VLESS, Trojan, Shadowsocks)"""
    
    print(f"📦 Setting up 3X-UI on {ip}...")
    
    # Read installation script
    script_path = Path(__file__).parent.parent / 'templates' / '3x-ui_install.sh'
    with open(script_path, 'r') as f:
        install_script = f.read()
    
    # Generate credentials
    admin_username = "admin"
    admin_password = generate_password()
    
    # Replace variables
    install_script = install_script.replace('{{ADMIN_USERNAME}}', admin_username)
    install_script = install_script.replace('{{ADMIN_PASSWORD}}', admin_password)
    
    # Connect SSH
    ssh = create_ssh_client(ip, username, password)
    
    try:
        # Check if already installed
        stdin, stdout, stderr = ssh.exec_command('systemctl is-active x-ui 2>/dev/null')
        is_running = stdout.read().decode().strip() == 'active'
        
        if is_running:
            print("✅ 3X-UI already running")
            
            # Try to get existing credentials
            stdin, stdout, stderr = ssh.exec_command('cat /opt/3x-ui/credentials.txt 2>/dev/null')
            creds = stdout.read().decode().strip()
            
            url = f"https://{custom_domain}" if custom_domain else f"http://{ip}:54321"
            
            return {
                "status": "success",
                "app": "3x-ui",
                "url": url,
                "credentials": {
                    "username": "admin",
                    "password": creds.split('\n')[1] if creds else "check /opt/3x-ui/credentials.txt"
                },
                "notes": "3X-UI was already installed and running"
            }
        
        print("📤 Uploading installation script...")
        
        create_script_cmd = f"""cat > /root/install_3x_ui.sh << 'EOFSCRIPT'
{install_script}
EOFSCRIPT
chmod +x /root/install_3x_ui.sh
"""
        
        stdin, stdout, stderr = ssh.exec_command(create_script_cmd)
        stdout.channel.recv_exit_status()
        
        print("⚙️  Running installation (5-10 minutes)...")
        print("   Installing: VMess, VLESS, Trojan, Shadowsocks support")
        
        # Run installation
        exit_code, output_lines = exec_command_with_output(
            ssh,
            'bash /root/install_3x_ui.sh 2>&1'
        )
        
        # Save logs
        log_file = Path(f'/tmp/3x-ui_install_{ip.replace(".", "_")}.log')
        with open(log_file, 'w') as f:
            f.write("\n".join(output_lines))
            f.write(f"\n\nExit status: {exit_code}")
        
        print(f"📝 Logs saved: {log_file}")
        
        if exit_code != 0:
            raise Exception(f"""3X-UI installation failed!

Exit code: {exit_code}

Last 20 lines:
{chr(10).join(output_lines[-20:])}

Full logs: {log_file}
""")
        
        # Verify running
        print("🔍 Verifying 3X-UI is running...")
        
        stdin, stdout, stderr = ssh.exec_command('systemctl is-active x-ui')
        is_active = stdout.read().decode().strip() == 'active'
        
        if not is_active:
            raise Exception("3X-UI service not running!")
        
        # Wait for service
        print("⏳ Waiting for 3X-UI to start...")
        time.sleep(10)
        
        # Check HTTP
        stdin, stdout, stderr = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost:54321')
        http_code = stdout.read().decode().strip()
        
        print(f"🌐 3X-UI HTTP status: {http_code}")
        
        # Format URL
        url = f"https://{custom_domain}" if custom_domain else f"http://{ip}:54321"
        
        print(f"✅ 3X-UI installed successfully!")
        print(f"   Panel: {url}")
        print(f"   Username: {admin_username}")
        print(f"   Password: {admin_password}")
        
        return {
            "status": "success",
            "app": "3x-ui",
            "url": url,
            "credentials": {
                "username": admin_username,
                "password": admin_password
            },
            "protocols": [
                "VMess",
                "VLESS",
                "Trojan",
                "Shadowsocks"
            ],
            "notes": "3X-UI panel ready! Create VPN accounts for your users.",
            "next_steps": [
                "1. Login to the panel",
                "2. Create inbound connections (VMess/VLESS recommended for Russia/China)",
                "3. Generate QR codes or links for clients",
                "4. Install v2rayN (Windows), v2rayNG (Android), or Shadowrocket (iOS)"
            ],
            "installation_log": str(log_file)
        }
    
    finally:
        ssh.close()
