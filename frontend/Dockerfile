# ==============================================================================
# Interview Practice Coach - Frontend Production Multi-Stage Dockerfile
# Stage 1: Node.js Vite + TypeScript compilation
# Stage 2: Nginx Alpine high-performance SPA static server & reverse proxy
# ==============================================================================

# --- Stage 1: Build ---
FROM node:20-alpine AS builder

WORKDIR /app

# Install npm dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy source and config files
COPY . .

# Build Vite application for production distribution
ARG VITE_API_BASE_URL=""
ARG VITE_WS_URL=""
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_WS_URL=$VITE_WS_URL

RUN npm run build

# --- Stage 2: Production Nginx Server ---
FROM nginx:1.25-alpine AS runner

# Remove default nginx static assets
RUN rm -rf /usr/share/nginx/html/*

# Copy compiled frontend assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

# Health check to ensure Nginx is serving index.html
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
