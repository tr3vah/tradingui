FROM nginx:1.25-alpine
WORKDIR /tmp

# Copy static web files into nginx html root
COPY web/ /usr/share/nginx/html/

# Copy our nginx proxy config
COPY deploy/nginx/default.conf /etc/nginx/conf.d/default.conf

# Create SSL directory
RUN mkdir -p /etc/nginx/ssl

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
