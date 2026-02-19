using 'main.bicep'

param environmentName = 'prod'
param acrName = 'bemeacr'
param location = 'eastus2'
param aiServicesName = 'dev-beme-ai'
param logAnalyticsWorkspaceName = 'dev-beme-logs'
param embeddingDeployment = 'text-embedding-3-small'
param chatDeployment = 'gpt-41'
param tags = {
  project: 'knowledge-enrichment-demo'
  environment: 'prod'
}
