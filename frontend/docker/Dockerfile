# syntax=docker/dockerfile:1
# Multi-stage: build the SPA with Vite, then serve the static assets with nginx.
# No Node runtime ships in the final image.

# ── Stage 1: build ─────────────────────────────────────────────────────────────
FROM node:20-alpine AS build

WORKDIR /app

# Install dependencies from the lockfile-agnostic manifest first (better caching).
COPY package.json ./
RUN npm install

COPY . .

# The API base URL is baked in at build time (defaults to the /api proxy path).
ARG VITE_API_URL=/api/v1
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build

# ── Stage 2: serve ─────────────────────────────────────────────────────────────
FROM nginx:1.27-alpine AS runtime

COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost/ >/dev/null 2>&1 || exit 1
