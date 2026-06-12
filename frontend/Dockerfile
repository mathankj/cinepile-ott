# Frontend image — Vite production build served by nginx.
#
# Stage 1 compiles the SPA; stage 2 is a ~10 MB nginx that serves the static
# files and reverse-proxies /v1 + /healthz to the api container. The SPA calls
# the API same-origin (VITE_API_BASE_URL is unset → ""), so no CORS config is
# needed anywhere.
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1
