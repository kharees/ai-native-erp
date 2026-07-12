# AI-Native ERP — Frontend (Next.js 14) production image
#
# Not verified with a live `docker build` — no Docker daemon available in
# the sandbox this was written in (see docs/production-hardening.md). The
# `npm run build` this depends on (with next.config.js's `output: "standalone"`,
# added alongside this Dockerfile) was verified locally and does produce the
# .next/standalone/server.js this image runs.

FROM node:20-slim AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

FROM node:20-slim AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Public env vars must be present at build time — Next.js inlines
# NEXT_PUBLIC_* values into the client bundle during `next build`, they
# cannot be swapped in at container start like server-only config can.
ARG NEXT_PUBLIC_API_BASE_URL
ARG NEXT_PUBLIC_APP_NAME
ARG NEXT_PUBLIC_APP_VERSION
ARG NEXT_PUBLIC_SUPABASE_URL
ARG NEXT_PUBLIC_SUPABASE_ANON_KEY
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL \
    NEXT_PUBLIC_APP_NAME=$NEXT_PUBLIC_APP_NAME \
    NEXT_PUBLIC_APP_VERSION=$NEXT_PUBLIC_APP_VERSION \
    NEXT_PUBLIC_SUPABASE_URL=$NEXT_PUBLIC_SUPABASE_URL \
    NEXT_PUBLIC_SUPABASE_ANON_KEY=$NEXT_PUBLIC_SUPABASE_ANON_KEY
RUN npm run build

FROM node:20-slim AS runner
WORKDIR /app
ENV NODE_ENV=production

RUN useradd --create-home --shell /bin/bash appuser
# .next/standalone (next.config.js: output: "standalone") ships its own
# minimal node_modules subset — no separate npm install needed here.
COPY --from=builder --chown=appuser:appuser /app/.next/standalone ./
COPY --from=builder --chown=appuser:appuser /app/.next/static ./.next/static
COPY --from=builder --chown=appuser:appuser /app/public ./public

USER appuser
EXPOSE 3000
ENV PORT=3000 HOSTNAME=0.0.0.0

CMD ["node", "server.js"]
