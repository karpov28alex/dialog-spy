FROM nginx:1.27-alpine
COPY index.html /usr/share/nginx/html/index.html
COPY admin.html /usr/share/nginx/html/admin.html
COPY app.js /usr/share/nginx/html/app.js
COPY admin.js /usr/share/nginx/html/admin.js
COPY styles.css /usr/share/nginx/html/styles.css
# Generate the browser cache key from the actual shipped assets. This avoids a
# manual version bump and guarantees changed JS/CSS receives a different URL.
RUN asset_version="$(cat /usr/share/nginx/html/app.js /usr/share/nginx/html/admin.js /usr/share/nginx/html/styles.css | sha256sum | cut -c1-16)" \
    && sed -i "s/__ASSET_VERSION__/${asset_version}/g" \
       /usr/share/nginx/html/index.html /usr/share/nginx/html/admin.html \
    && ! grep -R "__ASSET_VERSION__" /usr/share/nginx/html/*.html
COPY nginx.conf /etc/nginx/conf.d/default.conf
