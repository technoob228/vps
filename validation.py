import re
import ipaddress
import validators

def validate_ip(ip_str):
    """Validate IP address"""
    try:
        ipaddress.ip_address(ip_str)
        return True, None
    except ValueError:
        return False, "Invalid IP address format"

def validate_app(app_name, supported_apps):
    """Validate app name"""
    if app_name not in supported_apps:
        return False, f"Unsupported app. Must be one of: {', '.join(supported_apps)}"
    return True, None

def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    return True, None

def validate_username(username):
    """Validate username"""
    if not username or len(username) < 2:
        return False, "Username must be at least 2 characters"
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        return False, "Username can only contain letters, numbers, hyphens and underscores"
    return True, None

def validate_domain(domain):
    """Validate custom domain"""
    if not domain:
        return True, None  # Optional field
    
    if validators.domain(domain):
        return True, None
    else:
        return False, "Invalid domain format"

def validate_provision_request(data, supported_apps):
    """Validate complete provision request"""
    errors = []

    # Check required fields
    required_fields = ['ip_address', 'username', 'password', 'app']
    for field in required_fields:
        if field not in data or not data[field]:
            errors.append(f"Missing required field: {field}")

    if errors:
        return False, errors

    # Validate IP
    valid, error = validate_ip(data['ip_address'])
    if not valid:
        errors.append(error)

    # Validate app
    valid, error = validate_app(data['app'], supported_apps)
    if not valid:
        errors.append(error)

    # Validate username
    valid, error = validate_username(data['username'])
    if not valid:
        errors.append(error)

    # Validate password
    valid, error = validate_password(data['password'])
    if not valid:
        errors.append(error)

    # Validate custom domain (optional)
    if 'custom_domain' in data and data['custom_domain']:
        valid, error = validate_domain(data['custom_domain'])
        if not valid:
            errors.append(error)

    if errors:
        return False, errors

    return True, None


def validate_universal_provision_request(data):
    """Validate universal provision request"""
    errors = []

    # Check required fields
    required_fields = ['ip_address', 'username', 'password', 'source_type', 'source_url', 'app_name']
    for field in required_fields:
        if field not in data or not data[field]:
            errors.append(f"Missing required field: {field}")

    if errors:
        return False, errors

    # Validate IP
    valid, error = validate_ip(data['ip_address'])
    if not valid:
        errors.append(error)

    # Validate username
    valid, error = validate_username(data['username'])
    if not valid:
        errors.append(error)

    # Validate password
    valid, error = validate_password(data['password'])
    if not valid:
        errors.append(error)

    # Validate source_type
    valid_source_types = ['docker-compose', 'docker-image', 'github-repo']
    if data['source_type'] not in valid_source_types:
        errors.append(f"Invalid source_type. Must be one of: {', '.join(valid_source_types)}")

    # Validate source_url
    source_url = data['source_url']
    if not source_url or len(source_url) < 3:
        errors.append("source_url must be at least 3 characters")

    # Validate app_name
    app_name = data['app_name']
    if not re.match(r'^[a-z0-9][a-z0-9_-]*$', app_name):
        errors.append("app_name must start with letter/number and contain only lowercase letters, numbers, hyphens, underscores")

    # Validate custom domain (optional)
    if 'custom_domain' in data and data['custom_domain']:
        valid, error = validate_domain(data['custom_domain'])
        if not valid:
            errors.append(error)

    # Validate max_memory_mb (optional)
    if 'max_memory_mb' in data:
        try:
            mem = int(data['max_memory_mb'])
            if mem < 128 or mem > 16384:
                errors.append("max_memory_mb must be between 128 and 16384")
        except (ValueError, TypeError):
            errors.append("max_memory_mb must be a number")

    # Validate max_cpu (optional)
    if 'max_cpu' in data:
        try:
            cpu = float(data['max_cpu'])
            if cpu < 0.1 or cpu > 32:
                errors.append("max_cpu must be between 0.1 and 32")
        except (ValueError, TypeError):
            errors.append("max_cpu must be a number")

    # Validate ports (optional)
    if 'ports' in data and data['ports']:
        if not isinstance(data['ports'], dict):
            errors.append("ports must be a dictionary (e.g., {'80': '80'})")
        else:
            for host_port, container_port in data['ports'].items():
                try:
                    hp = int(host_port)
                    cp = int(container_port)
                    if not (1 <= hp <= 65535) or not (1 <= cp <= 65535):
                        errors.append(f"Invalid port number: {host_port}:{container_port}")
                except (ValueError, TypeError):
                    errors.append(f"Port must be a number: {host_port}:{container_port}")

    if errors:
        return False, errors

    return True, None
