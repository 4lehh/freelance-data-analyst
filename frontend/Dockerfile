FROM nginx:1.27-alpine

# Estáticos de la aplicación
COPY index.html /usr/share/nginx/html/index.html
COPY static/ /usr/share/nginx/html/static/

# Configuración con el reverse-proxy hacia el backend
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]