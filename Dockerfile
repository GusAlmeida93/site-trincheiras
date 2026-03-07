FROM node:20-alpine

WORKDIR /app

# Copy package files and install dependencies
COPY package.json package-lock.json* ./
RUN npm ci --production

# Copy application files
COPY server/ ./server/
COPY index.html styles.css script.js ./
COPY assets/ ./assets/
COPY public/ ./public/

EXPOSE 8080

CMD ["node", "server/server.js"]
