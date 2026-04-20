FROM node:20-alpine AS builder
WORKDIR /app
COPY frontend/package.json ./
RUN npm install --frozen-lockfile 2>/dev/null || npm install
COPY frontend/ .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=builder /app/dist /app/frontend/dist
COPY infra/nginx/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -q --spider http://localhost/health || exit 1
CMD ["nginx", "-g", "daemon off;"]
