import secrets
import string
import time
from pathlib import Path
from ssh_utils import create_ssh_client, exec_command_with_output, check_container_running

def generate_secret(length=32):
    """Generate secure random secret"""
    return secrets.token_hex(length)

def setup_outline(ip, username, password, custom_domain=None, job_id=None):
    """Install Outline - Notion alternative"""
    
    print(f"📦 Setting up Outline on {ip}...")
    
    # Read installation script
    script_path = Path(__file__).parent.parent / 'templates' / 'outline_install.sh'
    with open(script_path, 'r') as f:
        install_script = f.read()
    
    # Generate secrets
    secret_key = generate_secret(32)
    utils_secret = generate_secret(32)
    
    # Replace variables
    install_script = install_script.replace('{{SECRET_KEY}}', secret_key)
    install_script = install_script.replace('{{UTILS_SECRET}}', utils_secret)
    install_script = install_script.replace('{{SERVER_IP}}', ip)
    
    # Connect SSH
    ssh = create_ssh_client(ip, username, password)
    
    try:
        # Check if already installed
        if check_container_running(ssh, 'outline'):
            print("✅ Outline already running")
            
            url = f"https://{custom_domain}" if custom_domain else f"http://{ip}:3000"
            
            return {
                "status": "success",
                "app": "outline",
                "url": url,
                "credentials": {
                    "note": "Use magic link authentication - enter your email on first visit"
                },
                "notes": "Outline was already installed. Configure SMTP for email auth."
            }
        
        print("📤 Uploading installation script...")
        
        create_script_cmd = f"""cat > /root/install_outline.sh << 'EOFSCRIPT'
{install_script}
EOFSCRIPT
chmod +x /root/install_outline.sh
"""
        
        stdin, stdout, stderr = ssh.exec_command(create_script_cmd)
        stdout.channel.recv_exit_status()
        
        print("⚙️  Running installation (10-15 minutes)...")
        print("   Note: Outline requires PostgreSQL and Redis")
        
        # Run installation
        exit_code, output_lines = exec_command_with_output(
            ssh,
            'bash /root/install_outline.sh 2>&1',
            timeout=1200  # 20 minutes for Outline
        )
        
        # Save logs
        log_file = Path(f'/tmp/outline_install_{ip.replace(".", "_")}.log')
        with open(log_file, 'w') as f:
            f.write("\n".join(output_lines))
            f.write(f"\n\nExit status: {exit_code}")
        
        print(f"📝 Logs saved: {log_file}")
        
        if exit_code != 0:
            raise Exception(f"""Outline installation failed!

Exit code: {exit_code}

Last 30 lines:
{chr(10).join(output_lines[-30:])}

Full logs: {log_file}
""")
        
        # Verify running
        print("🔍 Verifying Outline services...")
        
        # Check all services
        stdin, stdout, stderr = ssh.exec_command('cd /opt/outline && docker compose ps')
        compose_status = stdout.read().decode()
        print(f"Services status:\n{compose_status}")
        
        if not check_container_running(ssh, 'outline'):
            raise Exception(f"Outline container not running!\n\nStatus:\n{compose_status}")
        
        # Wait for Outline to be ready
        print("⏳ Waiting for Outline to start (this can take 2-3 minutes)...")
        time.sleep(60)
        
        # Check HTTP
        stdin, stdout, stderr = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost:3000')
        http_code = stdout.read().decode().strip()
        
        print(f"🌐 Outline HTTP status: {http_code}")
        
        # Format URL
        url = f"https://{custom_domain}" if custom_domain else f"http://{ip}:3000"
        
        print(f"✅ Outline installed successfully!")
        print(f"   URL: {url}")
        print(f"   Authentication: Magic link (email-based)")
        
        return {
            "status": "success",
            "app": "outline",
            "url": url,
            "credentials": {
                "authentication": "magic-link",
                "note": "Enter your email on first visit to receive login link"
            },
            "notes": "Outline is ready! For production use, configure SMTP in /opt/outline/.env",
            "next_steps": [
                "1. Visit the URL and enter your email",
                "2. Check server logs for magic link: docker logs outline",
                "3. For email delivery, configure SMTP settings in /opt/outline/.env"
            ],
            "installation_log": str(log_file)
        }
    
    finally:
        ssh.close()
