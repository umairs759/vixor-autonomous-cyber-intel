# VIXOR — Frontend (Next.js 14 App Router) container
FROM node:20-alpine

ENV NODE_ENV=production

WORKDIR /app

# Copy dependency manifests first for layer caching
COPY package.json package-lock.json* ./
RUN npm ci

# Copy application code
COPY . .

# Build Next.js app
RUN npm run build

# Non-root user
RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs \
    && chown -R nextjs:nodejs /app
USER nextjs

EXPOSE 3000

CMD ["sh", "-c", "if [ -n \"$JWT_SECRET_KEY_FILE\" ] && [ -r \"$JWT_SECRET_KEY_FILE\" ]; then export JWT_SECRET_KEY=\"$(cat \"$JWT_SECRET_KEY_FILE\")\"; fi; exec npm start"]
