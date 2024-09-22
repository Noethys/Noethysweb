bind = "unix:../gunicorn.sock"
pidfile = "../gunicorn.pid"
wsgi_app = "noethysweb.wsgi"
preload_app = False  # Don't preload to allow SIGHUP to reload code
limit_request_line = 8190