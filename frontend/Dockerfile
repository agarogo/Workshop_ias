FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm install

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=development
ENV NEXT_PUBLIC_EXPERIMENTS_API_URL=/api/experiments
ENV EXPERIMENTS_BACKEND_URL=http://backend:8100
COPY --from=deps /app/node_modules ./node_modules
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0", "--port", "3000"]
