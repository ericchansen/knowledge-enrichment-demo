// Azure Storage Account — one per environment (prod / stage)
// Note: subscription policy blocks shared key access, must use Entra ID

@description('Storage account name (globally unique, alphanumeric, 3-24 chars)')
param name string

@description('Location')
param location string = resourceGroup().location

param tags object = {}

@description('Corpus container name')
param corpusContainer string = 'corpus'

@description('CU results container name')
param resultsContainer string = 'cu-results'

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: name
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    accessTier: 'Hot'
    allowSharedKeyAccess: false
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storageAccount
  name: 'default'
}

resource corpus 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: corpusContainer
}

resource results 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: resultsContainer
}

output storageId string = storageAccount.id
output storageName string = storageAccount.name
output storageAccountUrl string = storageAccount.properties.primaryEndpoints.blob
