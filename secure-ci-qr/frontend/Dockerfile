# Образ nginx, работающий от непривилегированного пользователя (Trivy DS-0002)
FROM nginxinc/nginx-unprivileged:1.29-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html script.js style.css /usr/share/nginx/html/

# Явно указываем непривилегированного пользователя nginx (uid 101)
USER 101

EXPOSE 8080
