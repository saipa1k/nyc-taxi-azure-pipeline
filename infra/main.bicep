// main.bicep
// Deploys an Azure Data Lake Storage Gen2 account with bronze/silver/gold
// containers for the NYC Taxi medallion architecture project.

@description('Base name used to derive resource names (lowercase, no spaces)')
param projectName string = 'nyctaxidl'

@description('Azure region for all resources')
param location string = resourceGroup().location

@description('Storage account SKU - Standard_LRS is cheapest for a learning project')
param storageSku string = 'Standard_LRS'

var storageAccountName = toLower('${projectName}${uniqueString(resourceGroup().id)}')

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: storageSku
  }
  kind: 'StorageV2'
  properties: {
    isHnsEnabled: true // enables hierarchical namespace = Data Lake Gen2
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  name: 'default'
  parent: storageAccount
}

resource bronzeContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  name: 'bronze'
  parent: blobService
}

resource silverContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  name: 'silver'
  parent: blobService
}

resource goldContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  name: 'gold'
  parent: blobService
}

output storageAccountName string = storageAccount.name
output storageAccountId string = storageAccount.id
output dfsEndpoint string = storageAccount.properties.primaryEndpoints.dfs
