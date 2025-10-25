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
