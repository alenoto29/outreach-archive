"""Local Gunicorn settings; keep credentials out of URL paths and request logs."""
import os

workers = 2
bind = f"{os.getenv('BIND_HOST', '127.0.0.1')}:{os.getenv('PORT', '8080')}"
accesslog = "-"
errorlog = "-"
# %(U)s = path without query string (vs %(r)s which includes it).
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(m)s %(U)s %(H)s" %(s)s %(b)s "%(f)s" "%(a)s"'
