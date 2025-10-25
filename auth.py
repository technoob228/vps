from functools import wraps
from flask import request, jsonify

def require_api_key(api_key):
    """Decorator to require API key authentication"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check for API key in header
            provided_key = request.headers.get('X-API-Key')
            
            if not provided_key:
                return jsonify({
                    "error": "Missing API key",
                    "message": "Include X-API-Key header in your request"
                }), 401
            
            if provided_key != api_key:
                return jsonify({
                    "error": "Invalid API key",
                    "message": "The provided API key is incorrect"
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator
