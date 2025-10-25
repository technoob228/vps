import secrets
import string
import time
from pathlib import Path
from ssh_utils import create_ssh_client, exec_command_with_output, check_container_running, get_container_logs

def generate_password(length=16):
    """Generate secure random password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def setup_n8n(ip, username, password, custom_domain=None, job_id=None):
    """Install n8n automation platform"""
    
    print(f"📦 Setting up n8n on {ip}...")
    
    # Generate credentials
    n8n_password = generate_password()
    
    # Read installation script
    script_path = Path(__file__).parent.parent / 'templates' / 'n8n_install.sh'
    with open(script_path, 'r') as f:
        install_script = f.read()
    
    # Replace variables
    install_script = install_script.replace('{{N8N_PASSWORD}}', n8n_password)
    
    # Connect SSH
    ssh = create_ssh_client(ip, username, password)
    
    try:
        # Check if already installed
        if check_container_running(ssh, 'n8n'):
            print("✅ n8n already running, skipping installation")
            
            # Try to get existing password
            stdin, stdout, stderr = ssh.exec_command('cat /opt/n8n/.env 2>/dev/null | grep N8N_PASSWORD | cut -d= -f2')
            existing_password = stdout.read().decode().strip()
            
            url = f"https://{custom_domain}" if custom_domain else f"http://{ip}:5678"
            
            return {
                "status": "success",
                "app": "n8n",
                "url": url,
                "credentials": {
                    "username": "admin",
                    "password": existing_password or "check server /opt/n8n/.env"
                },
                "notes": "n8n was already installed and running"
            }
        
        print("📤 Uploading installation script...")
        
        # Create script on server
        create_script_cmd = f"""cat > /root/install_n8n.sh << 'EOFSCRIPT'
{install_script}
EOFSCRIPT
chmod +x /root/install_n8n.sh
"""
        
        stdin, stdout, stderr = ssh.exec_command(create_script_cmd)
        stdout.channel.recv_exit_status()
        
        print("⚙️  Running installation (5-10 minutes)...")
        
        # Run installation
        exit_code, output_lines = exec_command_with_output(
            ssh, 
            'bash /root/install_n8n.sh 2>&1'
        )
        
        # Save logs
        log_file = Path(f'/tmp/n8n_install_{ip.replace(".", "_")}.log')
        with open(log_file, 'w') as f:
            f.write("\n".join(output_lines))
            f.write(f"\n\nExit status: {exit_code}")
        
        print(f"📝 Logs saved: {log_file}")
        
        if exit_code != 0:
            # Get Docker status
            stdin, stdout, stderr = ssh.exec_command('docker ps -a 2>&1')
            docker_status = stdout.read().decode()
            
            # Get container logs if exists
            container_logs = get_container_logs(ssh, 'n8n')
            
            raise Exception(f"""n8n installation failed!

Exit code: {exit_code}

Last 20 lines:
{chr(10).join(output_lines[-20:])}

Docker status:
{docker_status}

Container logs:
{container_logs[:1000]}

Full logs: {log_file}
""")
        
        # Verify running
        print("🔍 Verifying n8n is running...")
        
        if not check_container_running(ssh, 'n8n'):
            container_logs = get_container_logs(ssh, 'n8n')
            raise Exception(f"n8n container not running!\n\nLogs:\n{container_logs[:1000]}")
        
        # Wait for n8n to be ready
        print("⏳ Waiting for n8n to start...")
        time.sleep(15)
        
        # Check HTTP response
        stdin, stdout, stderr = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost:5678')
        http_code = stdout.read().decode().strip()
        
        print(f"🌐 n8n HTTP status: {http_code}")
        
        # Format URL
        url = f"https://{custom_domain}" if custom_domain else f"http://{ip}:5678"
        
        print(f"✅ n8n installed successfully!")
        print(f"   URL: {url}")
        print(f"   Username: admin")
        print(f"   Password: {n8n_password}")
        
        return {
            "status": "success",
            "app": "n8n",
            "url": url,
            "credentials": {
                "username": "admin",
                "password": n8n_password
            },
            "notes": "n8n is ready! Login and start creating workflows.",
            "installation_log": str(log_file)
        }
    
    finally:
        ssh.close()
