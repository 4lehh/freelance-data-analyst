# Freelance Data Analyst - Personal Project

[![GitHub](https://img.shields.io/badge/GitHub-4lehh-blue?logo=github)](https://github.com/4lehh)

## Herramientas de Desarrollo

<div align="center">
  <a href="https://skillicons.dev">
    <img src="https://skillicons.dev/icons?i=python,html,css,js,git,github,neovim,docker,markdown,postgresql&perline=10" />
  </a>
</div>

* **Modelo Principal**: QGwen 2.5 Coder.
* **Database**: PostgreSQL.
* **Interfaz y Despliegue**: HTML5 + CSS + JS y Docker.

## Descripción

El proyecto nace de la dificultad de los datasets con los que trabajamos. Para ello, he diseñado un agente local (Qwen 2.5 Coder) que, dado un dataset, te puede hacer un análisis básico de estadisticos descriptivos y también creación de gráficos y código de Machine Learning. Además, los gráficos los puede ejecutar de manera local y lo puedes visualizar dentro de la interfaz. Así también, los códigos generados los puedes descargar y ejecutar en tu computador sin problema alguno. 

## Ejecución y Despliegue

> [!NOTE] 
> Se requiere tener instalado Docker 29.6 o superior.

Para la inicialización del proyecto, primero debes clonar el repositorio:

```sh 
# Dentro de un directorio que tu elijas
git clone https://github.com/4lehh/freelance-data-analyst.git
``` 

Luego, teniendo Docker instalado:

```sh 
# Si deseas ver logs en el momento quitar el '-d'
docker compose up --build -d
```

Ahora, en tu navegador de preferencia, podrás ver la interfaz ubicada en: 

```sh 
# Interfaz
localhost:8501
```

## Contacto

| Nombre | Correo | Github |
|--------|--------|--------|
|Javier ALejandro Campos Contreras|camposjavier143@gmail.com|[@4lehh](https://github.com/4lehh)|
