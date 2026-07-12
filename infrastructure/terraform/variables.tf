
// API and Frontend Infrastructure
variable "website_location" {
  type        = string
  default     = "westeurope"
  description = "The Azure region to deploy the API and frontend. See https://azure.microsoft.com/en-gb/global-infrastructure/geographies/#choose-your-region"
}

variable "website_prefix" {
  type        = string
  nullable    = false
  description = "A prefix added to the name of all Azure resources"
}

// Static website config
variable "static_site_name" {
  type        = string
  default     = "e4future"
  description = "name of static website"
}
