# TechCorp Support Form - React Frontend
# Standalone Nginx deployment for the web support form

# Stage 1: Build
FROM node:18-slim AS builder

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --production=false 2>/dev/null || npm install
COPY . .
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built React app
COPY --from=builder /app/build /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
