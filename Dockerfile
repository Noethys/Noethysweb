FROM python:3.12

RUN apt-get update && \
    apt-get install -y cron supervisor && \
    rm -rf /var/lib/apt/lists/*

RUN python -m pip install gunicorn

WORKDIR /usr/src/app

COPY ./requirements.txt .

RUN pip install psycopg2
RUN pip3 install -r ./requirements.txt

RUN cat <<'EOF' > /etc/supervisor/conf.d/supervisord.conf
[supervisord]
nodaemon=true
logfile=/dev/null
logfile_maxbytes=0

[program:cron]
command=/usr/sbin/cron -f
autostart=true
autorestart=true
stdout_logfile=/dev/fd/1
stdout_logfile_maxbytes=0
stderr_logfile=/dev/fd/2
stderr_logfile_maxbytes=0

[program:app]
command=gunicorn noethysweb.wsgi --bind 0.0.0.0:80
directory=/usr/src/app/noethysweb
autostart=true
autorestart=true
stdout_logfile=/dev/fd/1
stdout_logfile_maxbytes=0
stderr_logfile=/dev/fd/2
stderr_logfile_maxbytes=0
EOF

COPY . .


WORKDIR /usr/src/app/noethysweb

# make sur it is executable so that we can easily manage a running instance like this:
# docker exec noethysweb ./manage.py import_defaut
RUN chmod +x ./manage.py

RUN ./manage.py collectstatic

CMD ["/bin/bash", "-c", "./manage.py migrate && /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf"]
