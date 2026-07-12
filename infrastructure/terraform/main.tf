# Configure the Microsoft Azure Provider
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 2.26"
    }
  }
}

# Declare Azure provider
provider "azurerm" {
  features {}
}

# Generate a random integer to create a globally unique name
resource "random_integer" "ri" {
  min = 10000
  max = 99999
}

# Create uniquely named resource group to deploy API and Frontend in
resource "azurerm_resource_group" "website_rg" {
  name     = "${var.website_prefix}RG-${random_integer.ri.result}"
  location = var.website_location
}



# Create an app service plan - Hosts the API
resource "azurerm_app_service_plan" "appserviceplan" {
  name                = "${var.website_prefix}-ASP-${random_integer.ri.result}"
  location            = azurerm_resource_group.website_rg.location
  resource_group_name = azurerm_resource_group.website_rg.name
  kind                = "linux"
  reserved            = true
  sku {
    tier = "PremiumV2"
    size = "P2v2"
  }
}

# Create a WebApp in the App service
# Azure container registry to push docker image to
resource "azurerm_container_registry" "acr" {
  name                = "${var.website_prefix}acr${random_integer.ri.result}"
  resource_group_name = azurerm_resource_group.website_rg.name
  location            = azurerm_resource_group.website_rg.location
  sku                 = "Basic"
  admin_enabled       = true
}

# WebApp to host API
resource "azurerm_app_service" "webapp" {
  name                = "${var.website_prefix}-webapp-${random_integer.ri.result}"
  location            = azurerm_resource_group.website_rg.location
  resource_group_name = azurerm_resource_group.website_rg.name
  app_service_plan_id = azurerm_app_service_plan.appserviceplan.id
  https_only          = true

  app_settings = {
    WEBSITES_ENABLE_APP_SERVICE_STORAGE = false
    # Settings for private Container Registires  
    DOCKER_REGISTRY_SERVER_URL      = "https://${azurerm_container_registry.acr.login_server}"
    DOCKER_REGISTRY_SERVER_USERNAME = azurerm_container_registry.acr.admin_username
    DOCKER_REGISTRY_SERVER_PASSWORD = azurerm_container_registry.acr.admin_password

    DOCKER_ENABLE_CI = true

    # Environment vars for Docker image
    # CHANGE: APP_MODULE was a convention of the (deprecated, removed)
    # tiangolo/uvicorn-gunicorn-fastapi base image; the rebuilt
    # docker_images/vgi_api.dockerfile starts gunicorn explicitly, so
    # APP_MODULE is no longer read.
    GRACEFUL_TIMEOUT = 300

    # CHANGE(security): the API no longer allows every origin (CORS). Set
    # this to the deployed frontend's origin. The static site hostname is only
    # known after `terraform apply`, so it is interpolated here.
    VGI_CORS_ORIGINS = "https://${azurerm_static_site.static_site.default_host_name}"

    # CHANGE(scalability): how many simulations each API worker may run in
    # parallel (in isolated subprocesses). 2 here x 2 gunicorn workers = up
    # to 4 concurrent simulations, ~400 MB RAM each while running — sized
    # for the P2v2 plan's 7 GB. Raise alongside the plan size.
    VGI_MAX_PARALLEL_SIMULATIONS = 2
  }

  # Configure Docker Image to load on start
  site_config {
    linux_fx_version = "DOCKER|${var.website_prefix}acr${random_integer.ri.result}.azurecr.io/vgi_api:latest"
    always_on        = "true"
  }
}

//Static site (Frontend)
resource "azurerm_static_site" "static_site" {
  name                = "${var.website_prefix}${var.static_site_name}"
  resource_group_name = azurerm_resource_group.website_rg.name
  location            = var.website_location
}


//Outputs
output "docker_api_command" {
  description = "Run the following command to build and push the docker image. Make sure you are in the project root directory first"
  value       = "az acr build --file docker_images/vgi_api.dockerfile --registry ${azurerm_container_registry.acr.login_server} --image vgi_api:latest ."
}

output "registry_username" {
    description = "For CI with GitHub actions set the 'REGISTRY_USERNAME' secret in your GitHub repo"
    value = "REGISTRY_USERNAME=${azurerm_container_registry.acr.admin_username}"
    sensitive = true
}

output "registry_password" {
    description = "For CI with GitHub actions set the 'REGISTRY_PASSWORD' secret in your GitHub repo"
    value = "REGISTRY_PASSWORD=${azurerm_container_registry.acr.admin_password}"
    sensitive = true
}

output "registry_url" {
    description = "For CI with GitHub actions set the 'REGISTRY_URL' secret in your GitHub repo"
    value = "REGISTRY_URL=${azurerm_container_registry.acr.login_server}"
    sensitive = true
}

output "api_hostname" {
    description = "The default host name of the API"
    value = "https://${azurerm_app_service.webapp.default_site_hostname}"
}

output "static_site_api_key" {
    description = "To deploy the static website set the `AZURE_STATIC_WEB_APPS_API_TOKEN` in your GitHub repo"
    value = "AZURE_STATIC_WEB_APPS_API_TOKEN=${azurerm_static_site.static_site.api_key}"
    sensitive = true
}

output "static_site_hostname" {
    description = "Append the host name to the filename .github/workflows/azure-static-web-apps-salmon-forest`"
    value = "azure-static-web-apps-salmon-forest-${azurerm_static_site.static_site.default_host_name}"
    sensitive = true
}
