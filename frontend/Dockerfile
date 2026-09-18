FROM node:22-bookworm-slim AS development
ENV NEXT_TELEMETRY_DISABLED=1
WORKDIR /app
RUN chown node:node /app
USER node
COPY --chown=node:node frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY --chown=node:node frontend/ ./
CMD ["npm", "run", "dev"]
