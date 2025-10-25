import secrets
import time
from pathlib import Path
from ssh_utils import create_ssh_client, exec_command_with_output, check_container_running

def setup_vaultwarden(ip, username, password, custom_domain=None, job_id=None):
    """Install Vaultwarden - Self-hosted Bitwarden"""
    
    print(f"📦 Setting up Vaultwarden on {ip}...")
    
    # Read installation script
    script_path = Path(__file__).parent.parent / 'templates' / 'vaultwarden_install.sh'
    with open(script_path, 'r') as f:
        install_script = f.read()
    
    # Generate admin token
    admin_token = secrets.token_urlsafe(32)
    
    # Replace variables
    install_script = install_script.replace('{{ADMIN_TOKEN}}', admin_token)
    install_script = install_script.replace('{{DOMAIN}}', custom_domain or f'http://{ip}:8080')
    
    # Connect SSH
    ssh = create_ssh_client(ip, username, password)
    
    try:
        # Check if already installed
        if check_container_running(ssh, 'vaultwarden'):
            print("✅ Vaultwarden already running")
            
            # Try to get existing token
            stdin, stdout, stderr = ssh.exec_command('cat /opt/vaultwarden/admin_token.txt 2>/dev/null')
            existing_token = stdout.read().decode().strip()
            
            url = f"https://{custom_domain}" if custom_domain else f"http://{ip}:8080"
            
            return {
                "status": "success",
                "app": "vaultwarden",
                "url": url,
                "credentials": {
                    "admin_url": f"{url}/admin",
                    "admin_token": existing_token or "check /opt/vaultwarden/admin_token.txt"
                },
                "notes": "Vaultwarden was already installed. Create account on first visit."
            }
        
        print("📤 Uploading installation script...")
        
        create_script_cmd = f"""cat > /root/install_vaultwarden.sh << 'EOFSCRIPT'
{install_script}
EOFSCRIPT
chmod +x /root/install_vaultwarden.sh
"""
        
        stdin, stdout, stderr = ssh.exec_command(create_script_cmd)
        stdout.channel.recv_exit_status()
        
        print("⚙️  Running installation (3-5 minutes)...")
        
        # Run installation
        exit_code, output_lines = exec_command_with_output(
            ssh,
            'bash /root/install_vaultwarden.sh 2>&1'
        )
        
        # Save logs
        log_file = Path(f'/tmp/vaultwarden_install_{ip.replace(".", "_")}.log')
        with open(log_file, 'w') as f:
            f.write("\n".join(output_lines))
            f.write(f"\n\nExit status: {exit_code}")
        
        print(f"📝 Logs saved: {log_file}")
        
        if exit_code != 0:
            raise Exception(f"""Vaultwarden installation failed!

Exit code: {exit_code}

Last 20 lines:
{chr(10).join(output_lines[-20:])}

Full logs: {log_file}
""")
        
        # Verify running
        print("🔍 Verifying Vaultwarden is running...")
        
        if not check_container_running(ssh, 'vaultwarden'):
            raise Exception("Vaultwarden container not running!")
        
        # Wait for service
        print("⏳ Waiting for Vaultwarden to start...")
        time.sleep(10)
        
        # Check HTTP
        stdin, stdout, stderr = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost:8080')
        http_code = stdout.read().decode().strip()
        
        print(f"🌐 Vaultwarden HTTP status: {http_code}")
        
        # Format URL
        url = f"https://{custom_domain}" if custom_domain else f"http://{ip}:8080"
        admin_url = f"{url}/admin"
        
        print(f"✅ Vaultwarden installed successfully!")
        print(f"   URL: {url}")
        print(f"   Admin: {admin_url}")
        print(f"   Admin Token: {admin_token}")
        
        return {
            "status": "success",
            "app": "vaultwarden",
            "url": url,
            "credentials": {
                "admin_url": admin_url,
                "admin_token": admin_token,
                "note": "Create your personal account on first visit. Use admin token for settings."
            },
            "notes": "Vaultwarden is ready! Create account and start using password manager.",
            "next_steps": [
                "1. Visit the URL and create your account (email + master password)",
                "2. Install Bitwarden browser extension",
                "3. Point extension to your server URL",
                f"4. Access admin panel at {admin_url} with the token"
            ],
            "installation_log": str(log_file)
        }
    
    finally:
        ssh.close()
