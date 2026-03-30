FROM node:20-alpine AS build

WORKDIR /app

ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL

COPY package.json .
RUN npm install

COPY . .
RUN npm run build

FROM node:20-alpine AS serve

WORKDIR /app

COPY --from=build /app/dist /app/dist
COPY --from=build /app/package.json .

RUN npm install --production

EXPOSE 3000

CMD ["npx", "vite", "preview", "--host", "0.0.0.0", "--port", "3000"]
