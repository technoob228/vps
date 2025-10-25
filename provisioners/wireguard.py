import time
from pathlib import Path
from ssh_utils import create_ssh_client, exec_command_with_output, check_container_running, get_container_logs

def setup_wireguard(ip, username, password, custom_domain=None, job_id=None):
    """Install WireGuard VPN with UI"""
    
    print(f"📦 Setting up WireGuard on {ip}...")
    
    # Read installation script
    script_path = Path(__file__).parent.parent / 'templates' / 'wireguard_install.sh'
    with open(script_path, 'r') as f:
        install_script = f.read()
    
    # Connect SSH
    ssh = create_ssh_client(ip, username, password)
    
    try:
        # Check if already installed
        if check_container_running(ssh, 'wireguard-ui'):
            print("✅ WireGuard UI already running")
            
            # Get existing password
            stdin, stdout, stderr = ssh.exec_command('cat /opt/wireguard-ui/admin_password.txt 2>/dev/null')
            admin_password = stdout.read().decode().strip()
            
            url = f"https://{custom_domain}" if custom_domain else f"http://{ip}:5000"
            
            return {
                "status": "success",
                "app": "wireguard",
                "url": url,
                "credentials": {
                    "username": "admin",
                    "password": admin_password or "check server /opt/wireguard-ui/admin_password.txt"
                },
                "notes": "WireGuard was already installed and running",
                "vpn_port": 51820
            }
        
        print("📤 Uploading installation script...")
        
        # Create script on server
        create_script_cmd = f"""cat > /root/install_wg.sh << 'EOFSCRIPT'
{install_script}
EOFSCRIPT
chmod +x /root/install_wg.sh
"""
        
        stdin, stdout, stderr = ssh.exec_command(create_script_cmd)
        stdout.channel.recv_exit_status()
        
        print("⚙️  Running installation (5-10 minutes)...")
        
        # Run installation
        exit_code, output_lines = exec_command_with_output(
            ssh,
            'bash /root/install_wg.sh 2>&1'
        )
        
        # Save logs
        log_file = Path(f'/tmp/wireguard_install_{ip.replace(".", "_")}.log')
        with open(log_file, 'w') as f:
            f.write("\n".join(output_lines))
            f.write(f"\n\nExit status: {exit_code}")
        
        print(f"📝 Logs saved: {log_file}")
        
        if exit_code != 0:
            stdin, stdout, stderr = ssh.exec_command('docker ps -a 2>&1')
            docker_status = stdout.read().decode()
            
            container_logs = get_container_logs(ssh, 'wireguard-ui')
            
            raise Exception(f"""WireGuard installation failed!

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
        print("🔍 Verifying WireGuard UI is running...")
        
        if not check_container_running(ssh, 'wireguard-ui'):
            container_logs = get_container_logs(ssh, 'wireguard-ui')
            raise Exception(f"WireGuard UI not running!\n\nLogs:\n{container_logs[:1000]}")
        
        # Get admin password
        print("🔑 Retrieving admin password...")
        time.sleep(2)
        
        stdin, stdout, stderr = ssh.exec_command('cat /opt/wireguard-ui/admin_password.txt')
        admin_password = stdout.read().decode().strip()
        
        if not admin_password:
            raise Exception("Failed to retrieve admin password")
        
        # Wait for UI to be ready
        print("⏳ Waiting for WireGuard UI...")
        time.sleep(10)
        
        # Check HTTP
        stdin, stdout, stderr = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost:5000')
        http_code = stdout.read().decode().strip()
        
        print(f"🌐 WireGuard UI HTTP status: {http_code}")
        
        # Format URL
        url = f"https://{custom_domain}" if custom_domain else f"http://{ip}:5000"
        
        print(f"✅ WireGuard installed successfully!")
        print(f"   UI: {url}")
        print(f"   VPN Port: 51820/udp")
        print(f"   Username: admin")
        print(f"   Password: {admin_password}")
        
        return {
            "status": "success",
            "app": "wireguard",
            "url": url,
            "credentials": {
                "username": "admin",
                "password": admin_password
            },
            "notes": "WireGuard VPN ready! Create client configs in the UI.",
            "vpn_port": 51820,
            "installation_log": str(log_file)
        }
    
    finally:
        ssh.close()
