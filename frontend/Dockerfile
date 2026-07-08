# --- Stage 1: Build the static SPA ---
FROM node:20-alpine AS builder
WORKDIR /app

# Install deps first for better layer caching.
COPY package*.json ./
RUN npm install --include=dev

# Build the production bundle.
COPY . .
# CI=false so Vite warnings don't fail the build.
RUN CI=false npm run build

# --- Stage 2: Serve with nginx ---
FROM nginx:1.27-alpine AS runtime

# SPA + reverse-proxy config (see frontend/nginx.conf).
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

# nginx runs in the foreground by default via its base image CMD.
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD wget -qO- http://localhost/ >/dev/null 2>&1 || exit 1
