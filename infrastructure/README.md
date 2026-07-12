# Project infrastructure

Deploy all infrastructure required to host [e4futuregrid](https://www.e4futuregrid.com/). This includes:

1. The VGI API
    - Written with [FastAPI](https://fastapi.tiangolo.com/) framework.
    - Deployed as a docker image to an Azure Web [App Service](https://docs.microsoft.com/en-us/azure/app-service/overview)
  
2. The VGI Frontend
    - A [Vue](https://vuejs.org/v2/guide/) app
    - Deployed as an Azure [Static WebApp](https://docs.microsoft.com/en-us/azure/static-web-apps/getting-started?tabs=vue)


The deployment steps are as follows:

1. Deploy Azure infrastructure.
2. Configure this repository to allow GitHub actions to deploy the API and Frontend.
3. Optionally configure DNS for a custom domain name.

## Step 1. Deploy Azure Infrastructure

### 📦 Requirements

This has grown from [Azure Sensible](https://github.com/alan-turing-institute/azure-sensible)

Before you start, you will need to install:

- [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli): Used to authenticate communication with Azure
- [Terraform](https://learn.hashicorp.com/tutorials/terraform/install-cli) >=v1.0: Deploys infrastructure on Azure

### 1. Deployment

#### 🔑 Authentication and Azure subscription
To use terraform to deploy infrastructure on Azure, you will first need to
authenticate using the Azure CLI.

```bash
az login
```

which will launch a browser prompting you to login.

Then you will need to set the subscription you would like to deploy the infrastructure into. This requires an subscription Azure.

To see a list of subscriptions available to you, run:

```bash
az account list --output table
```

Set the subscription you would like to deploy to. The VGI Turing Azure subscription is currently called `Electric Vehicle Grid Integration`.

```bash
az account set --subscription "Electric Vehicle Grid Integration"
```

#### :wrench: Infrastructure Configuration

Set the `/infrastructure/terraform` directory as your current working directory:

```bash
cd ./infrastructure/terraform
```

You can set configuration options by editing [`terraform/terraform.tfvars`](terraform/terraform.tfvars). To see what configuration options are available go to [`terraform/variables.tf`](terraform/variables.tf). Any that say `nullable = true` must have a value. You can also set these as environment variables, see https://www.terraform.io/language/values/variables. However, it is worth checking the deployment configuration into version control.

#### :arrow_up: Deploy

Initialise terraform

```bash
terraform init
```

Plan your changes

```bash
terraform plan
```

this will print a list of changes to your terminal so you can see what terraform will do.

When you are happy deploy the infrastructure with

```bash
terraform apply
```

### Step 2. Configure Continuous Delivery Pipeline

#### :hammer: Deploy API and frontend to infrastructure

Terraform should now have deployed the infrastructure. However, we still need to deploy our code to run on the infrastructure.

To do this we use GitHub actions. This makes sure any changes to our codebase are published to Azure whenever they are pushed to the `main` branch.

There are two GitHub actions:

1. API: [deploy_azurewebapp_api.yaml](../.github/workflows/deploy_azurewebapp_api.yaml)
2. Frontend: [azure-static-web-apps-salmon-forest-09e32d403.yml](../.github/workflows/azure-static-web-apps-salmon-forest-09e32d403.yml)

These use secrets from the GitHub repo to authenticate against Azure. To set the secrets follow the [GitHub instructions](https://docs.github.com/en/actions/security-guides/encrypted-secrets). Terraform will have created appropriate secrets for us. To get these values run:

```bash
terraform output
```

However, many of these are sensitive and this will not show. You can get the secrets by running

```bash
terraform output `<secret-name>`
```

where `<secret-name>` is given in the following table:


 Thus we need to set the following secrets in the repo:

| Secret Name                     | Purpose                               | secret-name         |
| ------------------------------- | ------------------------------------- | ------------------- |
| REGISTRY_USERNAME               | Username for Azure Container Registry | registery_username  |
| REGISTRY_PASSWORD               | Password for Azure Container Registry | registry_password   |
| REGISTRY_URL                    | URL Azure Container Registry          | registry_url        |
| AZURE_STATIC_WEB_APPS_API_TOKEN | API Key for Static WebSite            | static_site_api_key |


You need to trigger both GitHub actions, and they should then deploy to Azure. We also need to provide the hostname of the api to the frontend. You can use this commit to trigger the actions. 

To provide the API hostname to the front end find the [.env.production](../.env.production) file in the project root directory. Then set the `VUE_APP_API_URL` key to the value provided by

```bash
terraform output api_hostname
```

If you want to test a locally running frontend with the deployed API, you can do the same in [.env.development](../.env.development) .


### Help my API isn't live

Make sure you trigger the GitHub action workflows. They will deploy the frontend and API to Azure. It may take a little while for the API to go live. The following steps will happen automatically:

1. GH Action builds the API docker image and pushes it to the Azure Container Registry (ACR) created by terraform.
2. The ACR notifies the Azure WebApp that a new docker image has been pushed.
3. The Azure WebApp restarts and downloads the container from the ACR.

However, in practice the Azure WebApp may try and get a container image from the ACR before GH Actions uploads it. It may take some time before it tries to get the container image again. You can speed this up by restarting the Azure Web App.

#### Manually deploy API

The API can be deployed without GitHub actions, which might be useful if you are just testing things out. The exact command you need to run is unique to your deployment. Luckily you can ask terraform to give you the exact command:

```bash
terraform output docker_api_command
```

You should then run the command from the project root directory.

### 💣 Destroy the resources

If you no longer need your Azure resources you can remove them all with

```bash
terraform destroy
```

This will delete all Azure resources and any data stored on these resources will
be lost.


## Step 3. Optionally configure DNS for a custom domain name.

You can add a custom domain name to the frontend. For example, we manage DNS with [CloudFlare](https://www.cloudflare.com/en-gb/multi-cloud/azure/).

### Running the webapp locally

See the guide in `azure_funcs/README.md` in the [WebApp Repo](https://github.com/alan-turing-institute/vehicle-grid-integration-webapp-private).

### Refreshing the webapp

After pushing updates to the [WebApp Repo](https://github.com/alan-turing-institute/vehicle-grid-integration-webapp-private), the GitHub Actions should automatically redeploy the webapp and/or backend with your changes.

To see updates to the webapp pages, you may have to refresh your browser cache instead of doing a standard refresh of the page.
On a Mac, this can be done by pressing command + shift + R.
