// Azure Container App — one per environment (prod / stage)

@description('Name of the Container App')
param name string

@description('Location')
param location string = resourceGroup().location

@description('Container Apps Environment ID')
param environmentId string

@description('Full image reference (e.g., myacr.azurecr.io/enrichment:sha-abc123)')
param containerImage string

@description('ACR login server (e.g., myacr.azurecr.io)')
param acrLoginServer string

@description('User-assigned managed identity resource ID (must already have AcrPull)')
param userAssignedIdentityId string

@description('Environment variables for the container')
param envVars array = []

@description('Secrets for the container app')
param secrets array = []

param tags object = {}

@description('Minimum replicas (0 = scale to zero)')
param minReplicas int = 0

@description('Maximum replicas')
param maxReplicas int = 3

resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: name
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${userAssignedIdentityId}': {}
    }
  }
  properties: {
    managedEnvironmentId: environmentId
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8080
        transport: 'http'
        allowInsecure: false
      }
      registries: [
        {
          server: acrLoginServer
          identity: userAssignedIdentityId
        }
      ]
      secrets: secrets
    }
    template: {
      containers: [
        {
          name: 'enrichment'
          image: containerImage
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: envVars
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: [
          {
            name: 'http-scale'
            http: {
              metadata: {
                concurrentRequests: '20'
              }
            }
          }
        ]
      }
    }
  }
}

output appId string = containerApp.id
output appName string = containerApp.name
output appFqdn string = containerApp.properties.configuration.ingress.fqdn
output appUrl string = 'https://${containerApp.properties.configuration.ingress.fqdn}'
