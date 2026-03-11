FROM node:22-alpine

WORKDIR /app

ARG API_BASE_URL=http://backend:8000/api/v1
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1

ENV API_BASE_URL=${API_BASE_URL}
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

COPY frontend ./
RUN npm run build

EXPOSE 3000

CMD ["npm", "run", "start"]
