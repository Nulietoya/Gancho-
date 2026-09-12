# ETAPA 35 — imagem de produção do frontend. Build em duas etapas:
# a primeira compila o bundle estático (Vite), a segunda só serve
# esses arquivos com nginx — a imagem final não carrega Node nem
# node_modules, só HTML/CSS/JS já prontos.
#
# `VITE_API_BASE_URL` precisa ser passado como build arg (não como
# variável de ambiente do container em runtime) porque o Vite grava
# esse valor DENTRO do JS compilado — ver docs/deploy.md.
FROM node:20-slim AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
