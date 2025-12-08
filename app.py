from flask import Flask, request, jsonify
import threading
import uuid
import time
from pathlib import Path

# Import our modules
from config import Config
from storage import JobStorage
from validation import validate_provision_request, validate_universal_provision_request
from auth import require_api_key

# Import provisioners
from provisioners.n8n import setup_n8n
from provisioners.wireguard import setup_wireguard
from provisioners.outline import setup_outline
from provisioners.vaultwarden import setup_vaultwarden
from provisioners.x3ui import setup_3x_ui
from provisioners.seafile import setup_seafile
from provisioners.filebrowser import setup_filebrowser
from provisioners.universal import (
    setup_universal,
    InsufficientResourcesError,
    PortConflictError,
    SourceDownloadError,
    UniversalProvisionerException
)

app = Flask(__name__)

# Validate configuration
Config.validate()

# Initialize storage
storage = JobStorage(Config.DATABASE)

# Provisioner mapping
PROVISIONERS = {
    'n8n': setup_n8n,
    'wireguard': setup_wireguard,
    'outline': setup_outline,
    'vaultwarden': setup_vaultwarden,
    '3x-ui': setup_3x_ui,
    'seafile': setup_seafile,
    'filebrowser': setup_filebrowser,
}

def update_job_status(job_id, status, progress=None, **kwargs):
    """Update job status in storage"""
    job = storage.get_job(job_id) or {}
    job['status'] = status
    if progress is not None:
        job['progress'] = progress
    job.update(kwargs)
    storage.save_job(job_id, job)

def provision_worker(job_id, ip, username, password, app_type, custom_domain):
    """Background worker for provisioning"""
    
    try:
        from ssh_utils import wait_for_ssh
        
        # Step 1: Wait for SSH
        update_job_status(job_id, "waiting_ssh", progress=5, 
                         message="Waiting for server to be ready...")
        
        success, attempts = wait_for_ssh(ip, username, password, 
                                        max_retries=Config.SSH_MAX_RETRIES)
        
        if not success:
            update_job_status(
                job_id, "failed", progress=0,
                error=f"SSH timeout after {attempts} attempts. Server not ready."
            )
            return
        
        # Step 2: Install application
        update_job_status(job_id, "installing", progress=30,
                         message=f"Installing {app_type}...")
        
        provisioner = PROVISIONERS.get(app_type)
        if not provisioner:
            update_job_status(
                job_id, "failed", progress=0,
                error=f"Unknown app type: {app_type}"
            )
            return
        
        result = provisioner(ip, username, password, custom_domain, job_id)
        
        # Step 3: Complete
        update_job_status(
            job_id, "completed", progress=100,
            message="Installation completed successfully!",
            result=result
        )
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Provisioning failed for job {job_id}: {error_msg}")
        update_job_status(
            job_id, "failed", progress=0,
            error=error_msg
        )

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "version": "2.1.1",
        "supported_apps": Config.SUPPORTED_APPS
    }), 200

@app.route('/provision', methods=['POST'])
@require_api_key(Config.API_KEY)
def provision():
    """
    Create provisioning job
    
    Request body:
    {
        "ip_address": "95.179.200.45",
        "username": "root",
        "password": "secure_password",
        "app": "n8n",
        "custom_domain": "n8n.example.com"  // optional
    }
    
    Response (202 Accepted):
    {
        "job_id": "abc-123-def",
        "status": "started",
        "status_url": "/status/abc-123-def"
    }
    """
    
    data = request.json
    
    # Validate input
    valid, errors = validate_provision_request(data, Config.SUPPORTED_APPS)
    if not valid:
        return jsonify({"errors": errors}), 400
    
    # Create job
    job_id = str(uuid.uuid4())
    
    # Save initial job status
    storage.save_job(job_id, {
        "job_id": job_id,
        "status": "started",
        "progress": 0,
        "message": "Provisioning started",
        "ip": data['ip_address'],
        "app": data['app']
    })
    
    # Start background worker
    thread = threading.Thread(
        target=provision_worker,
        args=(
            job_id,
            data['ip_address'],
            data['username'],
            data['password'],
            data['app'],
            data.get('custom_domain')
        ),
        daemon=True
    )
    thread.start()
    
    return jsonify({
        "job_id": job_id,
        "status": "started",
        "status_url": f"/status/{job_id}"
    }), 202


def universal_provision_worker(job_id, data):
    """Background worker for universal provisioning"""

    try:
        from ssh_utils import wait_for_ssh

        ip = data['ip_address']
        username = data['username']
        password = data['password']

        # Step 1: Wait for SSH
        update_job_status(job_id, "waiting_ssh", progress=5,
                         message="Waiting for server to be ready...")

        success, attempts = wait_for_ssh(ip, username, password,
                                        max_retries=Config.SSH_MAX_RETRIES)

        if not success:
            update_job_status(
                job_id, "failed", progress=0,
                error=f"SSH timeout after {attempts} attempts. Server not ready."
            )
            return

        # Step 2: Run universal provisioner
        update_job_status(job_id, "analyzing", progress=20,
                         message=f"Analyzing {data['source_type']} source...")

        result = setup_universal(
            ip=ip,
            username=username,
            password=password,
            source_type=data['source_type'],
            source_url=data['source_url'],
            app_name=data['app_name'],
            custom_domain=data.get('custom_domain'),
            job_id=job_id,
            max_memory_mb=data.get('max_memory_mb', 2048),
            max_cpu=data.get('max_cpu', 2.0),
            ports=data.get('ports'),
            env_vars=data.get('env_vars'),
            dockerfile_path=data.get('dockerfile_path')
        )

        # Step 3: Complete
        update_job_status(
            job_id, "completed", progress=100,
            message="Installation completed successfully!",
            result=result
        )

    except InsufficientResourcesError as e:
        update_job_status(
            job_id, "rejected", progress=0,
            error=str(e),
            error_type="insufficient_resources"
        )

    except PortConflictError as e:
        update_job_status(
            job_id, "rejected", progress=0,
            error=str(e),
            error_type="port_conflict"
        )

    except SourceDownloadError as e:
        update_job_status(
            job_id, "failed", progress=0,
            error=str(e),
            error_type="source_download"
        )

    except UniversalProvisionerException as e:
        update_job_status(
            job_id, "failed", progress=0,
            error=str(e),
            error_type="provisioner"
        )

    except Exception as e:
        error_msg = str(e)
        print(f"❌ Universal provisioning failed for job {job_id}: {error_msg}")
        update_job_status(
            job_id, "failed", progress=0,
            error=error_msg,
            error_type="unknown"
        )


@app.route('/provision/universal', methods=['POST'])
@require_api_key(Config.API_KEY)
def provision_universal():
    """
    Universal provisioner - install any Docker application

    Request body:
    {
        "ip_address": "95.179.200.45",
        "username": "root",
        "password": "secure_password",
        "source_type": "docker-compose" | "docker-image" | "github-repo",
        "source_url": "https://raw.githubusercontent.com/.../docker-compose.yml",
        "app_name": "my-app",

        // Optional
        "custom_domain": "app.example.com",
        "max_memory_mb": 2048,
        "max_cpu": 2.0,
        "ports": {"8080": "80"},
        "env_vars": {"API_KEY": "xyz"},
        "dockerfile_path": "docker/Dockerfile"
    }

    Response (202 Accepted):
    {
        "job_id": "abc-123-def",
        "status": "started",
        "status_url": "/status/abc-123-def"
    }
    """

    data = request.json

    # Validate input
    valid, errors = validate_universal_provision_request(data)
    if not valid:
        return jsonify({"errors": errors}), 400

    # Create job
    job_id = str(uuid.uuid4())

    # Save initial job status
    storage.save_job(job_id, {
        "job_id": job_id,
        "status": "started",
        "progress": 0,
        "message": "Universal provisioning started",
        "ip": data['ip_address'],
        "app": data['app_name'],
        "source_type": data['source_type'],
        "source_url": data['source_url']
    })

    # Start background worker
    thread = threading.Thread(
        target=universal_provision_worker,
        args=(job_id, data),
        daemon=True
    )
    thread.start()

    return jsonify({
        "job_id": job_id,
        "status": "started",
        "status_url": f"/status/{job_id}"
    }), 202


@app.route('/status/<job_id>', methods=['GET'])
def get_status(job_id):
    """
    Get job status
    
    Response (in progress):
    {
        "job_id": "abc-123",
        "status": "installing",
        "progress": 60,
        "message": "Installing n8n..."
    }
    
    Response (completed):
    {
        "job_id": "abc-123",
        "status": "completed",
        "progress": 100,
        "result": {
            "url": "http://95.179.200.45:5678",
            "credentials": {...}
        }
    }
    """
    
    job = storage.get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    return jsonify(job), 200

@app.route('/jobs', methods=['GET'])
@require_api_key(Config.API_KEY)
def list_jobs():
    """
    List recent jobs
    
    Query params:
    - limit: number of jobs (default: 100)
    - status: filter by status (optional)
    """
    
    limit = request.args.get('limit', 100, type=int)
    status = request.args.get('status')
    
    jobs = storage.list_jobs(limit=limit, status=status)
    
    return jsonify({
        "total": len(jobs),
        "jobs": jobs
    }), 200

@app.route('/stats', methods=['GET'])
@require_api_key(Config.API_KEY)
def get_stats():
    """Get provisioning statistics"""
    
    stats = storage.get_stats()
    
    return jsonify(stats), 200

@app.route('/cleanup', methods=['POST'])
@require_api_key(Config.API_KEY)
def cleanup_jobs():
    """Manually trigger job cleanup"""
    
    deleted = storage.cleanup_old_jobs(Config.MAX_JOB_AGE_HOURS)
    
    return jsonify({
        "message": f"Cleaned up {deleted} old jobs"
    }), 200

def start_cleanup_scheduler():
    """Background thread to cleanup old jobs"""
    def cleanup_loop():
        while True:
            time.sleep(Config.JOB_CLEANUP_INTERVAL)
            deleted = storage.cleanup_old_jobs(Config.MAX_JOB_AGE_HOURS)
            if deleted > 0:
                print(f"🧹 Cleaned up {deleted} old jobs")
    
    thread = threading.Thread(target=cleanup_loop, daemon=True)
    thread.start()

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 VPS Provisioner v2.1.1")
    print("=" * 60)
    print(f"📊 Database: {Config.DATABASE}")
    print(f"🔐 API Key: {Config.API_KEY[:10]}..." if len(Config.API_KEY) > 10 else "⚠️  No API key set!")
    print(f"📱 Pre-configured apps: {', '.join(Config.SUPPORTED_APPS)}")
    print("=" * 60)
    print("📋 Endpoints:")
    print("   POST /provision - Create provisioning job (pre-configured apps)")
    print("   POST /provision/universal - Install ANY Docker app (NEW! ⭐)")
    print("   GET  /status/<job_id> - Check job status")
    print("   GET  /jobs - List all jobs (requires API key)")
    print("   GET  /stats - Get statistics (requires API key)")
    print("   POST /cleanup - Cleanup old jobs (requires API key)")
    print("   GET  /health - Health check")
    print("=" * 60)
    print("✨ Universal Provisioner:")
    print("   Install from docker-compose, docker-image, or github-repo")
    print("   Automatic resource checking and safety limits")
    print("   See UNIVERSAL_PROVISIONER_GUIDE.md for examples")
    print("=" * 60)
    print("\n🌐 Server starting on http://0.0.0.0:5001")
    print("⚠️  Use Gunicorn in production: gunicorn -w 4 -b 0.0.0.0:5001 app:app\n")
    
    # Start cleanup scheduler
    start_cleanup_scheduler()
    
    # Run Flask (development only)
    app.run(host='0.0.0.0', port=5001, debug=False)
