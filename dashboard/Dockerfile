# dashboard/Dockerfile

# --- Build stage: creates /app/dist ---
FROM node:20-alpine AS build
WORKDIR /app
# Only copy files needed to install deps first (better cache)
COPY package*.json ./
RUN npm ci
# Now copy the rest of the source and build
COPY . .
# If it's a Vite/React app, this creates ./dist
RUN npm run build

# --- Runtime stage: nginx to serve static files ---
FROM nginx:1.25-alpine AS runtime
# Optional: custom nginx config (if you have it)
COPY nginx.conf /etc/nginx/conf.d/default.conf
# Copy built files from the build stage
COPY --from=build /app/dist/ /usr/share/nginx/html/
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
