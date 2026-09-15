# syntax=docker/dockerfile:1

# Stage 1 — build
FROM node:20-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Browser → FastAPI rule: VITE_API_BASE_URL must be host-resolvable (localhost:8000),
# not a Docker service name. Passed as build arg so the built JS embeds the correct URL.
ARG VITE_API_BASE_URL=http://localhost:8000
ARG VITE_API_V1_PREFIX=/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_API_V1_PREFIX=$VITE_API_V1_PREFIX

RUN npm run build

# Stage 2 — serve with nginx (small, production-like)
FROM nginx:alpine AS runtime
COPY --from=build /app/dist /usr/share/nginx/html
# SPA fallback — all routes serve index.html
RUN printf 'server {\n\
    listen 80;\n\
    server_name localhost;\n\
    root /usr/share/nginx/html;\n\
    index index.html;\n\
    location / {\n\
        try_files $uri $uri/ /index.html;\n\
    }\n\
}\n' > /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
