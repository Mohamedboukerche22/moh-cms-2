import os
import secrets
from datetime import datetime
from flask import current_app
from werkzeug.utils import secure_filename


def allowed_file(filename, allowed_extensions):
    """Check if file has allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


def save_uploaded_file(file, upload_folder, allowed_extensions):
    """Save uploaded file securely"""
    if file and file.filename and allowed_file(file.filename, allowed_extensions):
        # Generate unique filename
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{secrets.token_hex(8)}{ext}"
        
        # Ensure upload directory exists
        os.makedirs(upload_folder, exist_ok=True)
        
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)
        return unique_filename
    return None


def format_datetime(dt):
    """Format datetime for display"""
    if dt is None:
        return 'Never'
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def format_time_delta(dt):
    """Format time difference from now"""
    if dt is None:
        return 'Never'
    
    now = datetime.utcnow()
    if dt > now:
        delta = dt - now
        prefix = 'in '
    else:
        delta = now - dt
        prefix = ''
    
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if days > 0:
        return f"{prefix}{days} day{'s' if days != 1 else ''} ago"
    elif hours > 0:
        return f"{prefix}{hours} hour{'s' if hours != 1 else ''} ago"
    elif minutes > 0:
        return f"{prefix}{minutes} minute{'s' if minutes != 1 else ''} ago"
    else:
        return f"{prefix}{seconds} second{'s' if seconds != 1 else ''} ago"


def get_language_extension(language):
    """Get file extension for programming language"""
    extensions = {
        'python3': '.py',
        'cpp': '.cpp',
        'c': '.c',
        'java': '.java'
    }
    return extensions.get(language, '.txt')


def truncate_text(text, max_length=100):
    """Truncate text to specified length"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + '...'


# Template filters
def register_template_filters(app):
    """Register custom template filters"""
    
    @app.template_filter('datetime')
    def datetime_filter(dt):
        return format_datetime(dt)
    
    @app.template_filter('timedelta')
    def timedelta_filter(dt):
        return format_time_delta(dt)
    
    @app.template_filter('truncate')
    def truncate_filter(text, length=100):
        return truncate_text(text, length)


# Register filters
from app import app
register_template_filters(app)
