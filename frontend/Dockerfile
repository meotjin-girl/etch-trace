FROM oven/bun:1.3.14-alpine AS build
WORKDIR /app
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile
COPY . .
RUN bun run build

FROM nginx:1.27-alpine
COPY --from=build /app/*.html /app/*.css /app/*.js /usr/share/nginx/html/
COPY --from=build /app/vendor /usr/share/nginx/html/vendor
