## Deploy to Azure Container Registry Manually

From the project root directory:

Ensure you have the Azure CLI installed.

Sign in 

```bash 
az login
```

Build docker image and push to container registry:

```bash
az acr build --file docker_images/vgi_api.dockerfile --registry vgiregistry.azurecr.io --image vgi_api:latest .
```

where `registry` is the deployed Azure Container Registry.


