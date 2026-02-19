// Main deployment — Knowledge Enrichment Demo
// Deploys all infrastructure for a given environment (prod / stage)
//
// Shared resources (deploy once):  ACR
// Per-environment resources:       Container Apps Env, Container App,
//                                  AI Search, Storage Account
//
// Existing resources (referenced): AI Services (dev-beme-ai),
//                                  Log Analytics (dev-beme-logs)

targetScope = 'resourceGroup'

// ── Parameters ──────────────────────────────────────────────────────────────

@description('Environment name (prod, stage, pr-42, etc.)')
param environmentName string

@description('Location for all new resources')
param location string = resourceGroup().location

@description('Container image to deploy (e.g., myacr.azurecr.io/enrichment:sha-abc)')
param containerImage string = ''

@description('ACR name (globally unique)')
param acrName string

@description('Existing AI Services account name')
param aiServicesName string = 'dev-beme-ai'

@description('Existing Log Analytics workspace name')
param logAnalyticsWorkspaceName string = 'dev-beme-logs'

@description('Embedding model deployment name')
param embeddingDeployment string = 'text-embedding-3-small'

@description('Chat model deployment name')
param chatDeployment string = 'gpt-41'

param tags object = {}

// ── Computed Names ──────────────────────────────────────────────────────────

var envSuffix = environmentName == 'prod' ? '' : '-${environmentName}'
var searchName = 'beme-search${envSuffix}'
var storageName = 'bemestorage${replace(environmentName, '-', '')}'
var appEnvName = 'beme-cae${envSuffix}'
var appName = 'beme-enrichment${envSuffix}'

// Well-known role definition GUIDs
var storageBlobDataContributorRole = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
var searchServiceContributorRole = '7ca78c08-252a-4471-8644-bb5ff32d4ba0'
var cognitiveServicesUserRole = 'a97b65f3-24c7-4388-baec-2e87135dc908'
var acrPullRole = '7f951dda-4ed3-4680-a7ca-43fe172d538d'

// ── Existing Resources ──────────────────────────────────────────────────────

resource aiServices 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: aiServicesName
}

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = {
  name: logAnalyticsWorkspaceName
}

// ── Shared: ACR ─────────────────────────────────────────────────────────────

module acr 'modules/acr.bicep' = {
  name: 'acr-${acrName}'
  params: {
    name: acrName
    location: location
    tags: tags
  }
}

// ── Per-Environment: Storage ────────────────────────────────────────────────

module storage 'modules/storage.bicep' = {
  name: 'storage-${environmentName}'
  params: {
    name: storageName
    location: location
    tags: union(tags, { environment: environmentName })
  }
}

// ── Per-Environment: AI Search ──────────────────────────────────────────────

module search 'modules/search.bicep' = {
  name: 'search-${environmentName}'
  params: {
    name: searchName
    location: location
    tags: union(tags, { environment: environmentName })
  }
}

// ── Per-Environment: Container Apps ─────────────────────────────────────────

module appEnv 'modules/container-app-env.bicep' = {
  name: 'cae-${environmentName}'
  params: {
    name: appEnvName
    location: location
    logAnalyticsWorkspaceId: logAnalytics.id
    tags: union(tags, { environment: environmentName })
  }
}

module app 'modules/container-app.bicep' = if (!empty(containerImage)) {
  name: 'app-${environmentName}'
  params: {
    name: appName
    location: location
    environmentId: appEnv.outputs.environmentId
    containerImage: containerImage
    acrLoginServer: acr.outputs.acrLoginServer
    tags: union(tags, { environment: environmentName })
    minReplicas: environmentName == 'prod' ? 1 : 0
    maxReplicas: environmentName == 'prod' ? 3 : 1
    secrets: [
      { name: 'search-api-key', value: search.outputs.searchAdminKey }
      { name: 'cu-key', value: aiServices.listKeys().key1 }
    ]
    envVars: [
      { name: 'ENVIRONMENT', value: environmentName }
      { name: 'CONTENTUNDERSTANDING_ENDPOINT', value: aiServices.properties.endpoint }
      { name: 'CONTENTUNDERSTANDING_KEY', secretRef: 'cu-key' }
      { name: 'AZURE_OPENAI_ENDPOINT', value: '${aiServices.properties.endpoint}openai/' }
      { name: 'AZURE_OPENAI_KEY', secretRef: 'cu-key' }
      { name: 'SEARCH_ENDPOINT', value: search.outputs.searchEndpoint }
      { name: 'SEARCH_API_KEY', secretRef: 'search-api-key' }
      { name: 'STORAGE_ACCOUNT_URL', value: storage.outputs.storageAccountUrl }
      { name: 'EMBEDDING_DEPLOYMENT', value: embeddingDeployment }
      { name: 'CHAT_DEPLOYMENT', value: chatDeployment }
      { name: 'SEARCH_INDEX_BASELINE', value: 'baseline-index' }
      { name: 'SEARCH_INDEX_ENHANCED', value: 'enhanced-index' }
      { name: 'LOG_LEVEL', value: environmentName == 'prod' ? 'INFO' : 'DEBUG' }
    ]
  }
}

// ── Role Assignments (Container App managed identity) ───────────────────────

var appPrincipalId = !empty(containerImage) ? app.outputs.principalId : ''

// Storage Blob Data Contributor — read/write blobs
module roleStorage 'modules/role-assignment.bicep' = if (!empty(containerImage)) {
  name: 'role-storage-${environmentName}'
  params: {
    principalId: appPrincipalId
    roleDefinitionId: storageBlobDataContributorRole
  }
}

// Cognitive Services User — call AI Services (CU + OpenAI)
module roleCognitive 'modules/role-assignment.bicep' = if (!empty(containerImage)) {
  name: 'role-cognitive-${environmentName}'
  params: {
    principalId: appPrincipalId
    roleDefinitionId: cognitiveServicesUserRole
  }
}

// Search Service Contributor — manage indexes
module roleSearch 'modules/role-assignment.bicep' = if (!empty(containerImage)) {
  name: 'role-search-${environmentName}'
  params: {
    principalId: appPrincipalId
    roleDefinitionId: searchServiceContributorRole
  }
}

// ACR Pull — pull images from registry
module roleAcrPull 'modules/role-assignment.bicep' = if (!empty(containerImage)) {
  name: 'role-acr-pull-${environmentName}'
  params: {
    principalId: appPrincipalId
    roleDefinitionId: acrPullRole
  }
}

// ── Outputs ─────────────────────────────────────────────────────────────────

output acrLoginServer string = acr.outputs.acrLoginServer
output storageAccountUrl string = storage.outputs.storageAccountUrl
output searchEndpoint string = search.outputs.searchEndpoint
output appUrl string = !empty(containerImage) ? app.outputs.appUrl : ''
output appFqdn string = !empty(containerImage) ? app.outputs.appFqdn : ''
