# Two stages: Node builds the static files, nginx serves them.
# (In the cloud the files go to Blob Storage instead; this image is for running locally.)

# ---------- Stage 1: build ----------
FROM node:22-alpine AS build
WORKDIR /app

# Dependencies first: this layer is cached until the package files change.
COPY package.json package-lock.json ./
RUN npm ci

# Then the code, and build the static files into /app/dist.
COPY . .
RUN npm run build

# ---------- Stage 2: serve ----------
# nginx image that runs as a non-root user (listens on 8080).
FROM nginxinc/nginx-unprivileged:1.30-alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
