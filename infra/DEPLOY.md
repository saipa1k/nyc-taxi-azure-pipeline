# Deploying the storage layer

## Prerequisites
- Azure CLI installed (`az --version` to check)
- Logged in: `az login`
- An active subscription selected: `az account set --subscription "<your-subscription-name>"`

## 1. Create a resource group
```bash
az group create --name rg-nyctaxi-project --location eastus
```

## 2. Deploy the Bicep template
```bash
az deployment group create \
  --resource-group rg-nyctaxi-project \
  --template-file main.bicep \
  --parameters projectName=nyctaxidl
```

This creates:
- One StorageV2 account with hierarchical namespace enabled (i.e. Data Lake Gen2, not plain blob storage)
- Three containers: `bronze`, `silver`, `gold`

## 3. Confirm it worked
```bash
az storage account show \
  --name <storageAccountName-from-output> \
  --resource-group rg-nyctaxi-project \
  --query "isHnsEnabled"
```
Should return `true`.

## 4. Note the outputs
The deployment prints `storageAccountName` and `dfsEndpoint` — you'll need both
when setting up the Data Factory linked service in the next step.

## Cost note
Standard_LRS storage is a few cents per GB/month. Nothing here runs
continuously, so leaving it deployed while you build costs pennies. Delete
the whole resource group when you're done experimenting:
```bash
az group delete --name rg-nyctaxi-project
```
