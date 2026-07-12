# NEW (2026-07-06, see CHANGES.md §13): builds the EXISTING Vue frontend
# (src/ — old code, unchanged) and serves it with Caddy.
#
# Stage 1 compiles the frontend. The 2021 Vue CLI 4 toolchain uses webpack 4,
# whose hashing needs OpenSSL's legacy provider on Node >= 17 — hence
# NODE_OPTIONS below (verified: builds cleanly this way).
FROM node:24-slim AS frontend
ENV NODE_OPTIONS=--openssl-legacy-provider
WORKDIR /build
COPY package.json package-lock.json babel.config.js ./
RUN npm ci --no-audit --no-fund
COPY src ./src
ARG VUE_APP_API_URL
ENV VUE_APP_API_URL=${VUE_APP_API_URL}
RUN npx vue-cli-service build

# Stage 2: Caddy does not ship a rate-limit module; compile it in. This is
# the only protection the anonymous, CPU-expensive /simulate endpoint has,
# so it is worth the extra build stage.
FROM caddy:2-builder AS caddybuild
RUN xcaddy build --with github.com/mholt/caddy-ratelimit

FROM caddy:2
COPY --from=caddybuild /usr/local/bin/caddy /usr/local/bin/caddy
COPY --from=frontend /build/dist /srv
COPY deployment/Caddyfile /etc/caddy/Caddyfile
