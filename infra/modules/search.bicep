// Azure AI Search — one per environment (prod / stage)
// Indexes are created by the application at runtime

@description('Search service name (globally unique)')
param name string

@description('Location')
param location string = resourceGroup().location

@description('SKU')
@allowed(['free', 'basic', 'standard', 'standard2', 'standard3'])
param sku string = 'basic'

param tags object = {}

resource search 'Microsoft.Search/searchServices@2024-06-01-preview' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: sku
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
  }
}

output searchId string = search.id
output searchName string = search.name
output searchEndpoint string = 'https://${search.name}.search.windows.net'
#disable-next-line outputs-should-not-contain-secrets
output searchAdminKey string = search.listAdminKeys().primaryKey
