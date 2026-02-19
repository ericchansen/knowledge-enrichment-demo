// Main deployment — Knowledge Enrichment Demo
// Deploys the Container App for a given environment (prod / stage).
//
// Managed by Bicep:   ACR (shared), Container App + CAE + MI (per-env)
// Pre-existing:       AI Services, AI Search, Storage, Log Analytics
//
// All environments share the same Search indexes and Storage corpus.

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

@description('Existing AI Search service name')
param searchServiceName string = 'dev-beme-search'

@description('Existing Storage account name')
param storageAccountName string = 'devbemestorage'

@description('Embedding model deployment name')
param embeddingDeployment string = 'text-embedding-3-small'

@description('Chat model deployment name')
param chatDeployment string = 'gpt-41'

param tags object = {}

// ── Computed Names ──────────────────────────────────────────────────────────

var envSuffix = environmentName == 'prod' ? '' : '-${environmentName}'
var appEnvName = 'beme-cae${envSuffix}'
var appName = 'beme-enrichment${envSuffix}'
var identityName = 'beme-id${envSuffix}'

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

resource searchService 'Microsoft.Search/searchServices@2024-06-01-preview' existing = {
  name: searchServiceName
}

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
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

// ── Per-Environment: User-Assigned Managed Identity ─────────────────────────

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: identityName
  location: location
  tags: union(tags, { environment: environmentName })
}

// ── Role Assignments (user-assigned MI) ─────────────────────────────────────

module roleStorage 'modules/role-assignment.bicep' = {
  name: 'role-storage-${environmentName}'
  params: {
    principalId: identity.properties.principalId
    roleDefinitionId: storageBlobDataContributorRole
  }
}

module roleCognitive 'modules/role-assignment.bicep' = {
  name: 'role-cognitive-${environmentName}'
  params: {
    principalId: identity.properties.principalId
    roleDefinitionId: cognitiveServicesUserRole
  }
}

module roleSearch 'modules/role-assignment.bicep' = {
  name: 'role-search-${environmentName}'
  params: {
    principalId: identity.properties.principalId
    roleDefinitionId: searchServiceContributorRole
  }
}

module roleAcrPull 'modules/role-assignment.bicep' = {
  name: 'role-acr-pull-${environmentName}'
  params: {
    principalId: identity.properties.principalId
    roleDefinitionId: acrPullRole
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
  dependsOn: [roleAcrPull]
  params: {
    name: appName
    location: location
    environmentId: appEnv.outputs.environmentId
    containerImage: containerImage
    acrLoginServer: acr.outputs.acrLoginServer
    userAssignedIdentityId: identity.id
    tags: union(tags, { environment: environmentName })
    minReplicas: environmentName == 'prod' ? 1 : 0
    maxReplicas: environmentName == 'prod' ? 3 : 1
    secrets: [
      { name: 'search-api-key', value: searchService.listAdminKeys().primaryKey }
      { name: 'cu-key', value: aiServices.listKeys().key1 }
    ]
    envVars: [
      { name: 'ENVIRONMENT', value: environmentName }
      { name: 'CONTENTUNDERSTANDING_ENDPOINT', value: aiServices.properties.endpoint }
      { name: 'CONTENTUNDERSTANDING_KEY', secretRef: 'cu-key' }
      { name: 'AZURE_OPENAI_ENDPOINT', value: aiServices.properties.endpoint }
      { name: 'AZURE_OPENAI_KEY', secretRef: 'cu-key' }
      { name: 'SEARCH_ENDPOINT', value: 'https://${searchService.name}.search.windows.net' }
      { name: 'SEARCH_API_KEY', secretRef: 'search-api-key' }
      { name: 'STORAGE_ACCOUNT_URL', value: storageAccount.properties.primaryEndpoints.blob }
      { name: 'EMBEDDING_DEPLOYMENT', value: embeddingDeployment }
      { name: 'CHAT_DEPLOYMENT', value: chatDeployment }
      { name: 'SEARCH_INDEX_BASELINE', value: 'baseline-index' }
      { name: 'SEARCH_INDEX_ENHANCED', value: 'enhanced-index' }
      { name: 'LOG_LEVEL', value: environmentName == 'prod' ? 'INFO' : 'DEBUG' }
    ]
  }
}

// ── Outputs ─────────────────────────────────────────────────────────────────

output acrLoginServer string = acr.outputs.acrLoginServer
output appUrl string = !empty(containerImage) ? app.outputs.appUrl : ''
output appFqdn string = !empty(containerImage) ? app.outputs.appFqdn : ''
