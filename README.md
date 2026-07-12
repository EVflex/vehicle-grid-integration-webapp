# VGI API and WebApp

Check out our demonstration [website](https://www.e4futuregrid.com/).

## API/Backend

The VGI API is written in [FastAPI](https://fastapi.tiangolo.com/) and run in production via [Azure Functions](https://docs.microsoft.com/en-us/azure/azure-functions/).

The project directory contains the following folders
```
vgi_api/
azure_funcs/
```


[`vgi_api`](vgi_api) is the VGI API (a python package, Python 3.10–3.14).

[`azure_funcs`](azure_funcs) is the Azure Function App which runs `vgi_api` in production.


## WebApp
If you're on Windows and don't have Node.js installed, you can install it from here https://nodejs.org/en/download/
The Node.js installer includes the NPM package manager.

## Project setup
```
npm install
```

### Compiles and hot-reloads for development

```
npm run serve
```

You can change the API endpoint by altering [.env.development](.env.development) which defaults to `http://127.0.0.1:8000`.

This assumes you are running the API server locally, which you can do with:

```bash
cd vgi_api && poetry run uvicorn vgi_api:app --reload --port 8000
```

If you want to use the production API (i.e. on Azure) change the contents of [.env.development](.env.development) to match that in [.env.production](.env.production).



### Compiles and minifies for production
```
npm run build
```

### Lints and fixes files
```
npm run lint
```

### Customize configuration
See [Configuration Reference](https://cli.vuejs.org/config/).
