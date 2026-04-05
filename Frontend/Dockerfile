FROM node:20-slim AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --legacy-peer-deps

COPY . .

# Build args become env vars at build time (Vite bakes them into the bundle)
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_ANON_KEY
ARG VITE_API_URL

# ARGs must be exported as ENV for Vite to read them during build
ENV VITE_SUPABASE_URL=$VITE_SUPABASE_URL
ENV VITE_SUPABASE_ANON_KEY=$VITE_SUPABASE_ANON_KEY
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# --- Production: serve static files with a tiny HTTP server ---
FROM node:20-slim AS runner

WORKDIR /app

RUN npm install -g serve@14

COPY --from=builder /app/dist ./dist

EXPOSE 8080

# -s = SPA mode (rewrites all routes to index.html)
CMD ["serve", "-s", "dist", "-l", "8080"]
